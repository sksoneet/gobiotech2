# GoBiotech data and update workflow

- `data/institutes.json` is the single source of truth. Every institute has `sources` (URLs), `data_collected` and `last_checked`.
- `tools/check_sources.py` re-reads each source URL, compares with the saved snapshot and writes `reports/changes-DATE.md`
  and `reports/review_queue.json`. It never edits the data. Fee, seat and percentage changes are listed as numbers added/removed.
- `.github/workflows/check-sources.yml` runs it every Monday and opens an issue when something needs review.
- `tools/build_page.py` builds the website page from the JSON (`python tools/build_page.py`).

## Review loop
1. Read the issue / report. 2. Open the source and confirm the change. 3. Edit `data/institutes.json`
(set `last_checked`, keep `sources`). 4. Run `python tools/check_sources.py --accept` to save the new baseline. 5. Rebuild and publish.

## Adding a state
Add objects to `data/institutes.json` with at least one source URL each. Prefer the institute's own prospectus or
admission notice; aggregator pages (Careers360 etc.) are noisy and can change for unrelated reasons.
Mark `status: "needs_verification"` until an official source is attached.

## Known limits
- Aggregator pages change often (ads, reviews), so expect some false alarms. Official PDFs and notices are far more reliable.
- Some source URLs came from search results and may be truncated; the checker reports them as "could not fetch" so they get fixed.
- Pages that need JavaScript to show content may look empty to the checker.

## Institution type menu
Every record needs `ownership`: `Central Government` (central universities, IITs/NITs, institutes of national importance,
ICAR and other central bodies), `State / UT Government` (state universities and government colleges, including state
agricultural and veterinary universities) or `Private` (private and private deemed universities, aided/private colleges).
`tools/validate_data.py` checks this before every site build.

## Sponsoring-agency menu
`agencies` is a list (it can be empty) of: `DBT`, `DST`, `CSIR`, `ICMR`, `ICAR`, or
`Govt. of India autonomous (IIT, AIIMS, NIT, IISER, IISc)`. Add a tag only when a source page shows the agency runs, funds or
supports the institute or its biotechnology programme (for example DBT-supported M.Sc seats admitted through GAT-B).
DST and ICMR institutes have not been added yet.
