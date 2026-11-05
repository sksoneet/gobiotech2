#!/usr/bin/env python3
"""Compute the GoBiotech Index (GBI) and write data/top20.json.

Run:  python tools/compute_index.py
Inputs : data/institutes.json, data/index_inputs.json (weights and the NIRF 2025 supplement)
Output : data/top20.json  (top 20 for UG, Masters and PhD with the score breakdown)
"""
import json, math, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "data" / "institutes.json").read_text(encoding="utf-8"))
X = json.loads((ROOT / "data" / "index_inputs.json").read_text(encoding="utf-8"))
W = X["weights"]
GOI = "Govt. of India autonomous (IIT, AIIMS, NIT, IISER, IISc)"
LEVELS = {"ug": "UG", "masters": "Masters", "phd": "PhD"}


def nirf_rank(i):
    """Return (label, comparable_rank) or (None, None)."""
    nm = i["name"].lower()
    for e in X["nirf_2025"]:
        if all(m in nm for m in e["match"]):
            ranks = e["ranks"]
            cands = [(r if c == "Overall" else r * X["category_rank_multiplier"], c, r) for c, r in ranks.items()]
            best = min(cands)[0]
            label = "NIRF 2025 " + ", ".join(f"{c} #{r}" for c, r in ranks.items())
            return (label, best)
    t = (i.get("rankings") or {}).get("NIRF", "")
    m = re.search(r"Overall #(\d+)", t)
    if m:
        return (f"NIRF 2025 Overall #{m.group(1)}", int(m.group(1)))
    m = re.search(r"(University|Engineering|Agriculture|Pharmacy) #(\d+)", t)
    if m:
        return (f"NIRF 2025 {m.group(1)} #{m.group(2)}", int(m.group(2)) * X["category_rank_multiplier"])
    if "101\u2013150" in t:
        return ("NIRF 2025 University band 101\u2013150", 125)
    return (None, None)


def standing(i):
    label, r = nirf_rank(i)
    if r is None:
        return X["unranked_standing_score"], "no published NIRF rank found"
    return max(0.0, 100 * (1 - math.log(max(r, 1)) / math.log(200))), label


def status_score(i):
    t = i["type"].lower()
    ag = set(i["agencies"])
    if GOI in ag or "national importance" in t or "eminence" in t or "tifr" in t or "icar" in t or "csir laboratory" in t or "icmr research" in t or "dst autonomous" in t or "dbt autonomous" in t:
        return 100, "institute of national importance or a national research institute"
    if "central university" in t or "central agricultural" in t:
        return 85, "central university"
    if i["ownership"] == "State / UT Government":
        return 65, "state or UT public institution"
    if "deemed" in t or "university" in t:
        return 55, "private or deemed university"
    return 45, "private college"


def programme(i, lv):
    e = i["eligibility"]
    ag = set(i["agencies"])
    if lv == "ug":
        t = ((e.get("ug") or "") + " " + i["programmes"]).lower()
        if "jee advanced" in t or "iisers" in t or "aptitude test (iat)" in t:
            return 100, "UG admission through JEE Advanced or the IISER aptitude test"
        if any(k in t for k in ("jee main", "josaa", "cuet", "neet", "kcet", "comedk", "tneA".lower(), "eamcet", "wbjee", "mht-cet")):
            return 85, "UG admission through a national or state common test"
        return 65, "UG programme with an institute-level route"
    if lv == "masters":
        t = ((e.get("masters") or "") + " " + " ".join(i["seats"]) + " " + i["programmes"]).lower()
        if "gat-b" in t or "dbt" in t:
            return 95, "DBT-supported M.Sc/M.Tech filled through GAT-B"
        if "iit jam" in t or " gate" in t or "gate " in t:
            return 90, "PG admission through IIT JAM or GATE"
        if "cuet" in t:
            return 85, "PG admission through CUET (PG)"
        return 65, "PG programme with an institute-level route"
    t = (e.get("phd") or "").lower()
    research = bool(ag & {"CSIR", "ICMR", "DST", "DBT", GOI})
    if ("jrf" in t or "fellowship" in t) and research:
        return 100, "PhD with a national fellowship route at a national research body"
    if "jrf" in t or "fellowship" in t or " net" in t or "gate" in t:
        return 85, "PhD with a national fellowship or test route"
    return 70, "PhD programme with an institute-level route (or details not yet collected)"


