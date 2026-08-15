#!/usr/bin/env python3
"""Friday digest email. Credentials ONLY from env (GitHub Actions secrets):
GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DIGEST_TO. Never hardcode.
Usage: python send_email.py [--preview]
"""
import json, os, smtplib, ssl, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://taxpracto.github.io/ath-tracker/"


def fmt(x, plus=False, dec=1):
    if x is None:
        return "&ndash;"
    return (f"{x:+.{dec}f}" if plus else f"{x:,.{dec}f}")


def build_html(state):
    f = state["funnel"]
    fins = state["finalists"]
    new = [x for x in fins if x.get("is_new")]
    dropped = state.get("dropped_since_last") or []
    rows = ""
    for i, x in enumerate(fins, 1):
        bench2 = x.get("sme_ret") if x["board"] == "SME" else x.get("sector_ret")
        a1 = None if x.get("n500_ret") is None else x["stock_ret"] - x["n500_ret"]
        a2 = None if bench2 is None else x["stock_ret"] - bench2
        bg = ' style="background:#e2efda"' if x.get("is_new") else ""
        warn = " &#9888;" if (x.get("audit_flag") or x.get("corp_flag")) else ""
        rows += (f'<tr{bg}><td>{i}</td><td><b>{x["symbol"]}{warn}</b></td>'
                 f'<td>{x["name"][:32]}</td><td>{x["board"]}</td>'
                 f'<td align="right">{fmt(x.get("mcap"), dec=0)}</td>'
                 f'<td>{x["zone_entry"]} ({x["days_in_zone"]}d)</td>'
                 f'<td align="right">{fmt(x["pct_from_ath"])}%</td>'
                 f'<td align="right">{fmt(x["stock_ret"], plus=True)}%</td>'
                 f'<td align="right">{fmt(a1, plus=True, dec=0)}</td>'
                 f'<td align="right">{fmt(a2, plus=True, dec=0)}</td>'
                 f'<td align="right">{fmt(x.get("ttm_pat"), dec=0)} vs {fmt(x.get("prior_peak_pat"), dec=0)}</td></tr>')
    newline = (", ".join(x["symbol"] for x in new) if new else "none") if state.get("had_previous") \
        else "first run (baseline)"
    dropline = ", ".join(dropped) if dropped else ("none" if state.get("had_previous") else "&ndash;")
    return f"""<div style="font-family:Arial,sans-serif;font-size:13px;color:#222;max-width:940px">
<h2 style="color:#1F3864;margin-bottom:4px">ATH Radar &mdash; {state['run_date']}</h2>
<p style="margin:4px 0"><b>{f['final']} stocks</b> at lifetime highs with record TTM profits, beating their benchmarks, Rs 1,000&ndash;20,000 Cr.
Funnel: {f['mainboard']:,} main + {f['sme']} SME &rarr; {f['ath_zone']} at ATH &rarr; {f['outperforming']} outperforming &rarr; {f['pat_at_ath']} record PAT &rarr; <b>{f['final']}</b>.</p>
<p style="margin:4px 0"><b>New this week:</b> {newline} &nbsp;|&nbsp; <b>Dropped:</b> {dropline}</p>
<p style="margin:4px 0">Live page: <a href="{SITE}">{SITE}</a></p>
<table border="0" cellpadding="5" cellspacing="0" style="border-collapse:collapse;font-size:12px;width:100%">
<tr style="background:#1F3864;color:#fff;text-align:left"><th>#</th><th>Symbol</th><th>Company</th><th>Board</th>
<th align="right">Mcap Cr</th><th>Entered zone</th><th align="right">%fromATH</th><th align="right">TTM</th>
<th align="right">&alpha; N500</th><th align="right">&alpha; sector/SME</th><th align="right">TTM PAT vs peak</th></tr>
{rows if rows else '<tr><td colspan="11">No stock passes every filter this week.</td></tr>'}
</table>
<p style="font-size:11px;color:#555">Green = new since last run. &#9888; = data caution (price mismatch vs exchange file, or possible corporate action) &mdash; verify before trusting that row. Alpha in percentage points. SME prices unadjusted, history since Jul-2024. Full workbook attached; methodology on the site.</p>
<p style="font-size:11px;color:#888">Factual screen for research &mdash; not investment advice.</p></div>"""


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
    msg = MIMEMultipart()
    msg["Subject"] = (f"ATH Radar | {state['funnel']['final']} stocks at lifetime highs "
                      f"| Rs 1k-20k Cr | {state['run_date']}")
    msg["From"] = addr
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    xlsx = os.path.join(BASE, "docs", "ATH_Tracker_latest.xlsx")
    if os.path.exists(xlsx):
        part = MIMEApplication(open(xlsx, "rb").read(), _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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
