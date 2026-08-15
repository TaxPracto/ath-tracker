#!/usr/bin/env python3
"""Generate docs/history.html — weekly archive + staying power; what-happened-after stats
activate automatically once appearances are 28+ days old. Static HTML, no JS."""
import json, os, re, bisect
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
BASE = os.path.dirname(os.path.abspath(__file__))
PXCACHE = os.path.join(BASE, "cache", "px")

HEAD = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ATH Radar — History</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#F7F5F0;--ink:#1F2328;--sub:#6B6F76;--line:#E4E0D8;--card:#FFFFFF;--green:#0E7C3A;--greenbg:#E7F3EA;--red:#B3261E;--gold:#8A6D1D;--goldbg:#F5EDD8;--blue:#1F3864}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:'Instrument Sans',sans-serif;font-size:15px;line-height:1.5}
.wrap{max-width:1100px;margin:0 auto;padding:28px 20px 60px}
h1{font-family:Fraunces,serif;font-size:30px;margin:0 0 4px}
h2{font-family:Fraunces,serif;font-size:20px;margin:30px 0 10px}
.sub{color:var(--sub)}.mono{font-family:'IBM Plex Mono',monospace}
a.nav{color:var(--blue);text-decoration:none;font-weight:600}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13.5px}
th{background:var(--blue);color:#fff;text-align:left;padding:8px 10px;font-weight:600}
td{padding:8px 10px;border-top:1px solid var(--line)}
.num{font-family:'IBM Plex Mono',monospace;text-align:right;white-space:nowrap}
.pos{color:var(--green)}.neg{color:var(--red)}
.tag{display:inline-block;border-radius:6px;padding:1px 7px;font-size:11.5px;font-weight:600}
.tag.sme{background:var(--goldbg);color:var(--gold)}.tag.main{background:#E8EDF7;color:var(--blue)}
.tag.t2t{background:#FBEAEA;color:var(--red)}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:8px 0;padding:10px 14px}
summary{cursor:pointer;font-weight:600}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin-top:10px}
.small{font-size:12.5px;color:var(--sub)}
.footer{margin-top:34px;padding-top:12px;border-top:1px solid var(--line);font-size:12.5px;color:var(--sub)}
</style></head><body><div class="wrap">
<div style="display:flex;justify-content:space-between;align-items:baseline">
<h1>ATH Radar — History</h1><a class="nav" href="index.html">← back to the radar</a></div>
<div class="sub">Every weekly list, how long names stay on it, and — once enough weeks accumulate — what happened after they appeared.</div>
"""


def _sym_tag(f):
    t2t = ' <span class="tag t2t">T2T</span>' if f.get("t2t") else ""
    board = ('<span class="tag sme">SME·' + (f.get("exch") or "NSE") + "</span>"
             if f.get("board") == "SME" else '<span class="tag main">Main</span>')
    link = f.get("scr_slug") or f["symbol"]
    return (f'<a class="nav" href="https://www.screener.in/company/{link}/" target="_blank">'
            f'{f["symbol"]}</a> {board}{t2t}')


def _series_for(f):
    """(dates, closes) for a symbol using local caches; None if unavailable."""
    if f.get("board") == "SME":
        store = _series_for._store
        if store is None:
            return None
        key = ("BSE:" + f["scr_slug"]) if f.get("exch") == "BSE" else f["symbol"]
        rec = store.get(key)
        if not rec:
            return None
        return ([datetime.strptime(t, "%Y%m%d").date() for t, _ in rec["px"]],
                [c for _, c in rec["px"]])
    key = re.sub(r"[^A-Za-z0-9._-]", "_", f["symbol"] + ".NS")
    path = os.path.join(PXCACHE, key + ".json")
    if not os.path.exists(path):
        return None
    try:
        res = json.load(open(path))["chart"]["result"][0]
        pairs = [(datetime.fromtimestamp(t).date(), c)
                 for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c]
        return [p[0] for p in pairs], [p[1] for p in pairs]
    except Exception:
        return None


_series_for._store = None


def _price_on_or_after(series, target):
    dts, cls = series
    i = bisect.bisect_left(dts, target)
    if i >= len(dts):
        return None
    return cls[i]


def build(hist):
    sme_path = os.path.join(BASE, "data", "sme_prices.json")
    _series_for._store = (json.load(open(sme_path)).get("symbols")
                          if os.path.exists(sme_path) else None)
    weeks = sorted(hist, key=lambda h: h["date"], reverse=True)  # newest first
    out = [HEAD]

    # ---- staying power (current list) ----
    out.append("<h2>Staying power — current list</h2>")
    if weeks:
        cur = weeks[0]
        present = [{h["date"]: {f["symbol"] for f in h["finalists"]}} for h in weeks]
        week_sets = [set(f["symbol"] for f in h["finalists"]) for h in weeks]
        rows = []
        for f in cur["finalists"]:
            streak = 0
            for ws in week_sets:
                if f["symbol"] in ws:
                    streak += 1
                else:
                    break
            first_seen = min(h["date"] for h in weeks if f["symbol"] in
                             {x["symbol"] for x in h["finalists"]})
            rows.append((streak, first_seen, f))
        rows.sort(key=lambda r: (-r[0], r[2]["symbol"]))
        body = "".join(
            f'<tr><td>{_sym_tag(f)}</td><td>{f["name"][:36]}</td>'
            f'<td class="num">{streak}</td><td class="num">{first_seen}</td>'
            f'<td class="num">{f["mcap"]:,.0f}</td>'
            f'<td class="num">{f["pe"] if f.get("pe") is not None else "—"}</td>'
            f'<td class="num">{f["zone_entry"]}</td></tr>'
            for streak, first_seen, f in rows)
        out.append('<table><tr><th>Stock</th><th>Company</th><th class="num">Weeks on list</th>'
                   '<th class="num">First seen</th><th class="num">Mkt Cap Rs Cr</th>'
                   '<th class="num">P/E</th><th class="num">Entered ATH zone</th></tr>'
                   + body + "</table>")

    # ---- what happened after (auto-activates) ----
    out.append("<h2>What happened after a name appeared</h2>")
    aged = []
    today = date.today()
    for h in weeks:
        d0 = datetime.strptime(h["date"], "%Y-%m-%d").date()
        if (today - d0).days < 28:
            continue
        for f in h["finalists"]:
            s = _series_for(f)
            if not s:
                continue
            p0 = f.get("last_close")
            if not p0:
                continue
            r4 = _price_on_or_after(s, d0 + timedelta(days=28))
            r12 = _price_on_or_after(s, d0 + timedelta(days=84)) if (today - d0).days >= 84 else None
            aged.append({"week": h["date"], "f": f,
                         "r4": None if r4 is None else (r4 / p0 - 1) * 100,
                         "r12": None if r12 is None else (r12 / p0 - 1) * 100})
    if not aged:
        out.append('<div class="box sub">Collecting data — this section switches on automatically '
                   'once appearances are 4+ weeks old. Each name will show its +4-week and '
                   '+12-week move from the Friday it appeared.</div>')
    else:
        r4s = sorted(a["r4"] for a in aged if a["r4"] is not None)
        med4 = r4s[len(r4s) // 2] if r4s else None
        pos4 = (100 * sum(1 for x in r4s if x > 0) / len(r4s)) if r4s else None
        out.append(f'<div class="box"><b>{len(aged)}</b> appearances measured so far · '
                   f'typical (+4w) move <b class="mono">{med4:+.1f}%</b> · '
                   f'rose in <b class="mono">{pos4:.0f}%</b> of cases. '
                   f'<span class="small">More weeks watched = more trust; under ~20 is a hint, not a verdict.</span></div>')
        body = "".join(
            f'<tr><td class="num">{a["week"]}</td><td>{_sym_tag(a["f"])}</td>'
            f'<td class="num">{a["f"]["last_close"]:,.1f}</td>'
            f'<td class="num {"pos" if (a["r4"] or 0) > 0 else "neg"}">'
            f'{"" if a["r4"] is None else format(a["r4"], "+.1f") + "%"}</td>'
            f'<td class="num {"pos" if (a["r12"] or 0) > 0 else "neg"}">'
            f'{"—" if a["r12"] is None else format(a["r12"], "+.1f") + "%"}</td></tr>'
            for a in aged)
        out.append('<table><tr><th>Appeared</th><th>Stock</th><th class="num">Close then</th>'
                   '<th class="num">+4 weeks</th><th class="num">+12 weeks</th></tr>' + body + "</table>")

    # ---- weekly archive ----
    out.append("<h2>Weekly archive</h2>")
    for i, h in enumerate(weeks):
        prev = set(f["symbol"] for f in weeks[i + 1]["finalists"]) if i + 1 < len(weeks) else None
        items = []
        for f in sorted(h["finalists"], key=lambda x: x["symbol"]):
            new = ' <span class="tag" style="background:#0E7C3A;color:#fff">NEW</span>' \
                if prev is not None and f["symbol"] not in prev else ""
            pe = f' · PE {f["pe"]:.0f}' if f.get("pe") else ""
            items.append(f'<div>{_sym_tag(f)} <span class="small">'
                         f'{f["mcap"]:,.0f} Cr{pe} · TTM {f["stock_ret"]:+.0f}%</span>{new}</div>')
        out.append(f'<details{" open" if i == 0 else ""}><summary>{h["date"]} — '
                   f'{len(h["finalists"])} stocks</summary>'
                   f'<div style="columns:2;gap:30px;margin-top:8px">{"".join(items)}</div></details>')

    out.append(f'<div class="footer">Generated {datetime.now(IST).strftime("%d %b %Y, %H:%M IST")} · '
               f'<a class="nav" href="index.html">current radar</a><br>'
               f'Factual screen for research — not investment advice.</div>')
    out.append("</div></body></html>")
    path = os.path.join(BASE, "docs", "history.html")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    print("wrote", path)


if __name__ == "__main__":
    build(json.load(open(os.path.join(BASE, "data", "history.json"))))
