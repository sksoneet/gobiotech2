#!/usr/bin/env python3
"""Checks data/institutes.json before the site is built. Exits 1 on problems."""
import json, pathlib, re, sys, collections
root = pathlib.Path(__file__).resolve().parent.parent
d = json.loads((root / "data" / "institutes.json").read_text(encoding="utf-8"))
OWN = {"Central Government", "State / UT Government", "Private"}
LEVELS = {"UG", "Masters", "PhD"}
AGENCIES = {"DBT", "DST", "CSIR", "ICMR", "ICAR", "Govt. of India autonomous (IIT, AIIMS, NIT, IISER, IISc)"}
errs, ids = [], collections.Counter(i.get("id") for i in d["institutes"])
for i in d["institutes"]:
    n = i.get("name", "?")
    for k in ("id", "name", "state", "city", "type", "ownership", "agencies", "address", "degrees", "programmes", "fees", "hostel", "website", "eligibility", "status", "sources"):
        if k not in i: errs.append(f"{n}: missing field {k}")
    if i.get("ownership") not in OWN: errs.append(f"{n}: ownership must be one of {sorted(OWN)}")
    if not set(i.get("agencies", [])) <= AGENCIES: errs.append(f"{n}: agencies must be a subset of {sorted(AGENCIES)}")
    if not set(i.get("degrees", [])) <= LEVELS or not i.get("degrees"): errs.append(f"{n}: degrees must be a non-empty subset of {sorted(LEVELS)}")
    if ids[i.get("id")] > 1: errs.append(f"{n}: duplicate id")
    for s in i.get("sources", []):
        if not re.match(r"^https?://\S+$", s.get("url", "")): errs.append(f"{n}: bad source URL {s.get('url')!r}")
print(f"{len(d['institutes'])} institutes checked, {len(errs)} problems")
for e in errs: print(" -", e)
sys.exit(1 if errs else 0)
