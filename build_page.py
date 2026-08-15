#!/usr/bin/env python3
"""Generate docs/index.html from state. Placeholder replacement (no f-string braces issues)."""
import json, os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

TPL = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ATH Radar — stocks at lifetime highs with record profits</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#F7F5F0;--ink:#1F2328;--sub:#6B6F76;--line:#E4E0D8;--card:#FFFFFF;--green:#0E7C3A;--greenbg:#E7F3EA;--red:#B3261E;--gold:#8A6D1D;--goldbg:#F5EDD8;--blue:#1F3864}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:'Instrument Sans',sans-serif;font-size:15px;line-height:1.5}
.wrap{max-width:1280px;margin:0 auto;padding:28px 20px 60px}
h1{font-family:Fraunces,serif;font-size:34px;margin:0 0 4px}
h2{font-family:Fraunces,serif;font-size:21px;margin:34px 0 10px}
.sub{color:var(--sub)}.mono{font-family:'IBM Plex Mono',monospace}
.funnel{margin:14px 0 6px;display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:13px}
.chip b{font-family:'IBM Plex Mono',monospace}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13.5px}
th{background:var(--blue);color:#fff;text-align:left;padding:9px 10px;font-weight:600;white-space:nowrap}
td{padding:9px 10px;border-top:1px solid var(--line);vertical-align:top}
tr.new td{background:var(--greenbg)}
.num{font-family:'IBM Plex Mono',monospace;text-align:right;white-space:nowrap}
.pos{color:var(--green)}.neg{color:var(--red)}
.tag{display:inline-block;border-radius:6px;padding:1px 7px;font-size:11.5px;font-weight:600}
.tag.sme{background:var(--goldbg);color:var(--gold)}.tag.main{background:#E8EDF7;color:var(--blue)}
.tag.newtag{background:var(--green);color:#fff;margin-left:6px}
.sym a{color:var(--blue);text-decoration:none;font-weight:600}.sym a:hover{text-decoration:underline}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-top:12px}
.box p{margin:6px 0}
.small{font-size:12.5px;color:var(--sub)}
.newstrip{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 4px}
.ncard{background:var(--card);border:1px solid var(--green);border-radius:10px;padding:10px 14px}
.ncard .nm{font-weight:600}
.footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);font-size:12.5px;color:var(--sub)}
a.dl{color:var(--blue)}
@media(max-width:900px){.hide-m{display:none}}
</style></head><body><div class="wrap">
<h1>ATH Radar</h1>
<div class="sub">Stocks within 2% of their all-time high, with all-time-high trailing profits, beating the market and their sector — market cap Rs 1,000–20,000 Cr. Sorted by newest arrival at the high.</div>
<div class="funnel">__FUNNEL__</div>
<div class="small">Prices as of __ASOF__ · generated __GENERATED__ · benchmarks (TTM): __BENCH__</div>
<h2>__NEWHDR__</h2>
<div class="newstrip">__NEWSTRIP__</div>
<h2>Current list (__NFIN__)</h2>
<table>
<tr><th>#</th><th>Stock</th><th class="hide-m">Company</th><th>Board</th><th class="hide-m">Sector index</th><th>Mkt Cap<br>Rs Cr</th><th>Entered<br>ATH zone</th><th>% from<br>ATH</th><th>TTM<br>return</th><th>vs N500<br>pp</th><th class="hide-m">vs sector/SME<br>pp</th><th>TTM PAT vs peak<br>Rs Cr</th></tr>
__ROWS__
</table>
<h2>Dropped since last run</h2>
<div>__DROPPED__</div>
<h2>How this list is made</h2>
<div class="box">
<p><b>Universe.</b> Every NSE mainboard stock (~2,400) plus NSE Emerge SMEs (~450).</p>
<p><b>Filter 1 — price at lifetime high.</b> Last close within 2% of the highest daily close ever (split-adjusted for mainboard; SME prices from exchange bhavcopies, history since Jul 2024, unadjusted for corporate actions).</p>
<p><b>Filter 2 — outperformance.</b> Trailing-12-month return strictly above the Nifty 500 AND Nifty Total Market; SMEs must also beat NIFTY SME EMERGE; mainboard stocks with a mapped sector index must also beat that sector. Stocks listed under a year use a matched window from listing.</p>
<p><b>Filter 3 — profits at lifetime high.</b> Trailing-12-month net profit (sum of last 4 quarters, or 2 half-years for SME reporters; consolidated preferred) must be at least every annual profit on record (~12 visible years) and every prior rolling window. Source: screener.in.</p>
<p><b>Filter 4 — size.</b> Market cap between Rs 1,000 Cr and Rs 20,000 Cr.</p>
<p><b>Sort.</b> Newest entrant first — the day the stock last crossed into the 2%-of-ATH zone. Green rows are new to the list since the previous weekly run.</p>
<p class="small">Caveats: profit history is limited to what screener.in shows (~12 years); SME all-time highs only reach back to Jul 2024 and ignore splits/bonuses (a split-affected SME may be missed); companies without screener data are excluded. Runs every Friday evening after market close.</p>
</div>
<div class="footer">Download: <a class="dl" href="ATH_Tracker_latest.xlsx">Excel workbook</a> · <a class="dl" href="data.json">raw data (JSON)</a><br>
This is a factual screen for research and education. It is not investment advice and not a recommendation to buy or sell anything.</div>
</div></body></html>
"""


def _fmt(x, plus=False, dec=1):
    if x is None:
        return "—"
    s = f"{x:+.{dec}f}" if plus else f"{x:,.{dec}f}"
    return s


def build(state):
    f = state["funnel"]
    funnel = (f'<span class="chip">Screened <b>{f["mainboard"]:,} main + {f["sme"]:,} SME</b></span>'
              f'<span class="chip">At ATH <b>{f["ath_zone"]}</b></span>'
              f'<span class="chip">Outperforming <b>{f["outperforming"]}</b></span>'
              f'<span class="chip">Record TTM PAT <b>{f["pat_at_ath"]}</b></span>'
              f'<span class="chip">Rs 1k–20k Cr band <b>{f["final"]}</b></span>')
    b = state["benchmarks"]
    bench = " · ".join(f"{k} <span class='mono'>{_fmt(v, plus=True)}%</span>" for k, v in b.items())

    fins = state["finalists"]
    new_names = [x for x in fins if x.get("is_new")]
    if not state.get("had_previous"):
        newhdr = "First run — baseline week"
        newstrip = '<div class="ncard sub">Every future run will highlight fresh arrivals here.</div>'
    elif new_names:
        newhdr = f"New this week ({len(new_names)})"
        newstrip = "".join(
            f'<div class="ncard"><span class="nm">{x["symbol"]}</span> '
            f'<span class="small">entered the ATH zone {x["zone_entry"]}</span></div>' for x in new_names)
    else:
        newhdr = "New this week"
        newstrip = '<div class="ncard sub">No new names this week.</div>'

    rows = []
    for i, x in enumerate(fins, 1):
        alpha1 = None if x.get("n500_ret") is None else x["stock_ret"] - x["n500_ret"]
        if x["board"] == "SME":
            alpha2 = None if x.get("sme_ret") is None else x["stock_ret"] - x["sme_ret"]
            sec_label = "SME Emerge"
        else:
            alpha2 = None if x.get("sector_ret") is None else x["stock_ret"] - x["sector_ret"]
            sec_label = x.get("sector_index") or "—"
        newtag = '<span class="tag newtag">NEW</span>' if x.get("is_new") else ""
        cls = ' class="new"' if x.get("is_new") else ""
        pat_pct = ""
        if x.get("prior_peak_pat") and x["prior_peak_pat"] > 0:
            pat_pct = f' <span class="pos">({(x["ttm_pat"]/x["prior_peak_pat"]-1)*100:+.0f}%)</span>'
        note = " *" if x.get("truncated_history") else ""
        win = "" if x.get("window_days", 365) >= 360 else f'<div class="small">listed &lt;1y</div>'
        rows.append(
            f'<tr{cls}><td class="num">{i}</td>'
            f'<td class="sym"><a href="https://www.screener.in/company/{x["symbol"]}/" target="_blank">{x["symbol"]}</a>{newtag}{note}</td>'
            f'<td class="hide-m">{x["name"][:38]}</td>'
            f'<td><span class="tag {"sme" if x["board"]=="SME" else "main"}">{x["board"]}</span></td>'
            f'<td class="hide-m">{sec_label}</td>'
            f'<td class="num">{_fmt(x.get("mcap"), dec=0)}</td>'
            f'<td class="num">{x["zone_entry"]}<div class="small">{x["days_in_zone"]}d in zone</div></td>'
            f'<td class="num">{_fmt(x["pct_from_ath"])}%</td>'
            f'<td class="num pos">{_fmt(x["stock_ret"], plus=True)}%{win}</td>'
            f'<td class="num">{_fmt(alpha1, plus=True, dec=0)}</td>'
            f'<td class="num hide-m">{_fmt(alpha2, plus=True, dec=0)}</td>'
            f'<td class="num">{_fmt(x.get("ttm_pat"), dec=0)} vs {_fmt(x.get("prior_peak_pat"), dec=0)}{pat_pct}'
            f'<div class="small">{x.get("basis","")}{", half-yearly" if x.get("reporting")=="half-yearly" else ""}</div></td></tr>')

    dropped = state.get("dropped_since_last") or []
    dropped_html = (" · ".join(f'<span class="mono">{s}</span>' for s in dropped)
                    if dropped else '<span class="sub">None.</span>' if state.get("had_previous")
                    else '<span class="sub">First run — nothing to compare against yet.</span>')

    html = (TPL.replace("__FUNNEL__", funnel)
            .replace("__ASOF__", state["asof"])
            .replace("__GENERATED__", datetime.now().strftime("%d %b %Y, %H:%M IST"))
            .replace("__BENCH__", bench)
            .replace("__NEWHDR__", newhdr)
            .replace("__NEWSTRIP__", newstrip)
            .replace("__NFIN__", str(len(fins)))
            .replace("__ROWS__", "\n".join(rows) if rows else '<tr><td colspan="12" class="sub">No stock passes every filter this week.</td></tr>')
            .replace("__DROPPED__", dropped_html))
    out = os.path.join(BASE, "docs", "index.html")
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out)


if __name__ == "__main__":
    build(json.load(open(os.path.join(BASE, "data", "state.json"))))
