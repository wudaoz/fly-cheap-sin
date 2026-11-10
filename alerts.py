#!/usr/bin/env python3
"""飞哪儿便宜 - low-fare alert rules. Usage: python3 alerts.py DATADIR [RUN]

Reads the compare / explore / alerts documents under DATADIR plus settings.json next to this
script, evaluates the run RUN (default: the newest runs/ document) and writes one
DATADIR/alerts/<RUN>_<CODE>.json per triggered destination. Prints the alert texts.

Rules (destinations in the compare document, incl. the fixed-date route):
  (a) low <= target price
  (b) low <= 90% of the previous run's low for that destination
  (c) >= 3 previous records and low < historical minimum
Europe (from the explore document with region "Europe"): (a), or >= 10% below the previous
Europe document for the same city.
Dedup: if the destination was alerted before and low is not >= 3% below that alert's price, skip.
"""
import json, os, sys, glob, datetime

DATA = sys.argv[1] if len(sys.argv) > 1 else "data"
HERE = os.path.dirname(os.path.abspath(__file__))

# Default target prices (same table as DEFAULT_TH / REGION_DEFAULT_TH in index.html); settings.json overrides per code.
DEFAULT_TH = {"KUL": 110, "PEN": 120, "BKK": 200, "HKT": 170, "SGN": 170, "DAD": 220, "HAN": 230, "PQC": 210, "MNL": 210,
              "PNH": 240, "DPS": 230, "CGK": 200, "REP": 300, "CNX": 280, "USM": 330, "KBV": 260, "CEB": 260, "LGK": 150, "BKI": 150, "RGN": 300,
              "HKG": 320, "TPE": 260, "MFM": 350, "TYO": 480, "OSA": 450, "SEL": 400, "CAN": 420,
              "ATH": 600, "VIE": 680, "MIL": 680, "ZRH": 680, "BCN": 680, "MUC": 680, "ROM": 680, "PAR": 720, "MAD": 720, "LON": 780, "AMS": 780}
REGION_TH = {"SEA": 250, "EA": 450, "CN": 420, "SA": 500, "EU": 720, "OTHER": 300}
REGION = {}
for _codes, _r in ((("KUL","BKK","SGN","HKT","HAN","MNL","DAD","PQC","PNH","REP","CNX","USM","DPS","CGK","PEN","KBV","CEB","BKI","LGK","RGN","VTE","LPQ","SIN"), "SEA"),
                   (("HKG","TPE","MFM","TYO","OSA","SEL","HIJ","FUK","CTS","PUS","OKA"), "EA"), (("PVG","PEK","CAN","SZX","CTU","XMN"), "CN"),
                   (("BOM","DEL","JAI","GOI","BLR","MAA","CCU","COK","KTM","HYD","CMB","MLE","DXB","AUH","DOH"), "SA")):
    for _c in _codes: REGION[_c] = _r
ZH = {"KUL": "吉隆坡", "BKK": "曼谷", "SGN": "胡志明市", "HKT": "普吉岛", "HAN": "河内", "MNL": "马尼拉", "DAD": "岘港", "PQC": "富国岛", "PNH": "金边",
      "REP": "暹粒", "CNX": "清迈", "USM": "苏梅岛", "DPS": "巴厘岛", "CGK": "雅加达", "PEN": "槟城", "CEB": "宿务", "KBV": "甲米", "BKI": "亚庇", "LGK": "兰卡威",
      "RGN": "仰光", "VTE": "万象", "LPQ": "琅勃拉邦", "SIN": "新加坡", "HKG": "香港", "TPE": "台北", "MFM": "澳门", "TYO": "东京", "OSA": "大阪", "SEL": "首尔", "FUK": "福冈", "CTS": "札幌", "OKA": "冲绳",
      "PVG": "上海", "PEK": "北京", "CAN": "广州", "SZX": "深圳", "CTU": "成都", "XMN": "厦门", "BOM": "孟买", "DEL": "新德里", "GOI": "果阿", "CMB": "科伦坡", "MLE": "马尔代夫", "KTM": "加德满都", "DXB": "迪拜", "DOH": "多哈",
      "LON": "伦敦", "ATH": "雅典", "LIS": "里斯本", "PAR": "巴黎", "DUB": "都柏林", "AMS": "阿姆斯特丹", "ROM": "罗马", "BCN": "巴塞罗那",
      "VCE": "威尼斯", "BER": "柏林", "PRG": "布拉格", "MAD": "马德里", "VIE": "维也纳", "BUD": "布达佩斯", "CPH": "哥本哈根", "MIL": "米兰", "MUC": "慕尼黑",
      "STO": "斯德哥尔摩", "ZRH": "苏黎世", "HEL": "赫尔辛基", "NCE": "尼斯", "IST": "伊斯坦布尔"}
