#!/usr/bin/env python3
"""Builds the ARTÉ Properties static site into ./site from ./data and ./src.
Edit data/listings.json, data/areas.json or data/site.json, then run:  python3 build.py
"""
import json, random, html, shutil, re
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "site"
S = json.loads((ROOT / "data/site.json").read_text())
L = json.loads((ROOT / "data/listings.json").read_text())
A = json.loads((ROOT / "data/areas.json").read_text())
AREA = {a["slug"]: a for a in A}
e = lambda s: html.escape(str(s), quote=True)
random.seed(1)

# ---------- formatting ----------
def aed(n):
    if n is None: return "Price on request"
    if n >= 1_000_000:
        v = f"{n/1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"AED {v}M"
    return f"AED {n:,.0f}"

def price_html(l):
    if l["price"] is None: return '<span class="price">Price on request</span>'
    pre = '<small>From </small>' if l.get("price_from") else ''
    suf = ' <small>/ year</small>' if l["status"] == "rent" else ''
    return f'<span class="price">{pre}{e(aed(l["price"]))}{suf}</span>'

def beds_txt(l):
    if l["type"] == "Office": return "Office"
    if l.get("beds") is None: return None
    b = l["beds"]; mx = l.get("beds_max")
    if mx: return f"{b}–{mx} beds"
    return "Studio" if b == 0 else f"{b} bed" + ("s" if b > 1 else "")

def sqft_txt(l):
    if not l.get("sqft"): return None
    if l.get("sqft_max"): return f'{l["sqft"]:,}–{l["sqft_max"]:,} sq ft'
    return f'{"from " if l.get("price_from") else ""}{l["sqft"]:,} sq ft'

def specs(l):
    out = [beds_txt(l)]
    if l.get("baths"): out.append(f'{l["baths"]} bath' + ("s" if l["baths"] > 1 else ""))
    out.append(sqft_txt(l))
    if l.get("handover"): out.append("Handover " + l["handover"])
    return "".join(f"<span>{e(x)}</span>" for x in out if x)

# ---------- drawings ----------
def facade(seed, kind="Apartment", label=""):
    """A lit building at dusk, used when a listing has no photo yet."""
    r = random.Random(seed)
    hue = r.choice(["#2a2230", "#232a33", "#2c2627", "#20262c"])
    parts = [f'<svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
             f'<defs><linearGradient id="g{seed}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#141820"/>'
             f'<stop offset=".62" stop-color="{hue}"/><stop offset="1" stop-color="#c4654f"/></linearGradient></defs>'
             f'<rect width="400" height="300" fill="url(#g{seed})"/>']
    # distant skyline
    x = 0
    while x < 400:
        w = r.randint(18, 40); h = r.randint(40, 120)
        parts.append(f'<rect x="{x}" y="{240-h}" width="{w}" height="{h+60}" fill="#191d24" opacity=".85"/>')
        x += w + r.randint(2, 8)
    if kind == "Villa":
        parts.append('<rect x="70" y="170" width="260" height="90" fill="#101317"/>'
                     '<rect x="120" y="128" width="170" height="46" fill="#14181d"/>'
                     '<rect x="60" y="164" width="280" height="8" fill="#d6c2a0" opacity=".35"/>'
                     '<rect x="112" y="122" width="186" height="7" fill="#d6c2a0" opacity=".3"/>')
        for i in range(5):
            parts.append(f'<rect x="{88+i*48}" y="190" width="34" height="46" fill="#f1c98f" opacity="{r.uniform(.35,.85):.2f}"/>')
        for i in range(3):
            parts.append(f'<rect x="{136+i*50}" y="138" width="32" height="26" fill="#f1c98f" opacity="{r.uniform(.3,.8):.2f}"/>')
        parts.append('<rect x="0" y="258" width="400" height="42" fill="#0d1013"/><rect x="40" y="262" width="320" height="12" rx="3" fill="#3e8fa0" opacity=".55"/>')
    else:
        tw = 150 if kind == "Office" else 120; tx = 200 - tw // 2; top = r.randint(18, 50)
        parts.append(f'<rect x="{tx}" y="{top}" width="{tw}" height="{300-top}" fill="#101317"/>'
                     f'<rect x="{tx}" y="{top}" width="4" height="{300-top}" fill="#d6c2a0" opacity=".45"/>')
        cols, rows = (8, 20) if kind == "Office" else (6, 18)
        cw = (tw - 20) / cols; rh = (300 - top - 20) / rows
        for j in range(rows):
            for i in range(cols):
                if r.random() < (.75 if kind == "Office" else .45):
                    parts.append(f'<rect x="{tx+12+i*cw:.1f}" y="{top+12+j*rh:.1f}" width="{cw-5:.1f}" height="{rh-5:.1f}" fill="#f1c98f" opacity="{r.uniform(.2,.9):.2f}"/>')
        parts.append('<rect x="0" y="282" width="400" height="18" fill="#0b0e11"/>')
    parts.append('</svg>')
    return "".join(parts)

