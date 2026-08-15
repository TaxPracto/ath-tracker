# ATH Radar — project brain

Self-owned, Rs.0-cost weekly screen: NSE stocks at all-time-high price + all-time-high TTM PAT +
outperforming benchmarks, market cap Rs 1,000–20,000 Cr, sorted newest-entrant-first.
Runs Fridays 19:30 IST via GitHub Actions: SME store update -> screen -> build site + xlsx ->
deploy GitHub Pages -> email digest.

- Live site: https://taxpracto.github.io/ath-tracker/ (+ data.json, ATH_Tracker_latest.xlsx)
- Repo: https://github.com/TaxPracto/ath-tracker (account: TaxPracto)
- Email digest goes ONLY to ashwani.adac@gmail.com. NEVER add other recipients.
- Sister project: sme-lockin-tracker (Unlock Radar) — same deploy workflow, same secrets pattern.

## Non-negotiable security rules
1. Claude NEVER sees the Gmail app password. Secrets live only in GitHub Actions
   (GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DIGEST_TO) — same names/values as the Unlock Radar.
2. Every page/email keeps the "not investment advice" disclaimer.

## Locked product rules (do not re-litigate)
- ATH test: last close within 2% of all-time-high daily close. Mainboard = Yahoo split-adjusted
  full history. SME = NSE bhavcopy closes since 2024-07-01, UNadjusted (caveat on page).
- Outperformance: TTM return strictly > Nifty 500 AND Nifty Total Market; SME additionally
  > NIFTY SME EMERGE; mainboard with mapped sector index additionally > that sector.
  Listings <1y: matched window from listing date, flagged.
- PAT test: TTM PAT = sum of last 4 quarters (or last 2 half-years when screener shows
  half-yearly columns — auto-detected via median column gap >120d). Must be >= every visible
  annual Net Profit and >= every prior rolling window. Consolidated preferred, standalone fallback.
- Mcap band: 1,000 <= mcap <= 20,000 Cr (screener.in figure).
- Sort: zone_entry date desc (day the stock last crossed INTO the 2% zone), tie-break TTM return.
- Diff: state.json carries previous finalists; page/email show NEW and DROPPED. First run = baseline.

## Architecture (repo root)
| file | role |
|---|---|
| seed_sme.py | maintains data/sme_prices.json {"dates":[...], "symbols":{sym:{isin,px:[[date,close]]}}} from UDiFF bhavcopies (SM/ST series). Store is COMMITTED so weekly runs fetch only missing days. Per-day extracts in cache/bhav/ (gitignored) |
| screen.py | the pipeline: universe (EQUITY_L.csv EQ series ~2,400 + SME store ~450) -> Yahoo daily per mainboard stock -> ATH-zone gate -> outperformance gate (index snapshots) -> screener fundamentals gate (PAT ATH + mcap + sector test) -> sort -> diff -> data/state.json, docs/data.json -> build_page + build_xlsx |
| build_page.py | docs/index.html. Placeholder .replace() template (NO f-string braces pitfalls). Light theme: #F7F5F0, Fraunces/Instrument Sans/IBM Plex Mono |
| build_xlsx.py | docs/ATH_Tracker_latest.xlsx via openpyxl. VALUES not formulas |
| send_email.py | Gmail SMTP 465, env-only creds, attaches xlsx, --preview mode writes digest_preview.html |
| .github/workflows/weekly.yml | cron 0 14 * * 5 (=19:30 IST Fri) + workflow_dispatch + push on *.py. seed -> screen -> commit data/docs -> deploy-pages -> email |

## Data sources (all verified working from GitHub runners' IP space)
- archives.nseindia.com — EQUITY_L.csv, ind_niftytotalmarket_list.csv (industry column),
  ind_close_all_DDMMYYYY.csv (ALL index closes incl. Nifty Total Market / Healthcare Index /
  Consumer Durables / Chemicals / Oil & Gas / NIFTY SME EMERGE), UDiFF bhavcopies
  BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip. Walk back <=7 days for holidays.
