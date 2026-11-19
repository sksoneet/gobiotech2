#!/usr/bin/env python3
"""Link every institute's UG / Masters / PhD section to the entrance exams used for admission.

Reads data/institutes.json and data/exams.json (plus optional data/exam_overrides.json) and writes an `entrance`
field on each institute:  {"ug": {"exams": [ids], "others": [names], "note": "..."}, "masters": {...}, "phd": {...}}

Detection uses only the text for that level (eligibility, level-specific seat lines, stream), so a B.Tech line that
mentions JEE Main never links the Masters section. Manual fixes go in data/exam_overrides.json:
  {"institute-id": {"masters": {"exams": ["gat-b"], "others": [], "note": ""}}}
Run:  python tools/link_exams.py
"""
import json, pathlib, re, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = ROOT / "data" / "institutes.json"
D = json.loads(P.read_text(encoding="utf-8"))
EX = {e["id"]: e for e in json.loads((ROOT / "data" / "exams.json").read_text(encoding="utf-8"))["exams"]}
OVR = {}
if (ROOT / "data" / "exam_overrides.json").exists():
    OVR = json.loads((ROOT / "data" / "exam_overrides.json").read_text(encoding="utf-8"))

SEATRE = {
    "ug": re.compile(r"B\.\s?Tech|B\.\s?Sc|B\.\s?E\.|BS-MS|\bBS\b|B\.S\.|integrated|\bUG\b|undergraduate", re.I),
    "masters": re.compile(r"M\.\s?Sc|M\.\s?Tech|M\.V\.Sc|M\.\s?E\.|M\.Biotech|master|\bPG\b|DBT-supported|GAT-B|JAM", re.I),
    "phd": re.compile(r"Ph\.?\s?D|doctoral", re.I),
}
OTHERS = [("KCET", r"\bkcet\b"), ("COMEDK UGET", r"comedk"), ("KEAM", r"\bkeam\b"), ("TNEA", r"\btnea\b"), ("WBJEE", r"wbjee"),
          ("OJEE", r"\bojee\b"), ("GUJCET / ACPC", r"gujcet|\bacpc\b"), ("AP EAPCET", r"ap eapcet"), ("BITSAT", r"bitsat"), ("VITEEE", r"viteee"), ("SRMJEEE", r"srmjeee"), ("KIITEE", r"kiitee"),
          ("JGEEBILS", r"jgeebils"), ("JNU entrance (JNUEE)", r"jnuee"), ("DST-INSPIRE fellowship", r"inspire"),
          ("HSTES counselling", r"hstes"), ("JAC Delhi counselling", r"jac delhi|jac chandigarh")]


def level_text(i, k):
    e = i["eligibility"]
    parts = [e.get(k) or "", (i.get("streams") or {}).get(k) or ""]
    parts += [s for s in i["seats"] if SEATRE[k].search(s)]
    if k == "masters":
        prog = i["programmes"].lower()
        if "gat-b" in prog or "dbt-supported" in prog:
            parts.append("GAT-B")
    return " ".join(parts)


def detect(i, k):
    t = level_text(i, k)
    tl = t.lower()
    nm = i["name"].lower()
    ex = []
    if k == "ug":
        if "jee advanced" in tl: ex.append("jee-advanced")
        if re.search(r"jee main|josaa|csab", tl): ex.append("jee-main")
        if "cuet" in tl: ex.append("cuet-ug")
        if re.search(r"\biat\b|iiser aptitude", tl): ex.append("iat")
        if "neet" in tl: ex.append("neet-ug")
        if re.search(r"\bnest\b", tl): ex.append("nest")
        if "mht-cet" in tl or "mht cet" in tl: ex.append("mht-cet")
        if re.search(r"eamcet|eapcet", tl): ex.append("ts-eapcet")
        if "aeee" in tl: ex.append("aeee")
    elif k == "masters":
        if re.search(r"iit jam|\bjam\b", tl): ex.append("iit-jam")
        if "cuet" in tl: ex.append("cuet-pg")
        if re.search(r"gat-b|gat b|dbt-supported", tl): ex.append("gat-b")
        if re.search(r"\bgate\b", tl): ex.append("gate")
        if re.search(r"aieea|icar aieea", tl): ex.append("icar-aieea-pg")
        if "aiims" in nm or "aiims" in tl: ex.append("aiims-msc")
        if re.search(r"cpget", tl): ex.append("ts-cpget")
        if re.search(r"pgcet", tl): ex.append("ap-pgcet")
    else:
        if re.search(r"csir[- /]?ugc[- ]net|csir/ugc|\bcsir\b.*\bnet\b", tl): ex.append("csir-ugc-net")
        elif re.search(r"ugc[- ]net", tl): ex.append("ugc-net")
        if re.search(r"dbt-bet|\bbet\b", tl): ex.append("dbt-bet")
        if re.search(r"\bgate\b", tl): ex.append("gate")
        if re.search(r"aice|icar.*jrf", tl): ex.append("icar-aice-jrf")
        if re.search(r"icmr-jrf|dhr|icmr jrf", tl): ex.append("dhr-bret")
        if "aiims" in nm: ex.append("aiims-phd")
    others = [n for n, rx in OTHERS if re.search(rx, tl)]
    own = bool(re.search(r"own (online |entrance |written |admission |common )?(test|exam|process|entrance)|(university|institute|college)['\u2019]?s? (own |online |common )?entrance (test|exam)|entrance (test|exam|examination)s? (conducted|run|held) by (the )?([a-z.\u2019' ]{0,40})(university|institute|college)|qualify the entrance|its own|interview", tl))
    counselling = bool(re.search(r"counselling", tl))
    merit = bool(re.search(r"\bmerit\b", tl))
    note = ""
    if own and not ex:
        note = "Institute's own entrance test or interview"
    elif own:
        note = "Some seats may use the institute's own test or interview"
    elif merit and not ex:
        note = "Merit-based admission on qualifying marks"
    elif counselling and not ex:
        note = "Admission through counselling; see the admission notice"
    return {"exams": [x for x in ex if x in EX], "others": others, "note": note}