def skyline(seed=7, w=1600, h=900, spire=True):
    r = random.Random(seed)
    g = [f'<svg class="sky" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMax slice" aria-hidden="true">'
         '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#141a24"/><stop offset=".3" stop-color="#3a2c40"/>'
         '<stop offset=".5" stop-color="#9a5150"/><stop offset=".62" stop-color="#e2725b"/><stop offset=".72" stop-color="#f6b993"/></linearGradient>'
         '<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a2a30"/><stop offset="1" stop-color="#0e1216"/></linearGradient>'
         '<linearGradient id="shade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#101417" stop-opacity=".88"/><stop offset=".5" stop-color="#101417" stop-opacity=".15"/><stop offset="1" stop-color="#101417" stop-opacity="0"/></linearGradient>'
         '<linearGradient id="floor" x1="0" y1="0" x2="0" y2="1"><stop offset=".7" stop-color="#101417" stop-opacity="0"/><stop offset="1" stop-color="#101417"/></linearGradient>'
         '</defs>'
         f'<rect width="{w}" height="{h}" fill="url(#sky)"/>'
         f'<circle cx="{w*.7:.0f}" cy="{h*.66:.0f}" r="70" fill="#ffd3ad" opacity=".55"/>']
    horizon = int(h * .72)
    city = []
    def layer(color, hmin, hmax, wmin, wmax, lit):
        x = -20
        while x < w:
            bw = r.randint(wmin, wmax); bh = r.randint(hmin, hmax)
            y = horizon - bh
            city.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{color}"/>')
            if r.random() < .3:
                city.append(f'<rect x="{x+bw*.3:.0f}" y="{y-bh*.12:.0f}" width="{bw*.4:.0f}" height="{bh*.12:.0f}" fill="{color}"/>')
            if lit:
                for j in range(4, bh - 6, 14):
                    for i in range(5, bw - 6, 11):
                        if r.random() < .16:
                            city.append(f'<rect x="{x+i}" y="{y+j}" width="5" height="7" fill="#f6cf98" opacity="{r.uniform(.35,.95):.2f}"/>')
            x += bw + r.randint(2, 14)
    layer("#3b2b38", 60, 190, 30, 70, False)
    layer("#231f29", 40, 260, 26, 64, False)
    if spire:  # a stepped needle tower, Downtown's signature silhouette
        cx = int(w * .74); base = horizon
        steps = [(64, 120), (50, 110), (38, 100), (28, 90), (18, 80), (10, 70), (4, 60)]
        y = base
        for sw, sh in steps:
            city.append(f'<rect x="{cx-sw/2:.0f}" y="{y-sh}" width="{sw}" height="{sh}" fill="#171a21"/>')
            y -= sh
        city.append(f'<rect x="{cx-1}" y="{y-60}" width="2" height="60" fill="#171a21"/><circle cx="{cx}" cy="{y-60}" r="2.5" fill="#ff8f75"/>')
    layer("#14171c", 30, 170, 34, 80, True)
    body = "".join(city)
    g.append(f'<g id="city">{body}</g>')
    g.append(f'<rect y="{horizon}" width="{w}" height="{h-horizon}" fill="url(#sea)"/>')
    g.append(f'<g opacity=".22" transform="translate(0 {2*horizon}) scale(1 -1)">{body}</g>')
    for i in range(14):
        yy = horizon + 12 + i * 14; xx = r.randint(0, w)
        g.append(f'<rect x="{xx}" y="{yy}" width="{r.randint(60,240)}" height="1.4" fill="#f4b48d" opacity="{r.uniform(.15,.45):.2f}"/>')
    g.append(f'<rect width="{w}" height="{h}" fill="url(#shade)"/><rect width="{w}" height="{h}" fill="url(#floor)"/></svg>')
    return "".join(g)

def mini_sky(seed):
    r = random.Random(seed)
    s = [f'<svg viewBox="0 0 400 240" preserveAspectRatio="xMidYMax slice" aria-hidden="true"><defs><linearGradient id="m{seed}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#151a20"/><stop offset=".7" stop-color="#5a3a3e"/><stop offset="1" stop-color="#d9775f"/></linearGradient>'
         f'<linearGradient id="mf{seed}" x1="0" y1="0" x2="0" y2="1"><stop offset=".35" stop-color="#101417" stop-opacity="0"/><stop offset="1" stop-color="#101417" stop-opacity=".95"/></linearGradient></defs>'
         f'<rect width="400" height="240" fill="url(#m{seed})"/>']
    x = 0
    while x < 400:
        bw = r.randint(14, 36); bh = r.randint(20, 150)
        s.append(f'<rect x="{x}" y="{200-bh}" width="{bw}" height="{bh+40}" fill="{r.choice(["#191c23","#1f1d26","#14171c"])}"/>')
        x += bw + r.randint(1, 6)
    s.append(f'<rect width="400" height="240" fill="url(#mf{seed})"/></svg>')
    return "".join(s)

def seed_of(s): return sum(ord(c) * (i + 1) for i, c in enumerate(s)) % 100000

def photo(l, i=0):
    ims = l.get("images") or []
    img = f'<img src="{e(ims[i])}" alt="{e(l["title"])}, {e(l["building"])}" loading="lazy" referrerpolicy="no-referrer" data-fallback>' if len(ims) > i else ""
    return facade(seed_of(l["slug"]), l["type"]) + img

