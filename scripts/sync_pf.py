#!/usr/bin/env python3
"""Pull Nav Bamrah's live listings from Property Finder into data/listings.json.

Runs on a schedule in GitHub Actions. Fails safe: if Property Finder can't be read,
or returns no listings, the existing listings are kept and the script exits with code 2
(the workflow then emails a warning and the site stays as it was).

Hand-written titles, summaries and highlights in data/overrides.json win over the
generated ones, matched by Property Finder listing id.
"""
import json, re, sys, time, urllib.request, urllib.error
from pathlib import Path

AGENT_ID = "261418"
ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "data/listings.json"
OVERRIDES = ROOT / "data/overrides.json"
API = ("https://www.propertyfinder.ae/api/pwa/property/search?sorting.sort=featured&filters.category_id={cat}"
       "&filters.furnished=all&pagination.page={page}&filters.utilities_price_type=notSelected"
       "&filters.price_type=price_type_any&pagination.limit=20&filters.agent_id=" + AGENT_ID + "&locale=en")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
           "Accept": "application/json", "Accept-Language": "en-GB,en;q=0.9",
           "Referer": f"https://www.propertyfinder.ae/en/agent/nav-bamrah-{AGENT_ID}"}
AREAS = [("dubai marina", "dubai-marina"), ("jumeirah beach residence", "dubai-marina"), ("downtown", "downtown-dubai"),
         ("business bay", "business-bay"), ("the springs", "the-springs"), ("dubai hills", "dubai-hills-estate"),
         ("creek harbour", "dubai-creek-harbour")]
DROP_WORDS = re.compile(r"\b(high roi|guaranteed)\b", re.I)  # no promised returns in adverts
NUM = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven"}

def fetch(cat, page):
    req = urllib.request.Request(API.format(cat=cat, page=page), headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as err:
            print(f"  attempt {attempt+1} failed: {err}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("Property Finder could not be read")

def slugify(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def summary(desc):
    d = re.sub(r"\s+", " ", desc or "").strip()
    d = re.sub(r"^(Arte Properties is (proud|pleased|delighted) to (present|offer)|Brought to you by Arte Properties,)\s*", "", d, flags=re.I)
    d = re.sub(r"^this\b", "A", d, flags=re.I)
    d = re.sub(r"\b(sq|ft|approx|no)\.", lambda m: m.group(1) + "\u2024", d, flags=re.I)  # keep abbreviations from splitting
    sents = [x.replace("\u2024", ".") for x in re.split(r"(?<=[.!?])\s+", d)]
    out = " ".join(sents[:2])[:420]
    return out[:1].upper() + out[1:] if out else ""

def gallery(url):
    """Full-size photos from the listing's own page (up to 16)."""
    if not url: return []
    try:
        req = urllib.request.Request(url, headers={**HEADERS, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = r.read().decode("utf-8", "ignore")
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
        imgs = json.loads(m.group(1))["props"]["pageProps"]["propertyResult"]["property"]["images"]["property"]
        return [i.get("full", i.get("medium", "")).split("?")[0] for i in imgs if i.get("full") or i.get("medium")][:16]
    except Exception as err:
        print(f"  gallery skipped for {url}: {err}")
        return []

def convert(p):
    loc = p.get("location") or {}
    path = (loc.get("path_name") or "")
    parts = [x.strip() for x in path.split(",") if x.strip() and x.strip() != "Dubai"]
    area = parts[-1] if parts else "Dubai"
    if len(parts) >= 2 and parts[0] in ("Jumeirah Lake Towers",) : area = parts[1] + ", JLT"
    hay = (path + " " + (loc.get("full_name") or "")).lower()
    area_slug = next((s for k, s in AREAS if k in hay), "")
    beds = int(p["bedrooms"]) if str(p.get("bedrooms", "")).isdigit() else None
    baths = int(p["bathrooms"]) if str(p.get("bathrooms", "")).isdigit() else None
    rent = p.get("category_id") == 2 or (p.get("price") or {}).get("period") in ("yearly", "monthly")
    price = (p.get("price") or {}).get("value")
    if (p.get("price") or {}).get("period") == "monthly" and price: price = price * 12
    ptype = p.get("property_type") or "Apartment"
    stage = "offplan" if p.get("completion_status") == "off_plan" else "ready"
    building = loc.get("name") or area
    hl = [h.strip() for h in (p.get("title") or "").split("|") if h.strip() and not DROP_WORDS.search(h)]
    title = (f"{NUM.get(beds, beds)}-bedroom {ptype.lower()}" if beds else ptype) + (f" in {building}" if building else "")
    return {
        "slug": slugify(f"{building}-{beds or ptype}-bed-{'rent' if rent else 'sale'}-{p['id']}"),
        "pf_id": str(p["id"]), "source": "propertyfinder",
        "status": "rent" if rent else "sale", "stage": stage,
        "title": title, "building": building, "area": area, "area_slug": area_slug,
        "type": ptype, "beds": beds, "baths": baths, "sqft": (p.get("size") or {}).get("value"),
        "price": None if (p.get("price") or {}).get("is_hidden") else price,
        "furnished": {"YES": True, "NO": False}.get(p.get("furnished")),
        "highlights": hl[:4], "amenities": (p.get("amenity_names") or [])[:10],
        "summary": summary(p.get("description")), "permit": p.get("rera") or "",
        "images": [i.get("medium", "").split("?")[0].replace("/668x452.", "/1312x894.") for i in (p.get("images") or []) if i.get("medium")],
        "thumb": next((i.get("medium", "").split("?")[0] for i in (p.get("images") or []) if i.get("medium")), ""),
        "url": p.get("share_url", ""),
    }

def main():
    current = json.loads(LISTINGS.read_text())
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    keep = [l for l in current if l.get("source") != "propertyfinder"]  # off-plan launches etc.
    live = []
    try:
        for cat in (1, 2):  # 1 = sale, 2 = rent
            page = 1
            while True:
                data = fetch(cat, page)
                rows = [l["property"] for l in data.get("listings", []) if l.get("property")]
                live += [convert(p) for p in rows]
                meta = data.get("meta") or {}
                if page >= (meta.get("page_count") or 1) or not rows: break
                page += 1
    except Exception as err:
        print(f"SYNC FAILED, keeping existing listings: {err}"); sys.exit(2)
    if not live:
        print("Property Finder returned no listings, keeping existing ones to be safe."); sys.exit(2)
    for l in live:
        l.pop("url", None)
        l.update(overrides.get(l["pf_id"], {}))
    LISTINGS.write_text(json.dumps(live + keep, indent=1, ensure_ascii=False) + "\n")
    print(f"Synced {len(live)} Property Finder listings (+{len(keep)} kept).")

if __name__ == "__main__":
    main()
