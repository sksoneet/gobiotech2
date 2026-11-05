#!/usr/bin/env python3
"""Re-read every source URL in data/institutes.json and report what changed.

It never edits institutes.json. Everything goes to reports/ for a human to review.

  python tools/check_sources.py                 # check all, write reports
  python tools/check_sources.py --only jnu      # check one institute id
  python tools/check_sources.py --accept        # after review: save current pages as the new baseline

Design for ~400+ unique links:
  * each unique URL is fetched once, even if many institutes cite it;
  * fetches run in parallel (12 workers) but at most 2 at a time per website, with a short pause;
  * short timeouts (15 s) and one retry, so a dead site cannot stall the run;
  * the first run records baselines and reports only broken links.
Outputs: reports/changes-DATE.md (human summary), reports/link_status.csv (every URL),
reports/review_queue.json (items needing a person).
"""
import argparse, csv, datetime, gzip, hashlib, json, pathlib, re, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "institutes.json"
SNAP = ROOT / "data" / "snapshots"
REPORTS = ROOT / "reports"
UA = "Mozilla/5.0 (compatible; GoBiotechBot/1.0; data accuracy checker)"
JACCARD_ALERT = 0.90
MAX_CHARS = 200_000
WORKERS, PER_HOST, TIMEOUT, RETRIES, PAUSE = 12, 2, 15, 1, 0.4

_host_locks = defaultdict(lambda: threading.Semaphore(PER_HOST))
_lock_guard = threading.Lock()


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


def host_lock(url):
    host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    with _lock_guard:
        return _host_locks[host]


def fetch(url):
    last = None
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read(5_000_000), r.headers.get("Content-Type", ""), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (404, 410, 403, 401):
                break
        except Exception as e:
            last = type(e).__name__
        time.sleep(1.5 * (attempt + 1))
    return None, None, last


def to_text(raw, ctype, url):
    if "pdf" in ctype.lower() or url.lower().split("?")[0].endswith(".pdf"):
        try:
            import io
            from pypdf import PdfReader
            return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)[:MAX_CHARS]
        except Exception:
            return "PDF-HASH:" + hashlib.sha256(raw).hexdigest()
    p = TextOnly()
    p.feed(raw.decode("utf-8", "ignore"))
    return re.sub(r"\s+", " ", " ".join(p.out))[:MAX_CHARS]


def sentences(text):
    return {s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n", text) if len(s.strip()) > 20}


def numbers(text):
    return set(re.findall(r"(?:₹|rs\.?|inr)?\s?\d[\d,\.]*\s?(?:lakh|lakhs|l|k|%|seats)?", text.lower()))


def snap_path(url):
    return SNAP / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt.gz")


def check_one(url):
    """Returns dict(status, text, err)."""
    with host_lock(url):
        raw, ctype, err = fetch(url)
        time.sleep(PAUSE)
    if err:
        return {"url": url, "status": "error", "err": err}
    text = to_text(raw, ctype, url)
    if len(text) < 200 and not text.startswith("PDF-HASH"):
        return {"url": url, "status": "thin", "text": text, "err": "page text is almost empty (may need JavaScript or blocks bots)"}
    return {"url": url, "status": "ok", "text": text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--accept", action="store_true")
    ap.add_argument("--data", default=str(DATA))
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    SNAP.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()

    users = defaultdict(list)  # url -> [institute names]
    notes = {}
    for inst in data["institutes"]:
        if args.only and inst["id"] != args.only:
            continue
        for s in inst.get("sources", []):
            users[s["url"]].append(inst["name"])
            notes.setdefault(s["url"], s.get("note", ""))
    urls = sorted(users)
    print(f"Checking {len(urls)} unique URLs for {sum(len(v) for v in users.values())} source links ...", flush=True)

    results = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(check_one, u): u for u in urls}
        for n, f in enumerate(as_completed(futs), 1):
            r = f.result()
            results[r["url"]] = r
            if n % 25 == 0:
                print(f"  {n}/{len(urls)} done", flush=True)

    queue, lines, rows = [], [], []
    baseline = unchanged = 0
    for u in urls:
        r = results[u]
        who = "; ".join(users[u][:3]) + (f" (+{len(users[u]) - 3} more)" if len(users[u]) > 3 else "")
        status, detail = r["status"], r.get("err", "")
        if r["status"] == "error":
            queue.append({"url": u, "institutes": users[u], "issue": f"fetch failed: {r['err']}"})
            lines.append(f"- **Broken or blocked** ({r['err']}): {u} \u2014 used by {who}")
        else:
            path = snap_path(u)
            text = r["text"]
            if r["status"] == "thin":
                queue.append({"url": u, "institutes": users[u], "issue": "page looks empty to the checker"})
                lines.append(f"- **Looks empty** (may need JavaScript or blocks bots): {u} \u2014 used by {who}")
            if not path.exists():
                path.write_bytes(gzip.compress(text.encode("utf-8")))
                baseline += 1
                status = "baseline" if r["status"] == "ok" else status
            else:
                old = gzip.decompress(path.read_bytes()).decode("utf-8")
                if old == text:
                    unchanged += 1
                    status = "unchanged" if r["status"] == "ok" else status
                elif r["status"] == "ok":
                    a, b = sentences(old), sentences(text)
                    jac = len(a & b) / max(1, len(a | b))
                    na, nb = numbers(old), numbers(text)
                    added, removed = sorted(nb - na)[:12], sorted(na - nb)[:12]
                    if jac <= JACCARD_ALERT or added or removed:
                        status = "changed"
                        detail = f"similarity {jac:.2f}; numbers added {added or '-'}; removed {removed or '-'}"
                        queue.append({"url": u, "institutes": users[u], "issue": "content changed", "similarity": round(jac, 3), "numbers_added": added, "numbers_removed": removed})
                        lines.append(f"- **Changed** ({detail}): {u} \u2014 used by {who}")
                    else:
                        unchanged += 1
                        status = "unchanged"
                    if args.accept:
                        path.write_bytes(gzip.compress(text.encode("utf-8")))
        rows.append([u, status, detail, "; ".join(users[u]), notes.get(u, "")])

    with open(REPORTS / "link_status.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["url", "status", "detail", "institutes", "note"])
        w.writerows(rows)
    broken = sum(1 for r in rows if r[1] == "error")
    body = [f"# Source check {today}", "",
            f"URLs checked: {len(urls)}. Baselines recorded: {baseline}. Unchanged: {unchanged}. Broken or blocked: {broken}. Needing review: {len(queue)}.", ""]
    body += sorted(lines) or ["Nothing needs review."]
    (REPORTS / f"changes-{today}.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    (REPORTS / "review_queue.json").write_text(json.dumps(queue, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(body[:40]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