# ---------- shared chrome ----------
WA_ICON = '<svg viewBox="0 0 32 32"><path d="M16 3C9 3 3.4 8.6 3.4 15.5c0 2.4.7 4.7 1.9 6.7L3 29l7-2.2c1.9 1 4 1.6 6.1 1.6 7 0 12.6-5.6 12.6-12.5S23 3 16 3zm0 22.9c-1.9 0-3.8-.5-5.4-1.5l-.4-.2-4.1 1.3 1.3-4-.3-.4c-1.1-1.7-1.7-3.6-1.7-5.6C5.4 9.8 10.1 5.1 16 5.1s10.6 4.7 10.6 10.4S21.9 25.9 16 25.9zm5.8-7.8c-.3-.2-1.9-.9-2.2-1-.3-.1-.5-.2-.7.2-.2.3-.8 1-1 1.2-.2.2-.4.2-.7.1-.3-.2-1.3-.5-2.5-1.6-.9-.8-1.6-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.5-.6c.2-.2.2-.3.3-.6.1-.2 0-.4 0-.6l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.3-1.2 1.1-1.2 2.8s1.2 3.2 1.4 3.5c.2.2 2.4 3.6 5.8 5 .8.3 1.4.5 1.9.7.8.3 1.6.2 2.2.1.7-.1 1.9-.8 2.2-1.5.3-.7.3-1.4.2-1.5-.1-.2-.3-.3-.6-.4z"/></svg>'
NAV = [("index.html", "Home"), ("listings.html", "Properties"), ("areas.html", "Area guides"), ("services.html", "Services"), ("about.html", "About"), ("contact.html", "Contact")]

def wa_link(msg): return f'https://wa.me/{S["whatsapp"]}?text=' + re.sub(r"\s", "%20", e(msg))

