# ARTÉ Properties website

Static site for artepropertiesdubai.com. Netlify builds it from this repo (`python3 build.py` → `site/`).

## How listings stay up to date
- `.github/workflows/sync-listings.yml` runs every 3 hours. It pulls Nav Bamrah's live listings from Property Finder (`scripts/sync_pf.py`), updates `data/listings.json`, and pushes. Netlify then redeploys.
- Instant refresh: GitHub → Actions → "Sync Property Finder listings" → Run workflow.
- If Property Finder can't be read, the run fails safe: listings stay as they were and GitHub emails a failure notice.
- Hand-written titles/summaries live in `data/overrides.json`, keyed by Property Finder listing id. Anything not overridden is generated from the Property Finder text.
- Off-plan launches (not on Property Finder) are kept in `data/listings.json` with `"source": "reelly"`; the sync never touches them.

## Other edits
- Phone, WhatsApp, email, address, ORN: `data/site.json`
- Area guides: `data/areas.json`
- Look and feel: `src/style.css`; behaviour: `src/app.js`; page templates: `build.py`

## Before launch
- Add the company ORN to `data/site.json`.
- Add Trakheesi permit numbers on Property Finder (the sync copies them across).
