#!/usr/bin/env python3
"""Re-derives the `agencies` tags for every record in data/institutes.json (rules below).
Run after adding records:  python tools/tag_agencies.py
A tag means the institute, or its biotechnology programme, is run, funded or supported by that agency,
judged from the record's own text. Edit a record's `agencies` by hand only if you also keep the rule in sync."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
P = ROOT / "data" / "institutes.json"
GOI = "Govt. of India autonomous (IIT, AIIMS, NIT, IISER, IISc)"
ICAR_WORDS = ("agricultural", "veterinary", "horticulture", "krishi")

def tags(i):
    ag = []
    meta = (i["type"] + " " + i["name"] + " " + i["department"]).lower()
    nm = i["name"].lower()
    body = " ".join([i["programmes"], i["department"], " ".join(i["seats"]),
                     i["eligibility"].get("masters") or "", i["eligibility"].get("ug") or ""]).lower()
    if "dbt" in body or "gat-b" in body or "regional centre for biotechnology" in meta or any(k in meta for k in ("cdfd", "niab", "dbt autonomous", "nccs", "rgcb")):
        ag.append("DBT")
    if "dst autonomous" in meta or "bose institute" in nm or "institute of nano science" in nm:
        ag.append("DST")
    if "csir" in meta or "cftri" in meta or "ccmb" in meta:
        ag.append("CSIR")
    if "icmr" in nm or "icmr research institute" in meta:
        ag.append("ICMR")
    if "icar" in meta or any(w in i["type"].lower() for w in ICAR_WORDS):
        ag.append("ICAR")
    t = i["type"].lower()
    if (i["ownership"] == "Central Government" and any(k in t for k in ("national importance", "eminence", "tifr"))) or \
       any(k in nm for k in ("indian institute of technology", "national institute of technology", "aiims", "all india institute", "iiser", "science education and research")):
        ag.append(GOI)
    return ag

if __name__ == "__main__":
    d = json.loads(P.read_text(encoding="utf-8"))
    for i in d["institutes"]:
        ag = tags(i)
        items = list(i.items()); i.clear()
        for k, v in items:
            if k == "agencies": continue
            i[k] = v
            if k == "ownership": i["agencies"] = ag
    P.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(len(d["institutes"]), dict(Counter(a for i in d["institutes"] for a in i["agencies"])))
