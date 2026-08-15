#!/usr/bin/env python3
"""SME price store maintainer — NSE Emerge (SM/ST) + BSE SME (M/MT) from daily bhavcopies.
data/sme_prices.json = {"dates":[...], "bse_dates":[...], "symbols": {key: rec}}
  key = NSE ticker (e.g. "AIMTRON") or "BSE:<scripcode>"
  rec = {"isin":..., "px": [[YYYYMMDD, close]...], "exch": "NSE"|"BSE", "code": str|None, "name": str}
Store is committed to the repo, so weekly runs fetch only missing days.
Per-day extracts cached in cache/bhav/ (NSE) and cache/bhavb/ (BSE) — not committed.
"""
import csv, io, json, os, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
NCACHE = os.path.join(BASE, "cache", "bhav")
BCACHE = os.path.join(BASE, "cache", "bhavb")
DATA = os.path.join(BASE, "data")
for p in (NCACHE, BCACHE, DATA):
    os.makedirs(p, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126",
      "Referer": "https://www.bseindia.com/"}
START = date(2024, 7, 1)
END = date.today()
STORE = os.path.join(DATA, "sme_prices.json")


def fetch_nse(d):
    tag = d.strftime("%Y%m%d")
    path = os.path.join(NCACHE, f"{tag}.json")
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
                out = {}
                for row in csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]))):
                    if row.get("SctySrs") in ("SM", "ST"):
                        try:
                            out[row["TckrSymb"]] = [row["ISIN"], float(row["ClsPric"])]
                        except (ValueError, KeyError):
                            pass
                json.dump(out, open(path, "w")); return
        except Exception:
            pass
        time.sleep(2 + attempt * 3)


def fetch_bse(d):
    tag = d.strftime("%Y%m%d")
    path = os.path.join(BCACHE, f"{tag}.json")
    if os.path.exists(path):
        return
    if d.weekday() >= 5:
        json.dump(None, open(path, "w")); return
    url = f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{tag}_F_0000.CSV"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=40)
            if r.status_code in (403, 404):
                json.dump(None, open(path, "w")); return
            if r.status_code == 200 and "TradDt" in r.text[:200]:
                out = {}
                for row in csv.DictReader(io.StringIO(r.text)):
                    if row.get("SctySrs") in ("M", "MT"):
                        try:
                            out[row["FinInstrmId"]] = [row["ISIN"], row.get("TckrSymb", ""),
                                                       row.get("FinInstrmNm", ""), float(row["ClsPric"])]
                        except (ValueError, KeyError):
                            pass
                json.dump(out, open(path, "w")); return
        except Exception:
            pass
        time.sleep(2 + attempt * 3)


def main():
    store = {"dates": [], "bse_dates": [], "symbols": {}}
    if os.path.exists(STORE):
        try:
            s = json.load(open(STORE))
            if "symbols" in s:
                store = s
                store.setdefault("bse_dates", [])
        except Exception:
            pass
    have_n, have_b = set(store["dates"]), set(store["bse_dates"])

    days = []
    d = START
    while d <= END:
        days.append(d); d += timedelta(days=1)

    todo = []
    for d in days:
        tag = d.strftime("%Y%m%d")
        if tag not in have_n and not os.path.exists(os.path.join(NCACHE, tag + ".json")):
            todo.append(("N", d))
        if tag not in have_b and not os.path.exists(os.path.join(BCACHE, tag + ".json")):
            todo.append(("B", d))
    print(f"store days NSE {len(have_n)} / BSE {len(have_b)}; fetching {len(todo)}", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(fetch_nse if k == "N" else fetch_bse, d) for k, d in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            fut.result()
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}", flush=True)

    merged_n = merged_b = 0
    for d in days:
        tag = d.strftime("%Y%m%d")
        if tag not in have_n:
            p = os.path.join(NCACHE, tag + ".json")
            if os.path.exists(p):
                try:
                    day = json.load(open(p))
                except Exception:
                    day = None
                if day is not None:
                    for sym, (isin, close) in day.items():
                        rec = store["symbols"].setdefault(sym, {"isin": isin, "px": []})
                        rec.update({"isin": isin, "exch": "NSE", "code": None,
                                    "name": rec.get("name", sym)})
                        rec["px"].append([tag, close])
                    store["dates"].append(tag); merged_n += 1
        if tag not in have_b:
            p = os.path.join(BCACHE, tag + ".json")
            if os.path.exists(p):
                try:
                    day = json.load(open(p))
                except Exception:
                    day = None
                if day is not None:
                    for code, (isin, tckr, name, close) in day.items():
                        key = "BSE:" + code
                        rec = store["symbols"].setdefault(key, {"isin": isin, "px": []})
                        rec.update({"isin": isin, "exch": "BSE", "code": code,
                                    "name": name or tckr or code,
                                    "tckr": tckr or code})
                        rec["px"].append([tag, close])
                    store["bse_dates"].append(tag); merged_b += 1

    for rec in store["symbols"].values():
        rec.setdefault("exch", "NSE"); rec.setdefault("code", None)
        rec["px"] = [list(x) for x in sorted({tuple(p) for p in rec["px"]})]
    store["dates"] = sorted(set(store["dates"]))
    store["bse_dates"] = sorted(set(store["bse_dates"]))
    json.dump(store, open(STORE, "w"))
    n_nse = sum(1 for r in store["symbols"].values() if r["exch"] == "NSE")
    n_bse = sum(1 for r in store["symbols"].values() if r["exch"] == "BSE")
    print(f"merged NSE {merged_n} / BSE {merged_b} days; store: {n_nse} NSE-SME + {n_bse} BSE-SME symbols", flush=True)


if __name__ == "__main__":
    main()