- query1.finance.yahoo.com/v8/finance/chart/{SYM}.NS — mainboard daily history.
  CRITICAL: use period1=0&period2=now&interval=1d. NEVER range=max — it silently returns
  weekly/monthly bars for long histories and corrupts ATH (cost a full debugging round).
  Yahoo has ZERO coverage of NSE SME symbols (verified 0/8) — hence the bhavcopy store.
- www.screener.in/company/{SYM}/consolidated/ (fallback /company/{SYM}/) — quarterly + annual
  Net Profit rows, Market Cap, sector text from /company/compare/ link texts. Throttle 1.2–1.9s.
- www.nseindia.com/api/* is NOT used — blocked from cloud IPs. Archives host is the workaround.

## Sector mapping
NSE Total Market CSV Industry column (authoritative for its 750) -> SECTOR_BY_NSE_INDUSTRY;
everything else via SECTOR_KEYWORDS match on screener compare-link text; no match -> broad-only.
SMEs: broad + SME Emerge only (no sector test).

## Pitfalls (each cost a debugging round somewhere)
- Yahoo range=max trap (above). Yahoo 429s: backoff handled in yahoo_daily.
- NSE historicalOR API caps ~70 rows per call and nseindia.com blocks datacenter IPs — that is
  why indices come from ind_close_all snapshot files instead.
- SME_EQUITY_L.csv is a stale 5-row stub — SME universe must come from bhavcopy SM/ST series.
- Screener SME pages often report HALF-YEARLY — the win=2 detection must stay.
- EQUITY_L.csv headers have leading spaces (" SERIES") — strip keys.
- LibreOffice recalc unreliable in sandboxes; xlsx ships computed values, never bare formulas.
- ind_close_all names differ from API names: "Nifty Healthcare Index" (not NIFTY HEALTHCARE),
  "NIFTY SME EMERGE" is uppercase. Match case-insensitively (parser uppercases keys).
- First run after seeding: state.json has no previous list -> is_new=None, page says baseline.
- RACE (bit us 2026-08-15): two pushes minutes apart -> two queued runs; the second run's
  "git pull --rebase" hit the first run's weekly-data commit -> conflict markers written into
  data/state.json AND docs/index.html -> "|| true" swallowed it -> deploy shipped a corrupted
  page and email crashed on invalid JSON. Fix = commit step uses "git fetch origin main &&
  git reset -q origin/main" (mixed reset keeps fresh working tree) instead of pull --rebase.
  Process rule regardless: batch changes into ONE push; never two quick pushes.
- Yahoo revises closes after hours: borderline ATH names flicker between runs (PRICOLLTD -1.0%
  became -2.3% overnight on the same trading day's data). Not a bug — the 2% gate is hard.
- Screener consolidated pages can be DATA-LESS STUBS while standalone has real data (OBSCP):
  the fundamentals() price-sanity guard (page Current Price within ±35% of our close) must stay
  — it is what rejects stub/wrong pages and falls through to the good basis.

## Change workflow (same as Unlock Radar)
Work in sandbox outputs/ath-tracker/ -> ast.parse check -> run pipeline or targeted probe ->
deploy via github.com/TaxPracto/ath-tracker/upload/main browser upload (multiple files, ONE
commit -> one workflow run + one email). Pushing *.py triggers the FULL workflow including email.
Pushing only .md files is safe (path filter excludes them... NOTE: workflow push filter is
['*.py', '.github/workflows/*.yml'] so .md pushes do NOT trigger).

## v2 (2026-08-15, same day): UI + BSE SME + gate
- Universe now ALSO includes BSE SME (bhavcopy series M/MT, ~350 active). seed_sme.py fetches
  BOTH exchanges; store keys: NSE ticker or "BSE:<scripcode>"; rec carries exch/code/name/tckr.
  Dedupe by ISIN: mainboard > NSE Emerge > BSE SME (catches SME->mainboard migrations too).
  BSE SME benchmarked vs NIFTY SME EMERGE as proxy (documented on page). Screener lookups for
  BSE SME use the numeric scrip code as slug (screener.in/company/<code>/).
- Page v2: sortable headers (data-i/data-t, arrows, null-last), search, pills for board /
  entered-within / mcap bucket, sector select, NEW-only toggle, live count, reset. All JS is a
  plain string in build_page.py — NO backslashes, NO regex literals. jsdom smoke test MANDATORY
  before deploy (gate + filters + sort assertions; preset localStorage 'ath_ok'='1' because
  jsdom lacks crypto.subtle).
- 3M/6M return columns (series_metrics _ret helper) in page + xlsx.
- Passcode gate + GoatCounter analytics were built, DISCUSSED, and REMOVED at Ashwani's
  explicit choice (2026-08-15): privacy model = unlisted URL, no tracking. Do NOT re-add
  either without asking him. Real lock if ever wanted = Cloudflare Pages + Access (backlog).
- PROCESS RULE from the same discussion: for feature decisions beyond the literal ask
  (access control, analytics, anything user-facing that he didn't specify), DISCUSS OPTIONS
  FIRST, build after he picks. He said: "why do you build directly, discuss with me."

## v3 (2026-08-15, later same day): BE series, P/E, History tab, PAT-history guards
- Universe includes NSE BE series (trade-for-trade, ~250 names incl. E2E Networks) with t2t
  flag -> red T2T badge on page, "Main (T2T)" in xlsx. Chosen by Ashwani after E2E was found
  missing solely due to the EQ-only filter.
- P/E column (screener "Stock P/E", parsed alongside mcap) on page (sortable, after Mkt Cap),
  in xlsx and history. Column indexes on index.html shifted — jsdom test tracks them.
- History: data/history.json (one entry per run date, idempotent - latest run of a day wins,
  KEEP-list of compact fields) + docs/history.html via build_history.py: staying-power table,
  weekly archive (details/summary, NEW badges), and a what-happened-after section (+4w/+12w
  from appearance close) that AUTO-ACTIVATES once appearances are 28+ days old. Prices for
  past names read from cache/px + SME store during the run. Nav links both ways.
- PAT-history guards (the E2E lesson, cost a near-miss): (a) half-yearly detection now
  requires EVERY gap >120d, not the median — a sparse quarterly history (E2E consolidated had
  3 quarters) must not be misread as half-yearly; (b) a basis with prior_peak None or with
  <2 annual years AND <3 rolling windows is rejected (too little history to claim an all-time
  high) and falls through to the other basis. E2E on full standalone history: TTM 31 vs peak
  48 -> correctly excluded. If its recovery crosses the old peak it enters automatically.

## v4 (2026-08-15): data-reliability guards (Ashwani: "make the data more reliable")
- PRE-FLIGHT GATE in screen.py: run DIES before touching docs/state on any of — universe
  counts too small, required indexes missing, snapshot stale >4d, >15% price-history failures,
  screener error rate >30%, finalist count outside 1..150, >2 audit mismatches. Failed gate =
  failed workflow job = site stays on last good build; GitHub emails the failure notification.
- SECOND-SOURCE AUDIT: every NSE finalist's close checked vs the exchange bhavcopy (2% tol);
  mismatch -> audit_flag -> warning symbol on page + email.
- CORP-ACTION FLAG: SME zone candidates with any historical day move <=-33% or >=+50% get
  corp_flag ("possible split/bonus, ATH base suspect") -> warning symbol on page + email.
- Flags persist into history.json (KEEP list).

## Backlog (discussed, not built)
SME corporate-action adjustment (splits create false ATH-misses); BE-series mainboard names;
dividend-adjusted ATH option; history page of past weekly lists (weekly state snapshots ->
staying-power + what-happened-after stats, radar-backtest style); per-stock modal (PAT
trajectory, liquidity/avg turnover); dropped-log page; ATH_PASSCODE env into workflow (needs
workflow-file edit); Cloudflare Access real lock; wire into TheWrap Stage 2 Sunday scan.

_Last updated: 2026-08-15 (v2: filters/sort/search UI, BSE SME universe, passcode gate, GoatCounter, 3M/6M columns)_