def support(i):
    txt = (" ".join(i["seats"]) + " " + i["fees"] + " " + " ".join(str(v or "") for v in i["eligibility"].values())).lower()
    s = 30
    if str(i["hostel"]).lower().startswith("yes"):
        s += 30
    if any(k in txt for k in ("stipend", "fellowship", "scholarship")):
        s += 20
    if set(i["agencies"]) & {"DBT", "CSIR", "ICMR", "DST", "ICAR", GOI}:
        s += 20
    return min(100, s)


OFFICIAL = re.compile(r"\.(ac\.in|res\.in|gov\.in|nic\.in|edu|edu\.in|org\.in)(/|$)|icmr\.gov|iit|nit|aiims|iiser", re.I)


def confidence(i):
    s = 30
    if i["status"] == "partly_sourced":
        s += 30
    if i["eligibility"].get("basis") == "sourced":
        s += 20
    if any(OFFICIAL.search(x["url"]) for x in i["sources"]) or i.get("last_checked"):
        s += 20
    return min(100, s)


out = {"name": X["name"], "weights": W, "notes": X["notes"], "generated": D.get("generated")}
for lv, deg in LEVELS.items():
    rows = []
    for i in D["institutes"]:
        if deg not in i["degrees"]:
            continue
        if lv == "ug" and ((i["streams"].get("ug") or "").lower().startswith("allied") or "no b.sc biotechnology" in i["programmes"].lower()):
            continue
        st, st_why = standing(i)
        ss, ss_why = status_score(i)
        ps, ps_why = programme(i, lv)
        sp, cf = support(i), confidence(i)
        total = (W["national_standing"] * st + W["institution_status"] * ss + W["programme_strength"] * ps + W["support"] * sp + W["data_confidence"] * cf) / 100
        rows.append({"id": i["id"], "name": i["name"], "state": i["state"], "city": i["city"], "ownership": i["ownership"], "agencies": i["agencies"],
                     "search": i["name"], "unranked": st_why.startswith("no published"), "score": round(total, 1),
                     "parts": {"national_standing": round(st), "institution_status": ss, "programme_strength": ps, "support": sp, "data_confidence": cf},
                     "why": f"{st_why}; {ss_why}; {ps_why}"})
    iis = [r for r in rows if r["name"].startswith("Indian Institute of Science Education and Research")]
    if iis:
        keep = dict(max(iis, key=lambda r: r["parts"]["national_standing"]))
        keep.update({"id": "iiser-network", "name": f"IISER network ({len(iis)} campuses: Pune, Kolkata, Mohali, Bhopal, Thiruvananthapuram, Tirupati, Berhampur)", "state": "Multiple states", "city": "Seven campuses", "search": "IISER"})
        rows = [r for r in rows if r not in iis] + [keep]
    rows.sort(key=lambda r: (-r["score"], -r["parts"]["national_standing"], r["name"]))
    for n, r in enumerate(rows[:20], 1):
        r["rank"] = n
    top = rows[:20]
    for n, r in enumerate(top):
        r["tie"] = (n > 0 and top[n - 1]["score"] == r["score"]) or (n + 1 < len(rows) and rows[n + 1]["score"] == r["score"])
    out[lv] = rows[:20]
    if lv in ("masters", "phd"):
        nu = [r for r in rows if r["unranked"] and r["parts"]["institution_status"] == 100 and not r["id"] == "iiser-network"]
        nu.sort(key=lambda r: (-r["parts"]["programme_strength"], -r["parts"]["support"], -r["parts"]["data_confidence"], r["name"]))
        top_ids = {r["id"] for r in rows[:20]}
        out.setdefault("notable_unranked", {})[lv] = [dict(r, in_top20=r["id"] in top_ids) for r in nu[:24]]
    out[lv + "_candidates"] = len(rows)
(ROOT / "data" / "top20.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
for lv in LEVELS:
    print(f"\n=== Top 20 {lv.upper()} (of {out[lv + '_candidates']} candidates)")
    for r in out[lv]:
        p = r["parts"]
        print(f"{r['rank']:>2}. {r['score']:5.1f}  {r['name'][:62]:62} | {r['state'][:12]:12} | N{p['national_standing']:>3} S{p['institution_status']:>3} P{p['programme_strength']:>3} U{p['support']:>3} C{p['data_confidence']:>3}")