def page(path, title, desc, body, active="", jsonld=None, og_img=""):
    nav = "".join(f'<a href="{h}"{" aria-current=page" if h == active else ""}>{t}</a>' for h, t in NAV)
    canon = S["domain"] + "/" + ("" if path == "index.html" else path.replace(".html", ""))
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    orn = f' · RERA ORN {e(S["orn"])}' if S["orn"] else ""
    areas_links = "".join(f'<a href="area-{a["slug"]}.html">{e(a["name"])}</a>' for a in A[:5])
    full_title = title if "ARTÉ" in title else f"{title} | ARTÉ Properties"
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full_title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{e(canon)}">
<meta property="og:title" content="{e(full_title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{e(canon)}">{f'<meta property="og:image" content="{e(og_img)}">' if og_img else ''}
<meta name="theme-color" content="#101417"><link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600&family=Marcellus&display=swap">
<link rel="stylesheet" href="style.css">{ld}</head>
<body data-wa="{e(S["whatsapp"])}" data-tel="{e(S["phone_href"])}" data-phone="{e(S["phone"])}">
<header class="top"><div class="wrap"><a class="logo" href="index.html" aria-label="ARTÉ Properties home"><b>ARTÉ</b><span>PROPERTIES</span></a>
<button class="menu-btn" aria-label="Menu" aria-expanded="false">☰</button><nav class="nav">{nav}<a class="btn sm" href="valuation.html" style="margin-left:8px">Free valuation</a></nav></div></header>
<main>{body}</main>
<footer><div class="wrap"><div class="fgrid">
<div><a class="logo" href="index.html"><b>ARTÉ</b><span>PROPERTIES</span></a><p style="margin-top:16px;max-width:34ch">A Dubai brokerage for buying, selling, leasing and managing premium homes.</p>
<p>{e(S["address"])}</p></div>
<div><h4>Properties</h4><a href="listings.html?stage=sale">For sale</a><a href="listings.html?stage=rent">For rent</a><a href="listings.html?stage=offplan">Off-plan</a><a href="valuation.html">Value my property</a></div>
<div><h4>Area guides</h4>{areas_links}<a href="areas.html">All areas</a></div>
<div><h4>Contact</h4><a href="tel:{e(S["phone_href"])}">{e(S["phone"])}</a><a href="mailto:{e(S["email"])}">{e(S["email"])}</a><a href="https://wa.me/{e(S["whatsapp"])}" target="_blank" rel="noopener">WhatsApp</a>
<a href="{e(S["instagram"])}" target="_blank" rel="noopener">Instagram</a><a href="{e(S["facebook"])}" target="_blank" rel="noopener">Facebook</a><a href="{e(S["linkedin"])}" target="_blank" rel="noopener">LinkedIn</a></div>
</div><div class="legal"><span>© 2026 {e(S["legal_name"])}{orn}. Regulated by the Real Estate Regulatory Agency (RERA), Dubai.</span><a href="privacy.html" style="display:inline">Privacy</a></div></div></footer>
<a class="wa" href="https://wa.me/{e(S["whatsapp"])}" target="_blank" rel="noopener" aria-label="Chat on WhatsApp">{WA_ICON}</a>
<script src="app.js"></script></body></html>'''

def form(name, fields, button, hidden=None, extra=""):
    hid = "".join(f'<input type="hidden" name="{e(k)}" value="{e(v)}">' for k, v in (hidden or {}).items())
    return (f'<form class="form" name="{name}" method="POST" data-netlify="true" netlify-honeypot="bot-field">'
            f'<input type="hidden" name="form-name" value="{name}">{hid}'
            f'<p class="hp"><label>Leave empty <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>'
            f'{fields}{extra}<button class="btn" type="submit">{button}</button>'
            f'<p class="small mute" style="margin:0">By sending this you agree to be contacted about your enquiry. See our <a href="privacy.html">privacy notice</a>.</p>'
            f'<div class="note" role="status" aria-live="polite"></div></form>')

def fld(name, label, typ="text", req=True, opts=None, ph="", auto=""):
    rq = " required" if req else ""
    idv = f"f-{name}-{random.randint(1000,9999)}"
    if opts is not None:
        o = "".join(f'<option value="{e(v)}">{e(t)}</option>' for v, t in opts)
        return f'<div><label for="{idv}">{label}</label><select id="{idv}" name="{name}"{rq}>{o}</select></div>'
    if typ == "textarea":
        return f'<div><label for="{idv}">{label}</label><textarea id="{idv}" name="{name}" placeholder="{e(ph)}"{rq}></textarea></div>'
    ac = f' autocomplete="{auto}"' if auto else ""
    return f'<div><label for="{idv}">{label}</label><input id="{idv}" name="{name}" type="{typ}" placeholder="{e(ph)}"{ac}{rq}></div>'

def contact_fields():
    return (f'<div class="row">{fld("name","Full name",auto="name")}{fld("phone","Phone or WhatsApp","tel",auto="tel",ph="+971")}</div>'
            f'{fld("email","Email","email",auto="email")}')

AREAS_OPT = [("", "Any area")] + sorted({(l["area"], l["area"]) for l in L})
TYPES_OPT = [("", "Any type")] + sorted({(l["type"], l["type"]) for l in L})
BEDS_OPT = [("", "Any beds"), ("1", "1 bed"), ("2", "2 beds"), ("3", "3 beds"), ("4", "4+ beds")]

def card(l):
    badge = f'<span class="badge op">{"Off-plan resale" if l.get("source")=="propertyfinder" else "Off-plan"}</span>' if l["stage"] == "offplan" else f'<span class="badge">{"For rent" if l["status"]=="rent" else "For sale"}</span>'
    dev = f' · {e(l["developer"])}' if l.get("developer") else ""
    return (f'<a class="card reveal" href="property-{l["slug"]}.html" data-listing data-status="{l["status"]}" data-stage="{l["stage"]}" data-area="{e(l["area"])}" data-type="{e(l["type"])}" data-beds="{l.get("beds") if l.get("beds") is not None else ""}" data-price="{l["price"] or ""}">'
            f'<div class="ph">{photo(l)}{badge}</div><div class="bd">{price_html(l)}<h3 style="margin:0;font-size:20px">{e(l["title"])}</h3>'
            f'<div class="where">{e(l["building"])}, {e(l["area"])}{dev}</div><div class="specs">{specs(l)}</div></div></a>')

# ---------- pages ----------
pages = {}

why = [("360° service", "Buying, selling, leasing and management under one roof, from first viewing to handover and beyond."),
       ("Personal attention", "A named adviser who learns what you want and only shows you homes that fit."),
       ("Market insight", "Pricing advice grounded in Dubai Land Department transaction data, not guesswork.")]
svc_icons = {
 "Buying and selecting": '<svg viewBox="0 0 40 40"><path d="M6 34V16L20 6l14 10v18H6z"/><path d="M16 34V23h8v11"/></svg>',
 "Selling and valuation": '<svg viewBox="0 0 40 40"><path d="M6 30l9-9 6 6 13-13"/><path d="M26 14h8v8"/></svg>',
 "Leasing": '<svg viewBox="0 0 40 40"><circle cx="13" cy="20" r="6"/><path d="M19 20h16M30 20v6M35 20v4"/></svg>',
 "Off-plan advisory": '<svg viewBox="0 0 40 40"><path d="M8 34V10h12v24M20 34V18h12v16M4 34h32"/></svg>',
 "Property management": '<svg viewBox="0 0 40 40"><rect x="7" y="8" width="26" height="26" rx="2"/><path d="M13 16h14M13 22h14M13 28h8"/></svg>',
 "After-sales care": '<svg viewBox="0 0 40 40"><path d="M20 34s-12-7-12-16a7 7 0 0112-5 7 7 0 0112 5c0 9-12 16-12 16z"/></svg>'}
services = [
 ("Buying and selecting", "We shortlist, arrange and accompany viewings, negotiate on your behalf and manage the transfer at the Dubai Land Department trustee office."),
 ("Selling and valuation", "A pricing view backed by recent comparable sales, professional photography, listing across the major portals and qualified buyers only."),
 ("Leasing", "Tenant search and screening, Ejari registration, cheque collection and renewals for landlords; a shortlist that fits your brief for tenants."),
 ("Off-plan advisory", "Access to launches from Dubai's leading developers, with a clear read on payment plans, escrow and handover timelines."),
 ("Property management", "Maintenance, inspections, service charges and tenant relations handled for owners living in Dubai or overseas."),
 ("After-sales care", "Snagging, utility connections, furnishing and handover support so a purchase becomes a home without the paperwork.")]

def svc_grid(items):
    return '<div class="svc">' + "".join(f'<div class="panel reveal">{svc_icons[t]}<h3>{t}</h3><p class="mute" style="margin:0">{d}</p></div>' for t, d in items) + '</div>'

def area_card(a):
    sub = f'<span class="mute small">AED {a["stats"]["psf"]:,} per sq ft · {a["stats"]["yield"]}% gross yield</span>' if a["stats"] else f'<span class="mute small">{e(a["line"])}</span>'
    return f'<a class="area-card reveal" href="area-{a["slug"]}.html">{mini_sky(seed_of(a["slug"]))}<div><h3>{e(a["name"])}</h3>{sub}</div></a>'

valuation_form = form("valuation", contact_fields() +
    f'<div class="row">{fld("property-location","Community and building",ph="e.g. Sidra 2, Dubai Hills Estate")}{fld("property-type","Property type",opts=[("Apartment","Apartment"),("Villa","Villa"),("Townhouse","Townhouse"),("Penthouse","Penthouse"),("Office","Office")])}</div>'
    f'<div class="row">{fld("bedrooms","Bedrooms",opts=[("Studio","Studio"),("1","1"),("2","2"),("3","3"),("4","4"),("5+","5+")])}{fld("intent","I am looking to",opts=[("Sell","Sell"),("Rent out","Rent out"),("Understand its value","Understand its value")])}</div>',
    "Request my valuation")

home = f'''
<section class="hero">{skyline()}<div class="wrap">
<p class="kicker">Dubai real estate, Business Bay</p>
<h1>Your gateway to exclusive properties in Dubai</h1>
<p class="lead">Homes to buy, rent and invest in across Downtown, Business Bay, Dubai Hills, the Marina and Creek Harbour, with an adviser beside you from first viewing to keys.</p>
<div class="tabs" role="tablist"><button class="tab" role="tab" data-stage="all" aria-selected="true">All</button><button class="tab" role="tab" data-stage="sale" aria-selected="false">Buy</button><button class="tab" role="tab" data-stage="rent" aria-selected="false">Rent</button><button class="tab" role="tab" data-stage="offplan" aria-selected="false">Off-plan</button></div>
<form class="search" id="home-search">{fld("area","Area",req=False,opts=AREAS_OPT)}{fld("type","Type",req=False,opts=TYPES_OPT)}{fld("beds","Bedrooms",req=False,opts=BEDS_OPT)}{fld("min","Min price (AED)","number",False,ph="Any")}{fld("max","Max price (AED)","number",False,ph="Any")}<button class="btn" type="submit">Search</button></form>
</div></section>