EU = {"London": "LON", "Athens": "ATH", "Lisbon": "LIS", "Paris": "PAR", "Dublin": "DUB", "Amsterdam": "AMS", "Rome": "ROM", "Barcelona": "BCN",
      "Venice": "VCE", "Berlin": "BER", "Prague": "PRG", "Madrid": "MAD", "Vienna": "VIE", "Budapest": "BUD", "Copenhagen": "CPH", "Milan": "MIL",
      "Munich": "MUC", "Stockholm": "STO", "Zürich": "ZRH", "Zurich": "ZRH", "Helsinki": "HEL", "Nice": "NCE", "Istanbul": "IST"}


def load(coll):
    docs = []
    for fn in glob.glob(os.path.join(DATA, coll, "*.json")):
        with open(fn, encoding="utf-8") as f:
            docs.append(json.load(f))
    return sorted(docs, key=lambda d: d.get("at", ""), reverse=True)


def md(iso):  # "2027-02-11" -> "2/11"
    d = datetime.date.fromisoformat(iso)
    return f"{d.month}/{d.day}"


def main():
    runs = load("runs")
    if not runs:
        print("no runs"); return
    run = sys.argv[2] if len(sys.argv) > 2 else runs[0]["run"]
    at = next((r["at"] for r in runs if r["run"] == run), runs[0]["at"])

    settings = {}
    sp = os.path.join(HERE, "settings.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            settings = json.load(f)
    user_th = settings.get("thresholds", {})

    def th(code, eu=False):
        if code in user_th: return user_th[code]
        if code in DEFAULT_TH: return DEFAULT_TH[code]
        return REGION_TH["EU"] if eu else REGION_TH.get(REGION.get(code, "OTHER"), 300)

    compares = load("compare")
    cur = next((c for c in compares if c["run"] == run), None)
    cur_label = (cur or {}).get("currency") or settings.get("currency", "SGD")
    prev = [c for c in compares if c["run"] != run and c["at"] < at]
    explores = load("explore")
    eu_cur = next((e for e in explores if e.get("region") == "Europe" and e["run"] == run), None)
    eu_prev = next((e for e in explores if e.get("region") == "Europe" and e["run"] != run and e["at"] < at), None)
    last_alert = {}
    for a in load("alerts"):  # newest first -> first seen is the latest
        if a["run"] != run and a["code"] not in last_alert:
            last_alert[a["code"]] = a["price"]

    def lows(doc):  # code -> min non-null of google/trip/agoda
        out = {}
        for it in doc.get("items", []):
            ps = [p for p in (it.get("google"), it.get("trip"), it.get("agoda")) if p is not None]
            if ps: out[it["code"]] = min(ps)
        return out

    hist = {}
    for c in prev:
        for code, p in lows(c).items():
            hist.setdefault(code, []).append(p)
    prev_low = lows(prev[0]) if prev else {}

    alerts = []
    if cur:
        for it in cur.get("items", []):
            code, low = it["code"], it.get("google")
            if low is None: continue
            t = th(code); h = hist.get(code, []); reasons = []
            if low <= t: reasons.append(f"低于心理价位 {t}")
            if code in prev_low and low <= prev_low[code] * 0.9: reasons.append(f"较上次 {prev_low[code]} 降 {round((1 - low / prev_low[code]) * 100)}%")
            new_low = len(h) >= 3 and low < min(h)
            if not reasons and not new_low: continue
            text = f"{ZH.get(code, code)} {md(it['out'])}→{md(it['back'])} 往返 {cur_label} {low}（Google）" + ("，" + "，".join(reasons) if reasons else "") + ("，创历史新低" if new_low else "")
            alerts.append((code, low, text))

    if eu_cur:
        prev_eu = {}
        for r in (eu_prev or {}).get("rows", []):
            if r[0] in EU: prev_eu[EU[r[0]]] = min(r[2], prev_eu.get(EU[r[0]], 10 ** 9))
        seen = set()
        for r in sorted(eu_cur.get("rows", []), key=lambda r: r[2]):
            code = EU.get(r[0])
            if not code or code in seen: continue
            seen.add(code)
            low, t, reasons = r[2], th(code, eu=True), []
            if low <= t: reasons.append(f"低于心理价位 {t}")
            if code in prev_eu and low <= prev_eu[code] * 0.9: reasons.append(f"较上次欧洲采集 {prev_eu[code]} 降 {round((1 - low / prev_eu[code]) * 100)}%")
            if not reasons: continue
            alerts.append((code, low, f"{ZH.get(code, code)} {md(r[6])}→{md(r[7])} 往返 {cur_label} {low}（Google），" + "，".join(reasons)))

    written = []
    for code, low, text in alerts:
        if code in last_alert and low > last_alert[code] * 0.97:
            print(f"skip {code} {low} (last alert {last_alert[code]})", file=sys.stderr); continue
        os.makedirs(os.path.join(DATA, "alerts"), exist_ok=True)
        with open(os.path.join(DATA, "alerts", f"{run}_{code}.json"), "w", encoding="utf-8") as f:
            json.dump({"at": at, "run": run, "code": code, "price": low, "src": "Google", "text": text}, f, ensure_ascii=False, indent=1)
        written.append(text)
    print("\n".join(written) if written else "no alerts")


if __name__ == "__main__":
    main()
