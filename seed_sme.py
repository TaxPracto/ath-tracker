#!/usr/bin/env python3
"""SME price store maintainer (NSE UDiFF bhavcopies, SM/ST series).
data/sme_prices.json = {"dates": [YYYYMMDD...], "symbols": {sym: {"isin":..., "px": [[YYYYMMDD, close]...]}}}
The store is committed to the repo, so weekly runs only fetch the few missing days.
Per-day extracts cached in cache/bhav/ (not committed).
"""
import csv, io, json, os, time, zipfile
from datetime import date, timedelta
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
BCACHE = os.path.join(BASE, "cache", "bhav")
DATA = os.path.join(BASE, "data")
os.makedirs(BCACHE, exist_ok=True)
os.makedirs(DATA, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126"}
START = date(2024, 7, 1)
END = date.today()
STORE = os.path.join(DATA, "sme_prices.json")


def fetch_day(d):
    """Ensure cache/bhav/{tag}.json exists. None = holiday/weekend/unavailable."""
    tag = d.strftime("%Y%m%d")
    path = os.path.join(BCACHE, f"{tag}.json")
    if os.path.exists(path):
        return
    if d.weekday() >= 5:
        json.dump(None, open(path, "w")); return
    url = f"https://archives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{tag}_F_0000.csv.zip"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 404:
                json.dump(None, open(path, "w")); return
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                rows = csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0])))
                out = {}
                for row in rows:
                    if row.get("SctySrs") in ("SM", "ST"):
                        try:
                            out[row["TckrSymb"]] = [row["ISIN"], float(row["ClsPric"])]
                        except (ValueError, KeyError):
                            pass
                json.dump(out, open(path, "w")); return
        except Exception:
            pass
        time.sleep(2 + attempt * 3)
    # leave missing -> retried next invocation


def main():
    store = {"dates": [], "symbols": {}}
    if os.path.exists(STORE):
        try:
            s = json.load(open(STORE))
            if "symbols" in s:
                store = s
        except Exception:
            pass
    have = set(store["dates"])

    days = []
    d = START
    while d <= END:
        days.append(d); d += timedelta(days=1)

    todo = [d for d in days
            if d.strftime("%Y%m%d") not in have
            and not os.path.exists(os.path.join(BCACHE, d.strftime("%Y%m%d") + ".json"))]
    print(f"store has {len(have)} days; fetching {len(todo)} more", flush=True)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(fetch_day, d) for d in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            fut.result()
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}", flush=True)

    # merge cached days not yet in store
    merged = 0
    for d in days:
        tag = d.strftime("%Y%m%d")
        if tag in have:
            continue
        p = os.path.join(BCACHE, tag + ".json")
        if not os.path.exists(p):
            continue
        try:
            day = json.load(open(p))
        except Exception:
            continue
        if day is None:
            continue
        for sym, (isin, close) in day.items():
            rec = store["symbols"].setdefault(sym, {"isin": isin, "px": []})
            rec["isin"] = isin
            rec["px"].append([tag, close])
        store["dates"].append(tag)
        merged += 1
    for rec in store["symbols"].values():
        rec["px"] = sorted({tuple(x) for x in rec["px"]})
        rec["px"] = [list(x) for x in rec["px"]]
    store["dates"] = sorted(set(store["dates"]))
    json.dump(store, open(STORE, "w"))
    print(f"merged {merged} new days; store: {len(store['symbols'])} symbols, "
          f"{len(store['dates'])} trading days", flush=True)


if __name__ == "__main__":
    main()