<section class="band"><div class="wrap">
<div class="head-row"><div><p class="kicker">Featured</p><h2>Properties we are showing now</h2></div><a class="btn ghost" href="listings.html">View all properties</a></div>
<div class="grid">{"".join(card(l) for l in (sorted([x for x in L if x["status"]=="sale"], key=lambda x: -(x["price"] or 0))[:3] + sorted([x for x in L if x["status"]=="rent"], key=lambda x: -(x["price"] or 0))[:3]))}</div>
</div></section>

<section class="band alt"><div class="wrap split">
<div><p class="kicker">Book a property valuation</p><h2>Unlock your property's potential</h2>
<p class="lead">Tell us about your home and we will come back within one working day with a price range based on recent sales and rents in your building and community.</p>
<ul class="ticks"><li>Comparable sales from Dubai Land Department records</li><li>Achievable rent and yield if you plan to let</li><li>A marketing plan and timeline if you decide to sell</li></ul></div>
<div class="panel">{valuation_form}</div></div></section>

<section class="band"><div class="wrap"><p class="kicker">Why ARTÉ Properties</p><h2>A smaller team, by design</h2>
<div class="points">{"".join(f'<div class="reveal"><div class="n">0{i+1}</div><h3>{t}</h3><p class="mute">{d}</p></div>' for i,(t,d) in enumerate(why))}</div></div></section>

<section class="band alt"><div class="wrap"><div class="head-row"><div><p class="kicker">Area guides</p><h2>Know the community before you view</h2></div><a class="btn ghost" href="areas.html">All area guides</a></div>
<div class="grid">{"".join(area_card(a) for a in A)}</div></div></section>

<section class="band"><div class="wrap"><div class="head-row"><div><p class="kicker">Services</p><h2>Everything from search to after-sales</h2></div><a class="btn ghost" href="services.html">Our services</a></div>
{svc_grid(services[:3])}</div></section>

