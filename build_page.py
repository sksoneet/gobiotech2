#!/usr/bin/env python3
"""Build the website page: injects data/institutes.json into tools/page_template.html.
   python tools/build_page.py [output.html]
"""
import json, pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
data = json.loads((root / "data" / "institutes.json").read_text(encoding="utf-8"))
tpl = (root / "tools" / "page_template.html").read_text(encoding="utf-8")
blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / "site" / "index.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(tpl.replace("/*__DATA__*/null", blob), encoding="utf-8")
print("wrote", out, len(data["institutes"]), "institutes")
