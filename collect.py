#!/usr/bin/env python3
# 飞哪儿便宜 - SerpApi collector. Usage: SERPAPI_KEY=... python3 collect.py DATADIR
# Reads settings.json next to this file (origin, currency, months, optional fixed-date route, ...),
# writes one JSON document per record into DATADIR/<collection>/<doc_id>.json and prints a summary.
import json, os, sys, datetime, urllib.request, urllib.parse, time

KEY = os.environ["SERPAPI_KEY"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

S = {}
if os.path.exists(os.path.join(HERE, "settings.json")):
    with open(os.path.join(HERE, "settings.json"), encoding="utf-8") as f:
        S = json.load(f)
ORIGIN = S.get("origin", "SIN")            # IATA code of the departure airport / city
CUR = S.get("currency", "SGD")
GL = S.get("gl", "sg")                     # Google country code (affects locale / price source)
TZ_HOURS = S.get("tzOffsetHours", 8)       # local time zone for run ids
MONTHS_AHEAD = int(S.get("monthsAhead", 5))   # current month + N-1
WINDOW_DAYS = int(S.get("windowDays", 125))
EUROPE = bool(S.get("europe", True))
FR = S.get("fixedRoute") or None           # {"dest","out","back","deadline","label","window"} or null

TZ = datetime.timezone(datetime.timedelta(hours=TZ_HOURS))
now = datetime.datetime.now(datetime.timezone.utc)
RUN = now.astimezone(TZ).strftime("%Y-%m-%dT%H%M")
AT = now.strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = now.astimezone(TZ).date()
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

# Explore returns city names; map the ones we track to IATA codes (same list as CITIES in index.html).
DEST = {"Federal Territory of Kuala Lumpur":"KUL","Kuala Lumpur":"KUL","Bangkok":"BKK","Ho Chi Minh City":"SGN","Phuket":"HKT","Hanoi":"HAN","Manila":"MNL","Da Nang":"DAD","Phú Quốc":"PQC","Phu Quoc":"PQC","Phnom Penh":"PNH","Krong Siem Reap":"REP","Siem Reap":"REP","Chiang Mai":"CNX","Ko Samui":"USM","Denpasar":"DPS","Bali":"DPS","Jakarta":"CGK","Penang":"PEN","George Town":"PEN","Krabi":"KBV","Cebu City":"CEB","Cebu":"CEB","Kota Kinabalu":"BKI","Langkawi":"LGK","Yangon":"RGN","Vientiane":"VTE","Luang Prabang":"LPQ","Singapore":"SIN",
        "Hong Kong":"HKG","Taipei City":"TPE","Taipei":"TPE","Macao":"MFM","Tokyo":"TYO","Osaka":"OSA","Seoul":"SEL","Hiroshima":"HIJ","Fukuoka":"FUK","Sapporo":"CTS","Busan":"PUS","Okinawa":"OKA",
        "Shanghai":"PVG","Beijing":"PEK","Guangzhou":"CAN","Shenzhen":"SZX","Chengdu":"CTU","Xiamen":"XMN",
        "Mumbai":"BOM","New Delhi":"DEL","Jaipur":"JAI","Goa":"GOI","Bengaluru":"BLR","Chennai":"MAA","Kolkata":"CCU","Kochi":"COK","Kathmandu":"KTM","Hyderabad":"HYD","Colombo":"CMB","Male":"MLE","Dubai":"DXB","Abu Dhabi":"AUH","Doha":"DOH"}
CITY = {"KUL":"Kuala Lumpur","BKK":"Bangkok","SGN":"Ho Chi Minh City","HKT":"Phuket","HAN":"Hanoi","MNL":"Manila","DAD":"Da Nang","PQC":"Phu Quoc","PNH":"Phnom Penh","REP":"Siem Reap","CNX":"Chiang Mai","USM":"Ko Samui","DPS":"Bali","CGK":"Jakarta","PEN":"Penang","KBV":"Krabi","CEB":"Cebu","BKI":"Kota Kinabalu","LGK":"Langkawi","RGN":"Yangon","VTE":"Vientiane","LPQ":"Luang Prabang","SIN":"Singapore",
        "HKG":"Hong Kong","TPE":"Taipei","MFM":"Macao","TYO":"Tokyo","OSA":"Osaka","SEL":"Seoul","HIJ":"Hiroshima","FUK":"Fukuoka","CTS":"Sapporo","PUS":"Busan","OKA":"Okinawa",
        "PVG":"Shanghai","PEK":"Beijing","CAN":"Guangzhou","SZX":"Shenzhen","CTU":"Chengdu","XMN":"Xiamen",
        "BOM":"Mumbai","DEL":"New Delhi","JAI":"Jaipur","GOI":"Goa","BLR":"Bengaluru","MAA":"Chennai","CCU":"Kolkata","COK":"Kochi","KTM":"Kathmandu","HYD":"Hyderabad","CMB":"Colombo","MLE":"Male","DXB":"Dubai","AUH":"Abu Dhabi","DOH":"Doha"}
EU = {"London":"LON","Athens":"ATH","Lisbon":"LIS","Paris":"PAR","Dublin":"DUB","Amsterdam":"AMS","Rome":"ROM","Barcelona":"BCN","Venice":"VCE","Berlin":"BER","Prague":"PRG","Madrid":"MAD","Vienna":"VIE","Budapest":"BUD","Copenhagen":"CPH","Milan":"MIL","Munich":"MUC","Stockholm":"STO","Zürich":"ZRH","Zurich":"ZRH","Helsinki":"HEL","Nice":"NCE","Istanbul":"IST"}

def api(params, tries=3):
    params = dict(params, api_key=KEY)
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                d = json.load(r)
            if d.get("search_metadata", {}).get("status") == "Success" or "destinations" in d or "best_flights" in d or "other_flights" in d:
                return d
            last = d.get("error") or d.get("search_metadata", {}).get("status")
        except Exception as e:
            last = str(e)
        time.sleep(5 * (i + 1))
    print("API FAILED", {k: v for k, v in params.items() if k != "api_key"}, last, file=sys.stderr)
    return None

def date_text(a, b):
    a = datetime.date.fromisoformat(a); b = datetime.date.fromisoformat(b)
    cur = TODAY.year
    if a.year == b.year:
        if a.month == b.month: s = f"{MON[a.month-1]} {a.day} – {b.day}"
        else: s = f"{MON[a.month-1]} {a.day} – {MON[b.month-1]} {b.day}"
        if a.year != cur: s += f", {a.year}"
        return s
    return f"{MON[a.month-1]} {a.day}, {a.year} – {MON[b.month-1]} {b.day}, {b.year}"

def stops_text(n): return "Nonstop" if not n else ("1 stop" if n == 1 else f"{n} stops")
def dur_text(m):
    if m is None: return ""
    h, mm = divmod(int(m), 60)
    return f"{h} hr" + (f" {mm} min" if mm else "")

def rows_from(dests):
    rows = []
    for x in dests:
        p = x.get("flight_price")
        if p is None or not x.get("start_date"): continue
        rows.append([x["name"], date_text(x["start_date"], x["end_date"]), int(p), stops_text(x.get("number_of_stops")),
                     dur_text(x.get("flight_duration")), x.get("airline", ""), x["start_date"], x["end_date"], x.get("destination_airport", {}).get("code", "")])
    return rows

note, best = [], {}
def add(coll, doc_id, doc):
    os.makedirs(os.path.join(OUT, coll), exist_ok=True)
    with open(os.path.join(OUT, coll, f"{doc_id}.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

base = {"departure_id": ORIGIN, "travel_duration": 2, "travel_mode": 1, "currency": CUR, "hl": "en", "gl": GL}

# 1. monthly explore from ORIGIN
months_done = []
for i in range(MONTHS_AHEAD):
    y, m = TODAY.year, TODAY.month + i
    while m > 12: m -= 12; y += 1
    key = f"{y}-{m:02d}"
    d = api(dict(base, engine="google_travel_explore", month=m))
    if not d: note.append(f"explore {key} failed"); continue
    rows = rows_from(d.get("destinations", []))
    rows = [r for r in rows if r[6][:7] == key] or rows
    if not rows: note.append(f"explore {key} empty"); continue
    add("explore", f"{RUN}_{key}", {"run": RUN, "at": AT, "origin": ORIGIN, "currency": CUR, "month": key, "label": f"1-week trip in {datetime.date(y, m, 1).strftime('%B')}", "source": "serpapi-explore", "rows": rows})
    months_done.append(key)
    for r in rows:
        code = DEST.get(r[0])
        if not code or code == ORIGIN: continue
        o = datetime.date.fromisoformat(r[6])
        if not (TODAY < o <= TODAY + datetime.timedelta(days=WINDOW_DAYS)): continue
        if code not in best or r[2] < best[code][0]: best[code] = (r[2], r[6], r[7])

# 2. Europe, next 6 months
eu_rows = []
if EUROPE:
    d = api(dict(base, engine="google_travel_explore", arrival_area_id="/m/02j9z", month=0))
    eu_rows = rows_from(d.get("destinations", [])) if d else []
    if eu_rows:
        add("explore", f"{RUN}_europe", {"run": RUN, "at": AT, "origin": ORIGIN, "currency": CUR, "month": "next-6-months", "region": "Europe", "label": "1-week trip in the next 6 months", "source": "serpapi-explore", "rows": eu_rows})
    else: note.append("europe explore failed/empty")

# 3. optional fixed-date route (specific dates via the Google Flights engine)
fixed = None
if FR and TODAY < datetime.date.fromisoformat(FR.get("deadline", FR["out"])):
    d = api({"engine": "google_flights", "departure_id": ORIGIN, "arrival_id": FR["dest"], "outbound_date": FR["out"], "return_date": FR["back"],
             "type": 1, "adults": 1, "travel_class": 1, "currency": CUR, "hl": "en", "gl": GL})
    if d:
        fl = (d.get("best_flights") or []) + (d.get("other_flights") or [])
        prices = [f["price"] for f in fl if f.get("price")]
        pi = d.get("price_insights") or {}
        low = pi.get("lowest_price") or (min(prices) if prices else None)
        if low:
            fixed = int(low)
            lvl = pi.get("price_level"); tr = pi.get("typical_price_range")
            ins = f"Prices are currently {lvl}" + (f" (typical {CUR} {tr[0]}–{tr[1]})" if tr else "") if lvl else ""
            a, b = datetime.date.fromisoformat(FR["out"]), datetime.date.fromisoformat(FR["back"])
            add("grid", f"{RUN}_{FR['dest']}", {"run": RUN, "at": AT, "dest": FR["dest"], "window": FR.get("window", f"{FR['out']} → {FR['back']}"), "insight": ins, "source": "serpapi-flights",
                 "cells": [[f"{MON[a.month-1]} {a.day}", f"{MON[b.month-1]} {b.day}", fixed]], "priceHistory": pi.get("price_history")})
        else: note.append(f"{FR['dest']}: no price")
    else: note.append(f"{FR['dest']} flights failed")

# 4. compare doc: the 9 cheapest tracked destinations (+ the fixed route)
items = [{"code": k, "city": CITY.get(k, k), "out": v[1], "back": v[2], "google": v[0], "trip": None, "agoda": None, "tripAlert": None}
         for k, v in sorted(best.items(), key=lambda kv: kv[1][0])[:9]]
if fixed: items.append({"code": FR["dest"], "city": FR.get("label") or CITY.get(FR["dest"], FR["dest"]), "out": FR["out"], "back": FR["back"], "google": fixed, "trip": None, "agoda": None, "tripAlert": None})
add("compare", RUN, {"run": RUN, "at": AT, "origin": ORIGIN, "currency": CUR, "source": "serpapi", "items": items})
status = "ok" if not note else "partial"
add("runs", RUN, {"run": RUN, "at": AT, "origin": ORIGIN, "status": status, "sources": ["google(serpapi)"],
                  "note": "; ".join(note) or f"{len(months_done)} months" + (f" + Europe {len(eu_rows)} cities" if EUROPE else "") + (f" + {FR['dest']}" if fixed else "") + " via SerpApi"})

eu_summary = sorted([[EU[r[0]], r[0], r[2], r[6], r[7]] for r in eu_rows if r[0] in EU], key=lambda x: x[2])
print(json.dumps({"RUN": RUN, "AT": AT, "origin": ORIGIN, "status": status, "months": months_done, "europeCities": len(eu_rows), "note": note,
                  "compare": [[i["code"], i["google"], i["out"], i["back"]] for i in items], "europe": eu_summary}, ensure_ascii=False, indent=0))