<section class="band cta-band"><div class="wrap split" style="align-items:center"><div><h2>Speak to an adviser today</h2><p class="lead" style="margin:0">Call, message or visit us in Business Bay. We reply on WhatsApp within the hour during working days.</p></div>
<div style="display:flex;gap:12px;flex-wrap:wrap"><a class="btn" href="https://wa.me/{S["whatsapp"]}" target="_blank" rel="noopener">Message on WhatsApp</a><a class="btn ghost" href="tel:{S["phone_href"]}">Call {e(S["phone"])}</a></div></div></section>'''

agent_ld = {"@context": "https://schema.org", "@type": "RealEstateAgent", "name": S["brand"], "legalName": S["legal_name"], "url": S["domain"],
            "telephone": S["phone"], "email": S["email"], "address": {"@type": "PostalAddress", "addressLocality": "Business Bay, Dubai", "addressCountry": "AE"},
            "sameAs": [S["instagram"], S["facebook"], S["linkedin"]], "areaServed": "Dubai"}
pages["index.html"] = page("index.html", "ARTÉ Properties | Luxury real estate in Dubai", "ARTÉ Properties is a Business Bay brokerage for luxury homes to buy, rent and invest in across Dubai, with free property valuations and off-plan advice.", home, "index.html", agent_ld)

# listings
listing_body = f'''<section class="band" style="padding-bottom:24px"><div class="wrap">
<p class="crumbs"><a href="index.html">Home</a> / Properties</p><h1>Properties in Dubai</h1>
<p class="lead">Homes for sale and rent, updated automatically from our live listings. New stock arrives every week, so tell us what you are after if it is not here yet.</p>
<div class="tabs" role="tablist"><button class="tab" role="tab" data-stage="all">All</button><button class="tab" role="tab" data-stage="sale">For sale</button><button class="tab" role="tab" data-stage="rent">For rent</button><button class="tab" role="tab" data-stage="offplan">Off-plan</button></div>
<form class="search" id="filter" style="max-width:none">{fld("area","Area",req=False,opts=AREAS_OPT)}{fld("type","Type",req=False,opts=TYPES_OPT)}{fld("beds","Bedrooms",req=False,opts=BEDS_OPT)}{fld("min","Min price (AED)","number",False,ph="Any")}{fld("max","Max price (AED)","number",False,ph="Any")}<button class="btn ghost" type="button" id="clear">Clear</button></form>
<p class="mute" style="margin:18px 0 0" id="count" aria-live="polite"></p></div></section>
<section class="band" style="padding-top:12px"><div class="wrap"><div class="grid">{"".join(card(l) for l in L)}</div>
<div class="empty" id="empty" hidden><h3>Nothing matches those filters yet</h3><p>Much of our stock is shared privately before it reaches the portals.</p><a class="btn" href="contact.html">Tell us what you are looking for</a></div></div></section>'''
pages["listings.html"] = page("listings.html", "Properties for sale and rent in Dubai", "Apartments, villas and off-plan projects for sale and rent in Dubai Marina, Business Bay, Downtown and Dubai Creek Harbour, from ARTÉ Properties.", listing_body, "listings.html")

# property pages
for l in L:
    a = AREA.get(l.get("area_slug") or "")
    hl = "".join(f"<li>{e(h)}</li>" for h in l["highlights"])
    ims = l.get("images") or []
    thumbs = ('<div class="thumbs">' + "".join(f'<div class="gallery sm">{facade(seed_of(l["slug"])+i, l["type"])}{photo(l, i)}</div>' for i in range(1, len(ims))) + '</div>') if len(ims) > 1 else ""
    amen = ('<h3 style="margin-top:24px">Features</h3><p class="chips">' + "".join(f"<span>{e(a)}</span>" for a in l["amenities"]) + '</p>') if l.get("amenities") else ""
    facts = [("Type", l["type"]), ("Bedrooms", beds_txt(l)), ("Bathrooms", l.get("baths")),
             ("Size", sqft_txt(l)), ("Developer", l.get("developer")), ("Handover", l.get("handover")), ("Furnished", {True: "Yes", False: "No"}.get(l.get("furnished"))), ("Status", ("Off-plan resale" if l.get("source")=="propertyfinder" else "Off-plan") if l["stage"] == "offplan" else ("For rent" if l["status"] == "rent" else "Ready, for sale"))]
    facts_html = "".join(f'<div><span>{k}</span><b>{e(v)}</b></div>' for k, v in facts if v)
    permit = f'<p class="small mute">Trakheesi permit {e(l["permit"])}</p>' if l.get("permit") else ""
    msg = f'Hello ARTÉ Properties, I am interested in {l["title"]} at {l["building"]}, {l["area"]}.'
    brochure = '<p class="small mute" style="margin:0">Ask for the brochure, floor plans and payment plan and we will send them on WhatsApp or email.</p>' if l["stage"] == "offplan" else ""
    enq = form("enquiry", contact_fields() + fld("message", "Message", "textarea", False, ph="Preferred viewing times, questions, budget"),
               "Send enquiry" if l["stage"] != "offplan" else "Request brochure and payment plan", {"property": f'{l["building"]}, {l["area"]} ({l["slug"]})'}, brochure)
    area_link = f'<p><a href="area-{a["slug"]}.html">Read our {e(a["name"])} area guide</a></p>' if a else ""
    similar = [x for x in L if x["slug"] != l["slug"] and (x["area"] == l["area"] or x["stage"] == l["stage"])][:3]
    body = f'''<section class="band"><div class="wrap">
<p class="crumbs"><a href="index.html">Home</a> / <a href="listings.html">Properties</a> / {e(l["building"])}</p>
<div class="split"><div>
<div class="gallery">{photo(l)}</div>{thumbs}
<p class="where" style="margin-top:22px">{e(l["building"])}, {e(l["area"])}</p><h1 style="font-size:clamp(30px,4vw,46px)">{e(l["title"])}</h1>
{price_html(l)}
<div class="facts">{facts_html}</div>
<p class="lead" style="color:var(--ink)">{e(l["summary"])}</p>
<h3>Highlights</h3><ul class="ticks">{hl}</ul>{amen}{area_link}{permit}
</div>
<aside class="panel sticky"><h2 style="font-size:28px">{"Request details" if l["stage"]=="offplan" else "Arrange a viewing"}</h2>
<p class="mute">Leave your details and an adviser will reply the same day.</p>
<a class="btn ghost" style="width:100%;margin-bottom:16px" href="{wa_link(msg)}" target="_blank" rel="noopener">Ask on WhatsApp</a>{enq}</aside></div></div></section>
{f'<section class="band alt"><div class="wrap"><h2>You may also like</h2><div class="grid" style="margin-top:20px">{"".join(card(x) for x in similar)}</div></div></section>' if similar else ""}'''
    desc = f'{l["title"]} at {l["building"]}, {l["area"]}. {(aed(l["price"]) if l["price"] else "Price on request")}. {l["summary"]}'[:300]
    ld = {"@context": "https://schema.org", "@type": "Offer", "name": f'{l["title"]}, {l["building"]}', "priceCurrency": "AED", "price": l["price"],
          "availability": "https://schema.org/InStock", "seller": {"@type": "RealEstateAgent", "name": S["brand"]}}
    pages[f'property-{l["slug"]}.html'] = page(f'property-{l["slug"]}.html', f'{l["title"]}, {l["building"]}', desc, body, "listings.html", ld if l["price"] else None, (l.get("images") or [""])[0])

# areas
areas_body = f'''<section class="band"><div class="wrap"><p class="crumbs"><a href="index.html">Home</a> / Area guides</p><h1>Dubai area guides</h1>
<p class="lead">What it is like to live in each community, who it suits, and what homes are selling for, using the latest Dubai Land Department figures where we have them.</p>
<div class="grid" style="margin-top:30px">{"".join(area_card(a) for a in A)}</div></div></section>'''
pages["areas.html"] = page("areas.html", "Dubai area guides", "Guides to Downtown Dubai, Business Bay, Dubai Creek Harbour, Dubai Hills Estate, The Springs and Dubai Marina: lifestyle, prices and who each community suits.", areas_body, "areas.html")

for a in A:
    st = a["stats"]
    if st:
        chg = st["psf_chg"]; cls = "up" if chg >= 0 else "down"
        stats = f'''<h2 style="margin-top:40px">The market in numbers</h2>
