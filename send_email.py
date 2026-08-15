#!/usr/bin/env python3
"""Friday digest email. Credentials ONLY from env (GitHub Actions secrets):
GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DIGEST_TO. Never hardcode.
Email-client rules learned the hard way: NO colors on <tr> (clients strip them ->
white-on-white headers); every color goes on the individual <td> as BOTH bgcolor
attribute and inline style. Table-based layout only.
Usage: python send_email.py [--preview]
"""
import json, os, smtplib, ssl, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://taxpracto.github.io/ath-tracker/"
BLUE, INK, SUB, GREENBG, LINE = "#1F3864", "#222222", "#666666", "#e2efda", "#e0ddd5"


def fmt(x, plus=False, dec=1):
    if x is None:
        return "&ndash;"
    return (f"{x:+.{dec}f}" if plus else f"{x:,.{dec}f}")


def th(label, align="left"):
    return (f'<td bgcolor="{BLUE}" align="{align}" style="background-color:{BLUE};'
            f'color:#ffffff;font-weight:bold;padding:7px 8px;font-size:12px;'
            f'font-family:Arial,sans-serif;white-space:nowrap">{label}</td>')


def td(val, align="left", bg="#ffffff", color=INK, bold=False):
    w = "font-weight:bold;" if bold else ""
    return (f'<td bgcolor="{bg}" align="{align}" style="background-color:{bg};color:{color};'
            f'{w}padding:6px 8px;font-size:12px;font-family:Arial,sans-serif;'
            f'border-bottom:1px solid {LINE};white-space:nowrap">{val}</td>')


def build_html(state):
    f = state["funnel"]
    fins = state["finalists"]
    new = [x for x in fins if x.get("is_new")]
    dropped = state.get("dropped_since_last") or []

    rows = ""
    for i, x in enumerate(fins, 1):
        a1 = None if x.get("n500_ret") is None else x["stock_ret"] - x["n500_ret"]
        bg = GREENBG if x.get("is_new") else "#ffffff"
        warn = " &#9888;" if (x.get("audit_flag") or x.get("corp_flag")) else ""
        t2t = " <span style='color:#B3261E;font-size:10px'>T2T</span>" if x.get("t2t") else ""
        board = ("SME-" + x.get("exch", "NSE")) if x["board"] == "SME" else "Main"
        patcell = f'{fmt(x.get("ttm_pat"), dec=0)} vs {fmt(x.get("prior_peak_pat"), dec=0)}'
        rows += ("<tr>"
                 + td(i, "right", bg)
                 + td(f'{x["symbol"]}{warn}{t2t}', "left", bg, bold=True)
                 + td(board, "left", bg)
                 + td(fmt(x.get("mcap"), dec=0), "right", bg)
                 + td(fmt(x.get("pe"), dec=0), "right", bg)
                 + td(f'{x["zone_entry"]} ({x["days_in_zone"]}d)', "left", bg)
                 + td(fmt(x["pct_from_ath"]) + "%", "right", bg)
                 + td(fmt(x["stock_ret"], plus=True, dec=0) + "%", "right", bg, color="#0E7C3A", bold=True)
                 + td(fmt(a1, plus=True, dec=0), "right", bg)
                 + td(patcell, "right", bg)
                 + "</tr>")

    newline = (", ".join(x["symbol"] for x in new) if new else "none") if state.get("had_previous") \
        else "first run (baseline)"
    dropline = ", ".join(dropped) if dropped else ("none" if state.get("had_previous") else "&ndash;")
    newcards = ""
    if new:
        chips = "".join(f'<span style="display:inline-block;background-color:{GREENBG};'
                        f'color:#0E7C3A;font-weight:bold;padding:3px 10px;border-radius:10px;'
                        f'font-size:12px;font-family:Arial,sans-serif;margin:2px">{x["symbol"]}</span>'
                        for x in new)
        newcards = (f'<tr><td style="padding:4px 24px 10px 24px;font-family:Arial,sans-serif;'
                    f'font-size:13px;color:{INK}"><b>New this week:</b><br>{chips}</td></tr>')

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background-color:#f2f0ea">
<span style="display:none;max-height:0;overflow:hidden">{f['final']} stocks at lifetime highs with record profits &middot; {len(new)} new this week</span>
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#f2f0ea" style="background-color:#f2f0ea">
<tr><td align="center" style="padding:18px 8px">
<table width="740" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="background-color:#ffffff;border-radius:8px;overflow:hidden">
<tr><td bgcolor="{BLUE}" style="background-color:{BLUE};padding:16px 24px">
  <span style="color:#ffffff;font-family:Georgia,serif;font-size:22px;font-weight:bold">ATH Radar</span>
  <span style="color:#b9c6de;font-family:Arial,sans-serif;font-size:13px">&nbsp;&nbsp;{state['run_date']} &middot; prices as of {state['asof']}</span>
