#!/usr/bin/env python3
"""飞哪儿便宜 - pack DATADIR/<collection>/*.json into DATADIR/bundle.json for the static dashboard.

Usage: python3 build_bundle.py DATADIR
The page fetches one file instead of hundreds. explore documents are capped to the newest
EXPLORE_RUNS runs (the trend charts rarely need more); everything else is included in full.
"""
import json, os, sys, glob, datetime

DATA = sys.argv[1] if len(sys.argv) > 1 else "data"
HERE = os.path.dirname(os.path.abspath(__file__))
EXPLORE_RUNS = 120


def load(coll):
    docs = []
    for fn in glob.glob(os.path.join(DATA, coll, "*.json")):
        with open(fn, encoding="utf-8") as f:
            docs.append(json.load(f))
    return sorted(docs, key=lambda d: d.get("at", ""), reverse=True)


settings = {}
sp = os.path.join(HERE, "settings.json")
if os.path.exists(sp):
    with open(sp, encoding="utf-8") as f:
        settings = json.load(f)

explore = load("explore")
keep = []
for d in explore:
    if d["run"] not in keep: keep.append(d["run"])
    if len(keep) >= EXPLORE_RUNS: break
explore = [d for d in explore if d["run"] in keep]

bundle = {"generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "settings": settings, "explore": explore, "compare": load("compare"), "grid": load("grid"),
          "alerts": load("alerts"), "runs": load("runs")}
os.makedirs(DATA, exist_ok=True)
with open(os.path.join(DATA, "bundle.json"), "w", encoding="utf-8") as f:
    json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
print({k: len(v) for k, v in bundle.items() if isinstance(v, list)}, os.path.getsize(os.path.join(DATA, "bundle.json")), "bytes")
