#!/usr/bin/env python3
"""ATH Tracker — weekly screen.
Universe: all NSE mainboard (EQ) via Yahoo daily history + NSE SME (SM/ST) via bhavcopy store.
Filters: (1) close within 2% of all-time high; (2) TTM return strictly above Nifty 500,
Nifty Total Market, sector index (mainboard, where mapped) / NIFTY SME EMERGE (SME);
(3) TTM PAT at all-time high (screener.in); (4) market cap Rs 1,000-20,000 Cr.
Sort: newest entrant into the 2%-of-ATH zone first. Diffs vs previous run in data/state.json.
Outputs: data/state.json, docs/index.html, docs/data.json, docs/ATH_Tracker_latest.xlsx.
"""
import csv, io, json, os, re, time, random, bisect, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
DOCS = os.path.join(BASE, "docs")
PXCACHE = os.path.join(BASE, "cache", "px")
SCRCACHE = os.path.join(BASE, "cache", "scr")
IDXCACHE = os.path.join(BASE, "cache", "idx")
for p in (DATA, DOCS, PXCACHE, SCRCACHE, IDXCACHE):
    os.makedirs(p, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
ATH_TOL = 0.02
MCAP_MIN, MCAP_MAX = 1000.0, 20000.0
TTM_DAYS = 365
TODAY = date.today()

SECTOR_BY_NSE_INDUSTRY = {
    "Automobile and Auto Components": "Nifty Auto",
    "Financial Services": "Nifty Financial Services",
    "Information Technology": "Nifty IT",
    "Healthcare": "Nifty Healthcare Index",
    "Fast Moving Consumer Goods": "Nifty FMCG",
    "Metals & Mining": "Nifty Metal",
    "Oil Gas & Consumable Fuels": "Nifty Oil & Gas",
    "Power": "Nifty Energy",
    "Realty": "Nifty Realty",
    "Consumer Durables": "Nifty Consumer Durables",
    "Media Entertainment & Publication": "Nifty Media",
    "Chemicals": "Nifty Chemicals",
}
SECTOR_KEYWORDS = [  # fallback mapping from screener sector text, first match wins
    (("auto",), "Nifty Auto"),
    (("bank",), "Nifty Financial Services"),
    (("finance", "nbfc", "insurance", "capital market", "stock", "broker", "asset management"), "Nifty Financial Services"),
    (("software", "it -", "it services", "information tech"), "Nifty IT"),
    (("pharma", "health", "hospital", "diagnos", "medical"), "Nifty Healthcare Index"),
    (("fmcg", "food", "beverage", "personal care", "tobacco", "breweries", "distiller"), "Nifty FMCG"),
    (("steel", "metal", "mining", "aluminium", "copper", "zinc", "iron"), "Nifty Metal"),
    (("oil", "gas", "petro", "refiner", "lubricant"), "Nifty Oil & Gas"),
    (("power", "electric utilit", "energy"), "Nifty Energy"),
    (("realty", "real estate"), "Nifty Realty"),
    (("consumer durable", "appliance", "electronics - consumer"), "Nifty Consumer Durables"),
    (("media", "entertainment", "broadcast", "film"), "Nifty Media"),
    (("chemical", "fertiliz", "pesticid", "agrochem", "dyes", "paint"), "Nifty Chemicals"),
]
BROAD = ["Nifty 500", "Nifty Total Market"]
SME_BENCH = "NIFTY SME EMERGE"


# ---------------- index snapshots (archives, works from GitHub runners) ----------------
def idx_snapshot(target, back=True, max_walk=7):
    """Return (actual_date, {index_name_upper: close}) for nearest trading day <= target
    (or >= target if back=False)."""
    step = -1 if back else 1
    d = target
    for _ in range(max_walk):
        tag = d.strftime("%d%m%Y")
        path = os.path.join(IDXCACHE, tag + ".json")
        if os.path.exists(path):
            snap = json.load(open(path))
            if snap:
                return d, snap
        else:
            url = f"https://archives.nseindia.com/content/indices/ind_close_all_{tag}.csv"
            try:
                r = requests.get(url, headers=UA, timeout=25)
            except Exception:
                r = None
            snap = {}
            if r is not None and r.status_code == 200 and "Index Name" in r.text[:200]:
                for row in csv.DictReader(io.StringIO(r.text)):
                    try:
                        snap[row["Index Name"].strip().upper()] = float(row["Closing Index Value"])
                    except (ValueError, KeyError):
                        pass
            json.dump(snap, open(path, "w"))
            if snap:
                return d, snap
        d += timedelta(days=step)
    raise RuntimeError(f"no index snapshot near {target}")


class IndexReturns:
    """TTM (or matched-window) index returns from two archive snapshots."""
    def __init__(self):
        self.end_date, self.end = idx_snapshot(TODAY, back=True)
        self.cache = {}

    def ret(self, name, anchor_date):
        key = (name.upper(), anchor_date)
        if key in self.cache:
            return self.cache[key]
        try:
            _, snap = idx_snapshot(anchor_date, back=True)
            start = snap.get(name.upper())
            end = self.end.get(name.upper())
            r = None if not start or not end else (end / start - 1) * 100
        except RuntimeError:
            r = None
        self.cache[key] = r
        return r


# ---------------- price series helpers ----------------
def series_metrics(ts_dates, closes):
    """ts_dates: list[date] ascending; closes: list[float]. Returns dict or None."""
    if len(closes) < 5:
        return None
    last, last_d = closes[-1], ts_dates[-1]
    ath = max(closes)
    ath_i = closes.index(ath)
    pct_from_ath = (last / ath - 1) * 100
    runmax, cond = 0.0, []
    for c in closes:
        runmax = max(runmax, c)
        cond.append(c >= (1 - ATH_TOL) * runmax)
    i = len(cond) - 1
    while i > 0 and cond[i - 1]:
        i -= 1
    anchor = max(ts_dates[0], last_d - timedelta(days=TTM_DAYS))
    j = bisect.bisect_right(ts_dates, anchor) - 1
    j = max(j, 0)
    stock_ret = (last / closes[j] - 1) * 100 if closes[j] > 0 and j < len(closes) - 1 else None
    return {"last_close": round(last, 2), "last_date": str(last_d), "ath": round(ath, 2),
            "ath_date": str(ts_dates[ath_i]), "pct_from_ath": round(pct_from_ath, 2),
            "zone_entry": str(ts_dates[i]), "days_in_zone": len(cond) - i,
            "anchor_date": str(ts_dates[j]), "window_days": (last_d - ts_dates[0]).days if (last_d - ts_dates[0]).days < TTM_DAYS else TTM_DAYS,
            "stock_ret": None if stock_ret is None else round(stock_ret, 2)}


def yahoo_daily(symbol):
    key = re.sub(r"[^A-Za-z0-9._-]", "_", symbol)
    path = os.path.join(PXCACHE, key + ".json")
    data = None
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < 3 * 86400:
        try:
            data = json.load(open(path))
        except Exception:
            data = None
    if data is None:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
               f"?period1=0&period2={int(time.time())}&interval=1d")
        for attempt in range(4):
            try:
                r = requests.get(url, headers=UA, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    json.dump(data, open(path, "w"))
                    break
                if r.status_code == 404:
                    json.dump({"missing": True}, open(path, "w"))
                    return None
                time.sleep((3 if r.status_code == 429 else 1.5) * (attempt + 1))
            except Exception:
                time.sleep(1.5 * (attempt + 1))
    if not data or data.get("missing"):
        return None
    try:
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        cl = res["indicators"]["quote"][0]["close"]
    except (KeyError, TypeError, IndexError):
        return None
    pairs = [(datetime.fromtimestamp(t).date(), c) for t, c in zip(ts, cl) if c]
    if not pairs:
        return None
    return [p[0] for p in pairs], [p[1] for p in pairs]


# ---------------- screener.in fundamentals ----------------
def parse_num(s):
    s = s.replace(",", "").strip()
    if s in ("", "-", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def screener_fetch(symbol, consolidated):
    tag = "C" if consolidated else "S"
    path = os.path.join(SCRCACHE, f"{symbol}_{tag}.html")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < 3 * 86400:
        return open(path, encoding="utf-8").read()
    url = f"https://www.screener.in/company/{symbol}/" + ("consolidated/" if consolidated else "")
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200:
                open(path, "w", encoding="utf-8").write(r.text)
                time.sleep(random.uniform(1.2, 1.9))  # throttle only real hits
                return r.text
            if r.status_code == 404:
                return None
            time.sleep(5 + attempt * 5)
        except Exception:
            time.sleep(5 + attempt * 5)
    return None


def row_from_table(table, row_name):
    heads = [th.get_text(strip=True) for th in table.find("thead").find_all("th")][1:]
    for tr in table.find("tbody").find_all("tr"):
        cells = tr.find_all("td")
        if cells and re.match(rf"^{row_name}\b", cells[0].get_text(strip=True), re.I):
            return heads, [parse_num(td.get_text(strip=True)) for td in cells[1:]]
    return None, None


def fundamentals(symbol, expected_price=None):
    """Return dict with mcap, sector_text, pat fields, or error.
    Guard: the screener page's own Current Price must roughly match our last close,
    else the page is a stub / wrong company and its numbers are rejected."""
    for consolidated in (True, False):
        html = screener_fetch(symbol, consolidated)
        if not html:
            continue
        if expected_price:
            pm = re.search(r"Current Price[^0-9]*([\d,]+(?:\.\d+)?)", html)
            page_price = float(pm.group(1).replace(",", "")) if pm else None
            if not page_price or not (0.65 <= page_price / expected_price <= 1.35):
                continue  # stub or mismatched page -> try other basis / fail
        soup = BeautifulSoup(html, "lxml")
        mcap = None
        m = re.search(r"Market Cap.{0,200}?([\d,]+(?:\.\d+)?)\s*(?:</span>)?\s*Cr", html, re.S)
        if m:
            mcap = float(m.group(1).replace(",", ""))
        sector_text = " ".join(a.get_text(strip=True)
                               for a in soup.select('a[href*="/company/compare/"]')).lower()
        qsec = soup.find("section", id="quarters")
        psec = soup.find("section", id="profit-loss")
        if not qsec or not qsec.find("table"):
            continue
        qh, qv = row_from_table(qsec.find("table"), "Net Profit")
        if not qv:
            continue
        quarters = [(h, v) for h, v in zip(qh, qv) if v is not None]
        if len(quarters) < 2:
            continue
        # detect half-yearly reporting (common for SME): median gap between period ends > 120 days
        def pdate(h):
            try:
                return datetime.strptime(h, "%b %Y").date()
            except ValueError:
                return None
        pds = [pdate(h) for h, _ in quarters]
        gaps = [(b - a).days for a, b in zip(pds, pds[1:]) if a and b]
        win = 2 if (gaps and sorted(gaps)[len(gaps) // 2] > 120) else 4
        vals = [v for _, v in quarters]
        if len(vals) < win:
            continue
        ttm = sum(vals[-win:])
        windows = [sum(vals[i:i + win]) for i in range(len(vals) - win + 1)]
        prior_win_max = max(windows[:-1]) if len(windows) > 1 else None
        annual_max = None
        if psec and psec.find("table"):
            ph, pv = row_from_table(psec.find("table"), "Net Profit")
            if pv:
                annual = [v for h, v in zip(ph, pv) if v is not None and h.strip().upper() != "TTM"]
                annual_max = max(annual) if annual else None
        prior_peak = max([x for x in (prior_win_max, annual_max) if x is not None], default=None)
        return {"mcap": mcap, "sector_text": sector_text,
                "basis": "consolidated" if consolidated else "standalone",
                "reporting": "half-yearly" if win == 2 else "quarterly",
                "ttm_pat": round(ttm, 1),
                "prior_peak_pat": None if prior_peak is None else round(prior_peak, 1),
                "latest_q": quarters[-1][0],
                "pat_at_ath": prior_peak is None or ttm >= prior_peak - 1e-6}
    return {"error": "no screener data", "pat_at_ath": False, "mcap": None}


def sector_index_for(nse_industry, sector_text):
    if nse_industry and nse_industry in SECTOR_BY_NSE_INDUSTRY:
        return SECTOR_BY_NSE_INDUSTRY[nse_industry]
    t = (sector_text or "").lower()
    for keys, idx in SECTOR_KEYWORDS:
        if any(k in t for k in keys):
            return idx
    return None


# ---------------- universe ----------------
def load_universe():
    r = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv",
                     headers=UA, timeout=30)
    r.raise_for_status()
    main = []
    for row in csv.DictReader(io.StringIO(r.text)):
        row = {k.strip(): (v or "").strip() for k, v in row.items()}
        if row.get("SERIES") == "EQ" and not row["SYMBOL"].startswith("DUMMY"):
            main.append({"symbol": row["SYMBOL"], "name": row["NAME OF COMPANY"], "board": "Main"})
    industry = {}
    try:
        r2 = requests.get("https://archives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv",
                          headers=UA, timeout=30)
        for row in csv.DictReader(io.StringIO(r2.text)):
            industry[row["Symbol"].strip()] = row["Industry"].strip()
    except Exception:
        pass
    for u in main:
        u["nse_industry"] = industry.get(u["symbol"])
    smes = []
    sme_path = os.path.join(DATA, "sme_prices.json")
    if os.path.exists(sme_path):
        store = json.load(open(sme_path))
        symbols = store.get("symbols", store)  # new schema {"symbols": {...}} or legacy flat
        cutoff = (TODAY - timedelta(days=14)).strftime("%Y%m%d")
        for sym, obj in symbols.items():
            if obj["px"] and obj["px"][-1][0] >= cutoff:  # still trading
                smes.append({"symbol": sym, "name": sym, "board": "SME", "nse_industry": None,
                             "_px": obj["px"]})
    return main, smes


# ---------------- main ----------------
def main():
    main_u, sme_u = load_universe()
    print(f"universe: {len(main_u)} mainboard + {len(sme_u)} SME", flush=True)
    idx = IndexReturns()
    for req in ["NIFTY 500", "NIFTY TOTAL MARKET", SME_BENCH]:
        assert req in idx.end, f"index missing from snapshot: {req}"

    candidates = []
    # mainboard via Yahoo
    def work(u):
        d = yahoo_daily(u["symbol"] + ".NS")
        time.sleep(random.uniform(0.02, 0.1))
        return u, d
    fails = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(work, u) for u in main_u]
        for n, fut in enumerate(as_completed(futs), 1):
            u, d = fut.result()
            if n % 250 == 0:
                print(f"  yahoo {n}/{len(main_u)}", flush=True)
            if d is None:
                fails += 1
                continue
            met = series_metrics(*d)
            if met and met["pct_from_ath"] >= -ATH_TOL * 100:
                candidates.append({**u, **met})
    print(f"mainboard fetched (missing {fails}), in ATH zone: {len(candidates)}", flush=True)

    # SME from bhavcopy store (unadjusted closes; history since Jul-2024)
    sme_zone = 0
    for u in sme_u:
        dts = [datetime.strptime(t, "%Y%m%d").date() for t, _ in u["_px"]]
        cls = [c for _, c in u["_px"]]
        met = series_metrics(dts, cls)
        if met and met["pct_from_ath"] >= -ATH_TOL * 100:
            candidates.append({**{k: v for k, v in u.items() if k != "_px"}, **met,
                               "truncated_history": dts[0] <= date(2024, 7, 5)})
            sme_zone += 1
    print(f"SME in ATH zone: {sme_zone}", flush=True)

    # outperformance gate (matched window via anchor_date)
    stage2 = []
    for c in candidates:
        if c["stock_ret"] is None:
            continue
        anchor = datetime.strptime(c["anchor_date"], "%Y-%m-%d").date()
        n500 = idx.ret("Nifty 500", anchor)
        ntm = idx.ret("Nifty Total Market", anchor)
        bench_extra = idx.ret(SME_BENCH, anchor) if c["board"] == "SME" else None
        if n500 is None or c["stock_ret"] <= n500:
            continue
        if ntm is not None and c["stock_ret"] <= ntm:
            continue
        if bench_extra is not None and c["stock_ret"] <= bench_extra:
            continue
        c.update({"n500_ret": round(n500, 2), "ntm_ret": None if ntm is None else round(ntm, 2),
                  "sme_ret": None if bench_extra is None else round(bench_extra, 2)})
        stage2.append(c)
    print(f"outperforming broad benchmarks: {len(stage2)}", flush=True)

    # fundamentals gate
    finalists, pat_pass = [], 0
    for i, c in enumerate(stage2, 1):
        f = fundamentals(c["symbol"], expected_price=c["last_close"])
        if i % 20 == 0:
            print(f"  screener {i}/{len(stage2)}", flush=True)
        c.update(f)
        if not f.get("pat_at_ath"):
            continue
        pat_pass += 1
        sec = sector_index_for(c.get("nse_industry"), f.get("sector_text"))
        c["sector_index"] = sec
        c["sector_ret"] = None
        if sec and c["board"] == "Main":
            anchor = datetime.strptime(c["anchor_date"], "%Y-%m-%d").date()
            sr = idx.ret(sec, anchor)
            c["sector_ret"] = None if sr is None else round(sr, 2)
            if sr is not None and c["stock_ret"] <= sr:
                continue
        if f.get("mcap") is None or not (MCAP_MIN <= f["mcap"] <= MCAP_MAX):
            continue
        finalists.append(c)
    print(f"PAT at ATH: {pat_pass}; after sector + mcap band: {len(finalists)}", flush=True)

    finalists.sort(key=lambda x: (x["zone_entry"], x["stock_ret"]), reverse=True)

    prev_syms = set()
    state_path = os.path.join(DATA, "state.json")
    if os.path.exists(state_path):
        try:
            prev_syms = {f["symbol"] for f in json.load(open(state_path)).get("finalists", [])}
        except Exception:
            pass
    now_syms = {f["symbol"] for f in finalists}
    for f in finalists:
        f["is_new"] = f["symbol"] not in prev_syms if prev_syms else None
        f.pop("sector_text", None)
    dropped = sorted(prev_syms - now_syms)

    state = {"run_date": str(TODAY), "asof": str(idx.end_date),
             "funnel": {"mainboard": len(main_u), "sme": len(sme_u),
                        "ath_zone": len(candidates), "outperforming": len(stage2),
                        "pat_at_ath": pat_pass, "final": len(finalists)},
             "benchmarks": {"Nifty 500": idx.ret("Nifty 500", TODAY - timedelta(days=TTM_DAYS)),
                            "Nifty Total Market": idx.ret("Nifty Total Market", TODAY - timedelta(days=TTM_DAYS)),
                            "NIFTY SME EMERGE": idx.ret(SME_BENCH, TODAY - timedelta(days=TTM_DAYS))},
             "dropped_since_last": dropped, "had_previous": bool(prev_syms),
             "finalists": finalists}
    json.dump(state, open(state_path, "w"), indent=1)
    json.dump(state, open(os.path.join(DOCS, "data.json"), "w"))
    print("state written:", len(finalists), "finalists", flush=True)

    import build_page
    build_page.build(state)
    import build_xlsx
    build_xlsx.build(state)
    print("site + xlsx built", flush=True)


if __name__ == "__main__":
    main()