<div class="stats"><div class="stat"><b>AED {st["psf"]:,}</b><span>Median price per sq ft <span class="{cls}">({chg:+.1f}%)</span></span></div>
<div class="stat"><b>{st["yield"]}%</b><span>Typical gross rental yield</span></div><div class="stat"><b>{st["sales"]:,}</b><span>Sales in the last twelve months</span></div>
<div class="stat"><b>{st["projects"]}</b><span>Projects, {st["under_construction_pct"]}% still under construction</span></div></div>
<table><thead><tr><th>Apartment size</th><th class="num">Median sale price, 2026 to date</th></tr></thead><tbody>{"".join(f'<tr><td>{b}</td><td class="num">{e(aed(p))}</td></tr>' for b,p in st["beds"])}</tbody></table>
<p class="small mute" style="margin-top:10px">Source: {e(S["market_source"])}. Figures are medians and move month to month; ask us for a building-level view.</p>'''
    else:
        stats = f'<div class="panel" style="margin-top:36px"><h3>Want the latest prices for {e(a["name"])}?</h3><p class="mute">We pull recent transactions for the exact cluster or building you are interested in, so you see what homes like yours have actually sold and let for.</p><a class="btn" href="{wa_link("Hello ARTÉ Properties, please send me the latest prices in " + a["name"] + ".")}" target="_blank" rel="noopener">Ask for a price report</a></div>'
    here = [l for l in L if l.get("area_slug") == a["slug"]]
    listing_sec = f'<section class="band alt"><div class="wrap"><h2>Properties in {e(a["name"])}</h2><div class="grid" style="margin-top:20px">{"".join(card(l) for l in here)}</div></div></section>' if here else ""
    body = f'''<section class="hero" style="min-height:min(60vh,520px)">{skyline(seed_of(a["slug"]), spire=a["slug"]=="downtown-dubai")}<div class="wrap">