TS_UNI = ("osmania", "kakatiya", "telangana university", "mahatma gandhi university", "palamuru", "satavahana", "telangana mahila", "jntuh")
AP_UNI = ("andhra university", "sri venkateswara university", "sri krishnadevaraya", "acharya nagarjuna", "yogi vemana", "sri padmavati", "rayalaseema", "vikrama simhapuri", "dravidian", "svims")
INFER_NOTE = "Typical route inferred from the institution type; confirm in the admission notice."


def infer_masters(i, r):
    """Add typical Masters routes when the text names none. Returns list of inferred exam ids."""
    nm, tp = i["name"].lower(), i["type"].lower()
    prog = i["programmes"].lower()
    ag = set(i["agencies"])
    inf = []
    if "national institute of technology" in nm and ("m.tech" in prog or "m.tech" in (i["eligibility"].get("masters") or "").lower()):
        inf.append("gate")
    if "indian institute of technology" in nm:
        if "m.tech" in prog or "m.s." in prog: inf.append("gate")
        if "m.sc" in prog: inf.append("iit-jam")
    if ("central university" in tp or "central agricultural" in tp) and "cuet-pg" not in r["exams"]:
        inf.append("cuet-pg")
    if "ICAR" in ag and "icar-aieea-pg" not in r["exams"]:
        inf.append("icar-aieea-pg")
    if i["state"] == "Telangana" and any(u in nm for u in TS_UNI) and "ts-cpget" not in r["exams"]:
        inf.append("ts-cpget")
    if i["state"] == "Andhra Pradesh" and any(u in nm for u in AP_UNI) and "ap-pgcet" not in r["exams"]:
        inf.append("ap-pgcet")
    return [x for x in dict.fromkeys(inf) if x in EX and x not in r["exams"]]


stats = collections.Counter(); none = []
for i in D["institutes"]:
    ent = {}
    for k, deg in (("ug", "UG"), ("masters", "Masters"), ("phd", "PhD")):
        if deg not in i["degrees"]:
            continue
        r = detect(i, k)
        o = (OVR.get(i["id"]) or {}).get(k)
        if o:
            r = {"exams": [x for x in o.get("exams", []) if x in EX], "others": o.get("others", []), "note": o.get("note", "")}
            if o.get("inferred"): r["inferred"] = [x for x in o["inferred"] if x in EX]
        if k == "masters" and not o:
            inf = infer_masters(i, r)
            if inf:
                r["inferred"] = inf
                r["exams"] = r["exams"] + inf
                r["note"] = (r["note"] + " \u00b7 " if r["note"] else "") + INFER_NOTE
        ent[k] = r
        stats[k + "_sections"] += 1
        if r["exams"]: stats[k + "_linked"] += 1
        elif r["others"] or r["note"]: stats[k + "_text_only"] += 1
        else: stats[k + "_nothing"] += 1; none.append((i["name"], k))
        for x in r["exams"]: stats["exam:" + x] += 1
    i["entrance"] = ent
P.write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
if __name__ == "__main__":
    for k in ("ug", "masters", "phd"):
        s = stats[k + "_sections"]
        print(f"{k:8} sections {s:3} | linked to an exam {stats[k+'_linked']:3} | text only {stats[k+'_text_only']:3} | nothing found {stats[k+'_nothing']:3}")
    print({k[5:]: v for k, v in sorted(stats.items()) if k.startswith("exam:")})
    print("examples with nothing found:", [f"{n[:28]} ({k})" for n, k in none[:12]])
