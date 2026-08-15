#!/usr/bin/env python3
"""Generate docs/index.html from state. Placeholder .replace() template — no f-string braces.
v2: sortable headers, search, board/entered/mcap pills, sector select, NEW toggle, live count.
JS is a plain string: NO backslashes, NO regex literals (see CLAUDE.md pitfalls)."""
import json, os
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
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
.wrap{max-width:1340px;margin:0 auto;padding:28px 20px 60px}
h1{font-family:Fraunces,serif;font-size:34px;margin:0 0 4px}
h2{font-family:Fraunces,serif;font-size:21px;margin:34px 0 10px}
.sub{color:var(--sub)}.mono{font-family:'IBM Plex Mono',monospace}
.funnel{margin:14px 0 6px;display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:13px}
.chip b{font-family:'IBM Plex Mono',monospace}
.controls{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:14px 0 10px;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
.controls label{font-size:12px;color:var(--sub);display:block;margin-bottom:3px}
.grp{display:flex;gap:6px;flex-wrap:wrap}
.pill{border:1px solid var(--line);background:var(--bg);border-radius:999px;padding:4px 12px;font-size:12.5px;cursor:pointer;user-select:none}
.pill.on{background:var(--blue);color:#fff;border-color:var(--blue)}
#q{border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:13.5px;font-family:inherit;width:190px}
#sec{border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:13px;font-family:inherit;max-width:210px}
#cnt{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--sub);margin-left:auto}
#reset{background:none;border:none;color:var(--blue);cursor:pointer;font-size:12.5px;text-decoration:underline;padding:0}
.newtogl{display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13.5px}
th{background:var(--blue);color:#fff;text-align:left;padding:9px 8px;font-weight:600;white-space:nowrap}
th.s{cursor:pointer}th.s:hover{background:#2a4a80}
th .ar{color:#F2C14E;font-size:11px;margin-left:3px}
td{padding:8px;border-top:1px solid var(--line);vertical-align:top}
tr.new td{background:var(--greenbg)}
.num{font-family:'IBM Plex Mono',monospace;text-align:right;white-space:nowrap}
.pos{color:var(--green)}.neg{color:var(--red)}
.tag{display:inline-block;border-radius:6px;padding:1px 7px;font-size:11.5px;font-weight:600}
.tag.sme{background:var(--goldbg);color:var(--gold)}.tag.main{background:#E8EDF7;color:var(--blue)}
.tag.newtag{background:var(--green);color:#fff;margin-left:6px}
.tag.t2t{background:#FBEAEA;color:var(--red)}
.sym a{color:var(--blue);text-decoration:none;font-weight:600}.sym a:hover{text-decoration:underline}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-top:12px}
.box p{margin:6px 0}
.small{font-size:12.5px;color:var(--sub)}
.newstrip{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 4px}
.ncard{background:var(--card);border:1px solid var(--green);border-radius:10px;padding:10px 14px}
.ncard .nm{font-weight:600}
.footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);font-size:12.5px;color:var(--sub)}
a.dl{color:var(--blue)}
@media(max-width:980px){.hide-m{display:none}}
</style></head><body>
<div class="wrap">
<h1>ATH Radar</h1>
<div class="sub">Stocks within 2% of their all-time high, with all-time-high trailing profits, beating the market and their sector — market cap Rs 1,000–20,000 Cr. Sorted by newest arrival at the high.</div>
<div class="funnel">__FUNNEL__</div>
<div class="small">Prices as of __ASOF__ · generated __GENERATED__ · benchmarks (TTM): __BENCH__ · <a class="dl" href="history.html"><b>History &amp; staying power →</b></a></div>
<h2>__NEWHDR__</h2>
<div class="newstrip">__NEWSTRIP__</div>
<h2>Current list</h2>
<div class="controls">
  <div><label>Search</label><input id="q" type="text" placeholder="symbol or company"></div>
  <div><label>Board</label><div class="grp" data-g="board">
    <span class="pill on" data-v="All">All</span><span class="pill" data-v="Main">Main</span><span class="pill" data-v="SME">SME</span></div></div>
  <div><label>Entered ATH zone</label><div class="grp" data-g="days">
    <span class="pill on" data-v="0">Any time</span><span class="pill" data-v="3">Last 3 sessions</span><span class="pill" data-v="7">~1 week</span><span class="pill" data-v="14">~2 weeks</span></div></div>
  <div><label>Market cap (Rs Cr)</label><div class="grp" data-g="mcap">
    <span class="pill on" data-v="All">All</span><span class="pill" data-v="1-5">1k–5k</span><span class="pill" data-v="5-10">5k–10k</span><span class="pill" data-v="10-20">10k–20k</span></div></div>
  <div><label>Sector</label><select id="sec"><option value="All">All sectors</option>__SECOPTS__</select></div>
  __NEWTOGL__
  <div style="align-self:flex-end"><button id="reset">reset</button></div>
  <div id="cnt" style="align-self:flex-end"></div>
</div>
<table id="tbl">
<thead><tr>
<th>#</th>
<th class="s" data-i="1" data-t="s">Stock<span class="ar"></span></th>
<th class="s hide-m" data-i="2" data-t="s">Company<span class="ar"></span></th>
<th class="s" data-i="3" data-t="s">Board<span class="ar"></span></th>
<th class="s hide-m" data-i="4" data-t="s">Sector index<span class="ar"></span></th>
<th class="s" data-i="5" data-t="n">Mkt Cap<br>Rs Cr<span class="ar"></span></th>
<th class="s" data-i="6" data-t="n">P/E<span class="ar"></span></th>
<th class="s" data-i="7" data-t="s">Entered<br>ATH zone<span class="ar"></span></th>
<th class="s" data-i="8" data-t="n">% from<br>ATH<span class="ar"></span></th>
<th class="s" data-i="9" data-t="n">3M<span class="ar"></span></th>
<th class="s" data-i="10" data-t="n">6M<span class="ar"></span></th>
<th class="s" data-i="11" data-t="n">TTM<span class="ar"></span></th>
<th class="s" data-i="12" data-t="n">vs N500<br>pp<span class="ar"></span></th>
<th class="s hide-m" data-i="13" data-t="n">vs sector/SME<br>pp<span class="ar"></span></th>
<th class="s" data-i="14" data-t="n">TTM PAT vs peak<br>Rs Cr<span class="ar"></span></th>
</tr></thead>
<tbody>
__ROWS__
</tbody>
</table>
<h2>Dropped since last run</h2>
<div>__DROPPED__</div>
<h2>How this list is made</h2>
<div class="box">
<p><b>Universe.</b> Every NSE mainboard stock — regular EQ series plus trade-for-trade BE series, badged <span class="tag t2t">T2T</span> (~2,650 total) — plus NSE Emerge (~450) and BSE SME (~350) companies, de-duplicated by ISIN (mainboard wins on migration). T2T = delivery-only settlement, often an exchange surveillance measure: extra caution warranted.</p>
<p><b>Filter 1 — price at lifetime high.</b> Last close within 2% of the highest daily close ever (split-adjusted for mainboard; SME prices from exchange bhavcopies, history since Jul 2024, unadjusted for corporate actions).</p>
<p><b>Filter 2 — outperformance.</b> Trailing-12-month return strictly above the Nifty 500 AND Nifty Total Market; SMEs must also beat NIFTY SME EMERGE (used as proxy benchmark for BSE SME too); mainboard stocks with a mapped sector index must also beat that sector. Stocks listed under a year use a matched window from listing.</p>
<p><b>Filter 3 — profits at lifetime high.</b> Trailing-12-month net profit (last 4 quarters, or 2 half-years for SME reporters; consolidated preferred) must be at least every annual profit on record (~12 visible years) and every prior rolling window. Source: screener.in.</p>
<p><b>Filter 4 — size.</b> Market cap between Rs 1,000 Cr and Rs 20,000 Cr.</p>
<p><b>Sort.</b> Default: newest entrant first — the day the stock last crossed into the 2%-of-ATH zone. Click any column header to re-sort. Green rows are new to the list since the previous weekly run.</p>
<p class="small">Caveats: profit history is limited to what screener.in shows (~12 years); SME all-time highs only reach back to Jul 2024 and ignore splits/bonuses (a split-affected SME may be missed); companies without screener data are excluded. Runs every Friday evening after market close.</p>
</div>
<div class="footer">Download: <a class="dl" href="ATH_Tracker_latest.xlsx">Excel workbook</a> · <a class="dl" href="data.json">raw data (JSON)</a><br>
This is a factual screen for research and education. It is not investment advice and not a recommendation to buy or sell anything.</div>
</div>
<script>
var rows = Array.prototype.slice.call(document.querySelectorAll('#tbl tbody tr'));
var state = {q:'', board:'All', days:0, mcap:'All', sec:'All', newonly:false};
function apply(){
  var n = 0;
  rows.forEach(function(r){
    var d = r.dataset, v = true;
    if (state.q && (d.sym + ' ' + d.name).toLowerCase().indexOf(state.q) === -1) v = false;
    if (v && state.board !== 'All' && d.board !== state.board) v = false;
    if (v && state.days > 0 && parseInt(d.days, 10) > state.days) v = false;
    if (v && state.mcap !== 'All'){
      var m = parseFloat(d.mcap);
      if (state.mcap === '1-5' && !(m < 5000)) v = false;
      if (state.mcap === '5-10' && !(m >= 5000 && m < 10000)) v = false;
      if (state.mcap === '10-20' && !(m >= 10000)) v = false;
    }
    if (v && state.sec !== 'All' && d.sector !== state.sec) v = false;
    if (v && state.newonly && d.isnew !== '1') v = false;
    r.style.display = v ? '' : 'none';
    if (v) n++;
  });
  document.getElementById('cnt').textContent = 'showing ' + n + ' of ' + rows.length;
}
document.querySelectorAll('.grp').forEach(function(g){
  g.addEventListener('click', function(e){
    var p = e.target.closest('.pill'); if (!p) return;
    g.querySelectorAll('.pill').forEach(function(x){ x.classList.remove('on'); });
    p.classList.add('on');
    var grp = g.dataset.g;
    state[grp] = grp === 'days' ? parseInt(p.dataset.v, 10) : p.dataset.v;
    apply();
  });
});
document.getElementById('q').addEventListener('input', function(e){ state.q = e.target.value.trim().toLowerCase(); apply(); });
document.getElementById('sec').addEventListener('change', function(e){ state.sec = e.target.value; apply(); });
var nt = document.getElementById('newonly');
if (nt) nt.addEventListener('change', function(e){ state.newonly = e.target.checked; apply(); });
document.getElementById('reset').addEventListener('click', function(){
  state = {q:'', board:'All', days:0, mcap:'All', sec:'All', newonly:false};
  document.getElementById('q').value = '';
  document.getElementById('sec').value = 'All';
  if (nt) nt.checked = false;
  document.querySelectorAll('.grp').forEach(function(g){
    g.querySelectorAll('.pill').forEach(function(x, i){ x.classList.toggle('on', i === 0); });
  });
  sortReset();
  apply();
});
// ---- sorting ----
var tbody = document.querySelector('#tbl tbody');
var origOrder = rows.slice();
function cellVal(r, i, t){
  var td = r.children[i];
  var x = td.dataset.v !== undefined ? td.dataset.v : td.textContent.trim();
  if (t === 'n'){ var f = parseFloat(x); return isNaN(f) ? null : f; }
  return ('' + x).toLowerCase();
}
function clearArrows(){ document.querySelectorAll('th.s .ar').forEach(function(a){ a.textContent = ''; }); }
function sortReset(){
  clearArrows();
  document.querySelectorAll('th.s').forEach(function(h){ delete h.dataset.d; });
  origOrder.forEach(function(r){ tbody.appendChild(r); });
}
document.querySelectorAll('th.s').forEach(function(th){
  th.addEventListener('click', function(){
    var i = parseInt(th.dataset.i, 10), t = th.dataset.t;
    var dir = th.dataset.d === 'desc' ? 'asc' : 'desc';
    if (t === 's' && !th.dataset.d) dir = 'asc';
    document.querySelectorAll('th.s').forEach(function(h){ if (h !== th) delete h.dataset.d; });
    th.dataset.d = dir;
    clearArrows();
    th.querySelector('.ar').textContent = dir === 'desc' ? '▼' : '▲';
    var sorted = rows.slice().sort(function(a, b){
      var va = cellVal(a, i, t), vb = cellVal(b, i, t);
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      if (va < vb) return dir === 'asc' ? -1 : 1;
      if (va > vb) return dir === 'asc' ? 1 : -1;
      return 0;
    });
    sorted.forEach(function(r){ tbody.appendChild(r); });
  });
});
apply();
</script>
</body></html>
"""


def _fmt(x, plus=False, dec=1):
    if x is None:
        return "—"
    return f"{x:+.{dec}f}" if plus else f"{x:,.{dec}f}"


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
        newhdr, newstrip = "First run — baseline week", '<div class="ncard sub">Every future run will highlight fresh arrivals here.</div>'
    elif new_names:
        newhdr = f"New this week ({len(new_names)})"
        newstrip = "".join(f'<div class="ncard"><span class="nm">{x["symbol"]}</span> '
                           f'<span class="small">entered the ATH zone {x["zone_entry"]}</span></div>' for x in new_names)
    else:
        newhdr, newstrip = "New this week", '<div class="ncard sub">No new names this week.</div>'

    sectors = sorted({("SME Emerge" if x["board"] == "SME" else (x.get("sector_index") or "—"))
                      for x in fins})
    secopts = "".join(f'<option value="{s}">{s}</option>' for s in sectors)
    newtogl = ('<div style="align-self:flex-end"><label class="newtogl"><input type="checkbox" id="newonly"> NEW only</label></div>'
               if state.get("had_previous") else "")

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
        t2ttag = ' <span class="tag t2t" title="Trade-for-trade series: delivery-only settlement">T2T</span>' if x.get("t2t") else ""
        cls = ' class="new"' if x.get("is_new") else ""
        patpk = (x["ttm_pat"] / x["prior_peak_pat"] - 1) * 100 if x.get("prior_peak_pat") and x["prior_peak_pat"] > 0 else None
        pat_pct = f' <span class="pos">({patpk:+.0f}%)</span>' if patpk is not None else ""
        note = " *" if x.get("truncated_history") else ""
        win = "" if x.get("window_days", 365) >= 360 else '<div class="small">listed &lt;1y</div>'
        rows.append(
            f'<tr{cls} data-sym="{x["symbol"]}" data-name="{x["name"]}" data-board="{x["board"]}" '
            f'data-sector="{sec_label}" data-mcap="{x.get("mcap") or 0}" data-days="{x["days_in_zone"]}" '
            f'data-isnew="{1 if x.get("is_new") else 0}">'
            f'<td class="num">{i}</td>'
            f'<td class="sym"><a href="https://www.screener.in/company/{x.get("scr_slug") or x["symbol"]}/" target="_blank">{x["symbol"]}</a>{newtag}{t2ttag}{note}</td>'
            f'<td class="hide-m">{x["name"][:38]}</td>'
            f'<td><span class="tag {"sme" if x["board"] == "SME" else "main"}">'
            f'{("SME·" + x.get("exch", "NSE")) if x["board"] == "SME" else "Main"}</span></td>'
            f'<td class="hide-m">{sec_label}</td>'
            f'<td class="num" data-v="{x.get("mcap") or ""}">{_fmt(x.get("mcap"), dec=0)}</td>'
            f'<td class="num" data-v="{x.get("pe") if x.get("pe") is not None else ""}">{_fmt(x.get("pe"), dec=0)}</td>'
            f'<td class="num" data-v="{x["zone_entry"]}">{x["zone_entry"]}<div class="small">{x["days_in_zone"]}d in zone</div></td>'
            f'<td class="num" data-v="{x["pct_from_ath"]}">{_fmt(x["pct_from_ath"])}%</td>'
            f'<td class="num" data-v="{x.get("ret_3m") if x.get("ret_3m") is not None else ""}">{_fmt(x.get("ret_3m"), plus=True, dec=0)}%</td>'
            f'<td class="num" data-v="{x.get("ret_6m") if x.get("ret_6m") is not None else ""}">{_fmt(x.get("ret_6m"), plus=True, dec=0)}%</td>'
            f'<td class="num pos" data-v="{x["stock_ret"]}">{_fmt(x["stock_ret"], plus=True)}%{win}</td>'
            f'<td class="num" data-v="{alpha1 if alpha1 is not None else ""}">{_fmt(alpha1, plus=True, dec=0)}</td>'
            f'<td class="num hide-m" data-v="{alpha2 if alpha2 is not None else ""}">{_fmt(alpha2, plus=True, dec=0)}</td>'
            f'<td class="num" data-v="{patpk if patpk is not None else ""}">{_fmt(x.get("ttm_pat"), dec=0)} vs {_fmt(x.get("prior_peak_pat"), dec=0)}{pat_pct}'
            f'<div class="small">{x.get("basis", "")}{", half-yearly" if x.get("reporting") == "half-yearly" else ""}</div></td></tr>')

    dropped = state.get("dropped_since_last") or []
    dropped_html = (" · ".join(f'<span class="mono">{s}</span>' for s in dropped)
                    if dropped else '<span class="sub">None.</span>' if state.get("had_previous")
                    else '<span class="sub">First run — nothing to compare against yet.</span>')

    html = (TPL.replace("__FUNNEL__", funnel)
            .replace("__ASOF__", state["asof"])
            .replace("__GENERATED__", datetime.now(IST).strftime("%d %b %Y, %H:%M IST"))
            .replace("__BENCH__", bench)
            .replace("__NEWHDR__", newhdr)
            .replace("__NEWSTRIP__", newstrip)
            .replace("__SECOPTS__", secopts)
            .replace("__NEWTOGL__", newtogl)
            .replace("__ROWS__", "\n".join(rows) if rows else '<tr><td colspan="15" class="sub">No stock passes every filter this week.</td></tr>')
            .replace("__DROPPED__", dropped_html))
    out = os.path.join(BASE, "docs", "index.html")
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out)


if __name__ == "__main__":
    build(json.load(open(os.path.join(BASE, "data", "state.json"))))
