#!/usr/bin/env python3
"""
tools/build_page.py
Builds site/index.html by injecting:
  - data/institutes.json
  - data/top20.json
  - data/advanced_biotech.json
into tools/page_template.html.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "institutes.json"
GBI_FILE = ROOT / "data" / "top20.json"
ADVANCED_FILE = ROOT / "data" / "advanced_biotech.json"
TEMPLATE_FILE = ROOT / "tools" / "page_template.html"
OUTPUT_DIR = ROOT / "site"
OUTPUT_FILE = OUTPUT_DIR / "index.html"

def build():
    print(f"Reading institutes from {DATA_FILE}...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        institutes_data = json.load(f)

    gbi_data = {}
    if GBI_FILE.exists():
        print(f"Reading GBI scores from {GBI_FILE}...")
        with open(GBI_FILE, "r", encoding="utf-8") as f:
            gbi_data = json.load(f)

    advanced_data = {}
    if ADVANCED_FILE.exists():
        print(f"Reading Advanced Biotech data from {ADVANCED_FILE}...")
        with open(ADVANCED_FILE, "r", encoding="utf-8") as f:
            advanced_data = json.load(f)
    else:
        print("Warning: data/advanced_biotech.json not found.")

    print(f"Reading template from {TEMPLATE_FILE}...")
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # Minify JSON for safe embedding
    page = template.replace("__INSTITUTES_DATA__", json.dumps(institutes_data, separators=(",", ":")))
    page = page.replace("__GBI_DATA__", json.dumps(gbi_data, separators=(",", ":")))
    page = page.replace("__ADVANCED_BIOTECH_DATA__", json.dumps(advanced_data, separators=(",", ":")))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"Build complete -> {OUTPUT_FILE} ({len(page):,} bytes).")

if __name__ == "__main__":
    build()