<p class="crumbs"><a href="index.html">Home</a> / <a href="areas.html">Area guides</a> / {e(a["name"])}</p><h1>{e(a["name"])}</h1><p class="lead">{e(a["line"])}</p></div></section>
<section class="band"><div class="wrap split"><div><p class="lead" style="color:var(--ink)">{e(a["intro"])}</p>
<h3 style="margin-top:28px">Living here</h3><ul class="ticks">{"".join(f"<li>{e(x)}</li>" for x in a["living"])}</ul>
<h3 style="margin-top:28px">Who it suits</h3><p>{e(a["buyers"])}</p>{stats}</div>
<aside class="panel sticky"><h2 style="font-size:28px">Buying or selling in {e(a["name"])}?</h2><p class="mute">Tell us what you need and an adviser who knows the community will be in touch.</p>
{form("area-enquiry", contact_fields() + fld("intent","I would like to",opts=[("Buy","Buy"),("Sell","Sell"),("Rent","Rent"),("Rent out","Rent out"),("Invest off-plan","Invest off-plan")]), "Send", {"area": a["name"]})}</aside></div></section>{listing_sec}'''
    pages[f'area-{a["slug"]}.html'] = page(f'area-{a["slug"]}.html', f'{a["name"]} area guide', f'{a["name"]}: {a["line"]} Lifestyle, prices and who it suits, from ARTÉ Properties.', body, "areas.html")

# services
pages["services.html"] = page("services.html", "Real estate services in Dubai", "Buying, selling, leasing, off-plan advisory, property management and after-sales care in Dubai from ARTÉ Properties.", f'''
<section class="band"><div class="wrap"><p class="crumbs"><a href="index.html">Home</a> / Services</p><h1>One team for the whole journey</h1>
<p class="lead">Whether you are buying your first apartment, letting a villa from overseas or building an off-plan portfolio, the same adviser looks after you from start to finish.</p>{svc_grid(services)}</div></section>
<section class="band alt"><div class="wrap split"><div><h2>How we work with buyers</h2><ul class="ticks"><li>A short call to understand budget, timing and must-haves</li><li>A shortlist, including homes not yet on the portals</li><li>Accompanied viewings, in person or by video call</li><li>Offer, Form F memorandum of understanding and deposit</li><li>Mortgage introductions if you need finance</li><li>Transfer at the trustee office and handover of keys</li></ul></div>
<div><h2>How we work with sellers</h2><ul class="ticks"><li>Valuation from recent comparable transactions</li><li>Form A listing agreement and Trakheesi advertising permit</li><li>Photography, video and listing on the major portals</li><li>Qualified buyers only, with feedback after every viewing</li><li>Negotiation, NOC from the developer and transfer</li></ul><a class="btn" href="valuation.html">Book a valuation</a></div></div></section>''', "services.html")

# about
pages["about.html"] = page("about.html", "About us", "ARTÉ Properties is a high-end Dubai brokerage built on personal service, careful advice and a hassle-free process.", f'''
<section class="band"><div class="wrap split"><div><p class="crumbs"><a href="index.html">Home</a> / About</p><h1>Distinction in luxury real estate</h1>
<p class="lead">ARTÉ Properties is a Dubai brokerage representing high-end homes for buyers, sellers, landlords and investors. We keep our client list deliberately small so that every one of them gets a senior adviser's time.</p>
<h3 style="margin-top:28px">Our vision</h3><p>To be the most trusted name in Dubai's luxury property market, known for a portfolio of exceptional homes and for advice clients come back to.</p>
<h3>Our mission</h3><p>To give every client a distinguished experience: honest pricing, a process without surprises, and someone who answers the phone.</p></div>
<div class="panel"><h3>Leadership</h3><p style="margin:0"><b>{e(S["director"]["name"])}</b></p><p class="mute">{e(S["director"]["title"])} · Dubai Broker Licence (BRN) {e(S["director"]["brn"])}</p>
<h3 style="margin-top:24px">Licensing</h3><p class="mute">{e(S["legal_name"])} is a real estate brokerage licensed in Dubai and regulated by the Real Estate Regulatory Agency (RERA).{f" Office registration number (ORN) {e(S['orn'])}." if S["orn"] else ""}</p>
<a class="btn" href="contact.html">Meet the team</a></div></div></section>''', "about.html")

# contact
pages["contact.html"] = page("contact.html", "Contact us", f'Contact ARTÉ Properties in Business Bay, Dubai. Call {S["phone"]}, WhatsApp or email {S["email"]}.', f'''
<section class="band"><div class="wrap split"><div><p class="crumbs"><a href="index.html">Home</a> / Contact</p><h1>Let's talk</h1>
<p class="lead">Call, message or send us your brief and an adviser will get back to you the same working day.</p>
<div class="facts" style="grid-template-columns:minmax(0,1fr)"><div><span>Phone</span><b><a href="tel:{S["phone_href"]}">{e(S["phone"])}</a></b></div>
<div><span>WhatsApp</span><b><a href="https://wa.me/{S["whatsapp"]}" target="_blank" rel="noopener">Message us</a></b></div><div><span>Email</span><b><a href="mailto:{S["email"]}">{e(S["email"])}</a></b></div><div><span>Office</span><b style="white-space:normal">{e(S["address"])}</b></div></div></div>
<div class="panel">{form("contact", contact_fields() + fld("interest","I am interested in",opts=[("Buying","Buying"),("Selling","Selling"),("Renting","Renting"),("Letting my property","Letting my property"),("Off-plan investment","Off-plan investment"),("Property management","Property management")]) + fld("message","Message","textarea",False,ph="Area, budget, timing"), "Send message")}</div></div></section>''', "contact.html")

# valuation
pages["valuation.html"] = page("valuation.html", "Free property valuation in Dubai", "Book a free valuation of your Dubai apartment, villa or townhouse, based on recent Dubai Land Department sales and rents.", f'''
<section class="band"><div class="wrap split"><div><p class="crumbs"><a href="index.html">Home</a> / Valuation</p><h1>What is your property worth today?</h1>
<p class="lead">A free, no-obligation valuation from an adviser who knows your community, usually within one working day.</p>
<ul class="ticks"><li>Recent comparable sales in your building and cluster</li><li>Achievable rent and gross yield</li><li>Advice on timing, presentation and pricing strategy</li></ul></div><div class="panel">{valuation_form}</div></div></section>''', "")

pages["privacy.html"] = page("privacy.html", "Privacy notice", "How ARTÉ Properties uses the details you send through this website.", f'''
<section class="band"><div class="wrap" style="max-width:760px"><h1>Privacy notice</h1>
<p>When you send a form on this website we receive your name, contact details and message so that an adviser can reply to your enquiry. We use them only for that purpose and for related follow-up about properties you have asked about.</p>
<p>We do not sell your details. Form submissions are stored by our website host and in our client records. You can ask us at any time to see, correct or delete what we hold by emailing <a href="mailto:{S["email"]}">{e(S["email"])}</a>.</p>
<p>If you message us on WhatsApp, WhatsApp's own privacy policy also applies to that conversation.</p></div></section>''')

pages["404.html"] = page("404.html", "Page not found", "This page could not be found.", f'''
<section class="hero" style="min-height:70vh">{skyline(3)}<div class="wrap"><h1>This page has moved</h1><p class="lead">Our website has been rebuilt. Try the properties page or get in touch.</p>
<div style="display:flex;gap:12px;flex-wrap:wrap"><a class="btn" href="listings.html">Browse properties</a><a class="btn ghost" href="contact.html">Contact us</a></div></div></section>''')

# ---------- write ----------
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir()
for name, content in pages.items():
    (OUT / name).write_text(content)
shutil.copy(ROOT / "src/style.css", OUT / "style.css")
shutil.copy(ROOT / "src/app.js", OUT / "app.js")
(OUT / "favicon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#101417"/><text x="32" y="44" text-anchor="middle" font-family="Georgia,serif" font-size="34" fill="#d6c2a0">A</text><rect x="18" y="50" width="28" height="2" fill="#e2725b"/></svg>')
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {S['domain']}/sitemap.xml\n")
urls = "".join(f"<url><loc>{S['domain']}/{'' if n=='index.html' else n.replace('.html','')}</loc></url>" for n in pages if n not in ("404.html",))
(OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
# old Wix URLs -> new pages (Netlify)
(OUT / "_redirects").write_text("""/about-1            /about           301
/contact-3          /contact         301
/list-of-properties /listings        301
/completed-properties /listings?stage=sale 301
/offplan-properties /listings?stage=offplan 301
""")

print(f"Built {len(pages)} pages into {OUT}")