</td></tr>
<tr><td style="padding:16px 24px 6px 24px;font-family:Arial,sans-serif;font-size:14px;color:{INK}">
  <b style="font-size:17px">{f['final']} stocks</b> at all-time highs with record TTM profits, beating their benchmarks, Rs 1,000&ndash;20,000 Cr.<br>
  <span style="color:{SUB};font-size:12px">Funnel: {f['mainboard']:,} main + {f['sme']} SME &rarr; {f['ath_zone']} at ATH &rarr; {f['outperforming']} outperforming &rarr; {f['pat_at_ath']} record PAT &rarr; <b>{f['final']}</b>
  &nbsp;&middot;&nbsp; Dropped: {dropline}</span>
</td></tr>
{newcards}
<tr><td style="padding:6px 24px 4px 24px">
<table width="100%" cellpadding="0" cellspacing="0">
<tr>{th('#', 'right')}{th('Stock')}{th('Board')}{th('Mcap Cr', 'right')}{th('P/E', 'right')}{th('Entered zone')}{th('%ATH', 'right')}{th('TTM', 'right')}{th('&alpha; N500', 'right')}{th('PAT vs peak', 'right')}</tr>
{rows}
</table>
</td></tr>
<tr><td align="center" style="padding:14px 24px 4px 24px">
<table cellpadding="0" cellspacing="0"><tr>
<td bgcolor="{BLUE}" style="background-color:{BLUE};border-radius:6px">
<a href="{SITE}" style="display:inline-block;padding:9px 22px;color:#ffffff;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-decoration:none">Open the radar &rarr; sort &amp; filter</a>
</td></tr></table>
</td></tr>
<tr><td style="padding:10px 24px 16px 24px;font-family:Arial,sans-serif;font-size:11px;color:{SUB}">
Green = new since last run &middot; &#9888; = data caution (price mismatch or possible corporate action) &middot; T2T = trade-for-trade series &middot; alpha in percentage points &middot; SME prices unadjusted (history since Jul-2024).
Full 28-column workbook attached; sector alphas, 3M/6M momentum and the History tab are on the site.<br><br>
<span style="color:#999999">Factual screen for research &mdash; not investment advice.</span>
</td></tr>
</table>
</td></tr></table>
</body></html>"""


def main():
    try:
        state = json.load(open(os.path.join(BASE, "data", "state.json")))
    except Exception as e:
        print(f"ERROR: data/state.json unreadable ({e}) - likely a merge conflict "
              f"from overlapping runs. Skipping email; investigate the commit step.")
        sys.exit(1)
    html = build_html(state)
    if "--preview" in sys.argv:
        open(os.path.join(BASE, "digest_preview.html"), "w", encoding="utf-8").write(html)
        print("preview written")
        return
    addr = os.environ.get("GMAIL_ADDRESS", "")
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    to = os.environ.get("DIGEST_TO", "")
    if not (addr and pwd and to):
        print("email secrets not configured yet - skipping digest (add GMAIL_ADDRESS, "
              "GMAIL_APP_PASSWORD, DIGEST_TO in repo Settings > Secrets > Actions)")
        return
    new_n = sum(1 for x in state["finalists"] if x.get("is_new"))
    newbit = f" | {new_n} new" if state.get("had_previous") else ""
    msg = MIMEMultipart()
    msg["Subject"] = (f"ATH Radar | {state['funnel']['final']} stocks{newbit} "
                      f"| Rs 1k-20k Cr | {state['run_date']}")
    msg["From"] = addr
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    xlsx = os.path.join(BASE, "docs", "ATH_Tracker_latest.xlsx")
    if os.path.exists(xlsx):
        part = MIMEApplication(open(xlsx, "rb").read(),
                               _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        part.add_header("Content-Disposition", "attachment",
                        filename=f"ATH_Tracker_{state['run_date']}.xlsx")
        msg.attach(part)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(addr, pwd)
        s.sendmail(addr, [to], msg.as_string())
    print("digest sent to", to)


if __name__ == "__main__":
    main()
