#!/usr/bin/env python3
"""Re-read every source URL in data/institutes.json and report what changed.

It never edits institutes.json. Changes go to reports/ for a human to review.

  python tools/check_sources.py                 # check all, write report
  python tools/check_sources.py --only jnu      # check one institute id
  python tools/check_sources.py --accept        # after review: save new pages as the baseline

First run records a baseline (nothing is "changed" yet).
"""
import argparse, datetime, gzip, hashlib, json, pathlib, re, sys, time
import urllib.request, urllib.error
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "institutes.json"
SNAP = ROOT / "data" / "snapshots"
REPORTS = ROOT / "reports"
UA = "GoBiotechBot/1.0 (+data accuracy checker; contact site owner)"
JACCARD_ALERT = 0.90   # page text this similar or less => flag
MAX_CHARS = 200_000


class TextOnly(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header"}

    def __init__(self):
        super().__init__()
        self.out, self.depth = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth and data.strip():
            self.out.append(data.strip())


def fetch(url, timeout=25, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(5_000_000)
                ctype = r.headers.get("Content-Type", "")
                return raw, ctype, None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (404, 410, 403):
                break
        except Exception as e:  # network, SSL, timeout
            last = type(e).__name__
        time.sleep(2 * (attempt + 1))
    return None, None, last


def to_text(raw, ctype, url):
    if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
        try:  # optional dependency
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join((p.extract_text() or "") for p in reader.pages)[:MAX_CHARS]
        except Exception:
            return "PDF-HASH:" + hashlib.sha256(raw).hexdigest()
    p = TextOnly()
    p.feed(raw.decode("utf-8", "ignore"))
    return re.sub(r"\s+", " ", " ".join(p.out))[:MAX_CHARS]


def sentences(text):
    return {s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n", text) if len(s.strip()) > 20}


def numbers(text):
    return set(re.findall(r"(?:₹|rs\.?|inr)?\s?\d[\d,\.]*\s?(?:lakh|lakhs|l|k|%|seats)?", text.lower()))


def snap_path(inst_id, i):
    return SNAP / f"{inst_id}-{i}.txt.gz"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--accept", action="store_true", help="store current pages as the new baseline")
    ap.add_argument("--data", default=str(DATA))
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    SNAP.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()
    lines, queue, baseline, ok = [], [], 0, 0

    for inst in data["institutes"]:
        if args.only and inst["id"] != args.only:
            continue
        for i, src in enumerate(inst.get("sources", [])):
            url = src["url"]
            raw, ctype, err = fetch(url)
            if err:
                queue.append({"id": inst["id"], "url": url, "issue": f"fetch failed: {err}"})
                lines.append(f"- **{inst['name']}**: could not fetch {url} ({err}). Link may be broken or blocked.")
                continue
            text = to_text(raw, ctype, url)
            path = snap_path(inst["id"], i)
            if not path.exists():
                path.write_bytes(gzip.compress(text.encode("utf-8")))
                baseline += 1
                continue
            old = gzip.decompress(path.read_bytes()).decode("utf-8")
            if old == text:
                ok += 1
                continue
            a, b = sentences(old), sentences(text)
            jac = len(a & b) / max(1, len(a | b))
            na, nb = numbers(old), numbers(text)
            added, removed = sorted(nb - na)[:12], sorted(na - nb)[:12]
            if jac <= JACCARD_ALERT or added or removed:
                queue.append({"id": inst["id"], "url": url, "issue": "content changed",
                              "similarity": round(jac, 3), "numbers_added": added, "numbers_removed": removed})
                lines.append(f"- **{inst['name']}** ({src.get('note','')}): content changed, similarity {jac:.2f}. "
                             f"Numbers added: {added or '-'}; removed: {removed or '-'}. {url}")
            if args.accept:
                path.write_bytes(gzip.compress(text.encode("utf-8")))
        time.sleep(1)  # be polite to servers

    report = ROOT / "reports" / f"changes-{today}.md"
    body = [f"# Source check {today}", "",
            f"Baselines recorded: {baseline}. Unchanged pages: {ok}. Needing review: {len(queue)}.", ""]
    body += lines or ["No changes needing review."]
    report.write_text("\n".join(body) + "\n", encoding="utf-8")
    (ROOT / "reports" / "review_queue.json").write_text(json.dumps(queue, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
