# Architecture

## Principles
1. **Deterministic, no model.** Search, crawl, regex and a scoring formula. It runs forever at zero marginal cost.
2. **The database is the asset.** Facts are stored as *observations* `(company, signal, value, source_url, evidence, run_id, time)`. Leads are a *view* over them.
3. **Stages chain through queries, not hand-offs.** PROFILE asks the DB "who is new or stale?" rather than taking a list from DISCOVER. A crashed run resumes by itself; re-profiling builds history.
4. **A failure is an observation.** An unreachable site becomes `status=failed` plus an `UNREACHABLE` observation. A search ban becomes a run error. Nothing fails silently.
5. **Never invent.** Only values printed on a page are stored. Empty beats wrong.

## Layout
```
metalscout/
├── __main__.py     CLI (init, run, serve, add, import, export, status, schedule)
├── config.py       YAML over defaults
├── db.py           SQLite schema + queries (companies, observations, buyer_signals, runs, kv)
├── net.py          domain helpers, public-host SSRF guard, robots.txt cache
├── sources.py      DISCOVER: query space, daily cursor, search providers, hit routing, CSV import
├── browser.py      Playwright surfer: best-first same-site crawl, pagination, scroll, timeout
├── extract.py      pure extractors: emails, phones, GSTIN/CIN/Udyam/IEC, quantities, metals, classify
├── profile.py      pages → observations
├── fit.py          observations → score, tier, reasons (computed on read)
├── leads.py        read model for UI and exports
├── engine.py       daily run: lock → stages → export → run record; logging
├── scheduler.py    in-app heartbeat + Windows Task Scheduler / cron
├── export.py       xlsx (5 tabs), csv, Google Sheets
├── server.py       stdlib HTTP JSON API + static files
└── web/            index.html, app.js, app.css (no build step)
```

## Run lifecycle
```
            ┌──────────── engine.run(trigger) ────────────┐
 Lock ─► start_run ─► DISCOVER ─► PROFILE ─► SIGNALS ─► EXPORT ─► finish_run(ok|partial|failed) ─► unlock
                       │            │           │          │
                 kv.query_cursor  companies   buyer_     exports/leads_YYYY-MM-DD.xlsx
                 +40 queries      status=new  signals    leads_latest.xlsx/.csv, gsheet
                 → companies      or stale    opened=0
                 → buyer_signals  → observations
```
Each stage is wrapped in its own try/except, so a failed stage doesn't stop the others.

## Data model
| Table | Key columns | Notes |
|---|---|---|
| `companies` | domain (unique), website, name, status, stage, last_profile_run | status: new/profiled/failed/challenged; stage: lead/contacted/replied/quoted/won/lost/not_fit |
| `observations` | company_id, run_id, signal, value, num, source_url, evidence | append-only; latest run per company is the current view |
| `buyer_signals` | url (unique), kind, metals, quantity, emails, phones, intent, restricted, opened | marketplace/tender/social/csv |
| `runs` | id, trigger, started, finished, status, stats(json), errors(json) | powers the Runs tab and "ran today?" |
| `kv` | query_cursor, query_total, schema_version | |

## Discovery query space
`templates × metals × industries × clusters`, deduplicated, in a **fixed order**. Each run takes the next `queries_per_run` from a cursor stored in `kv`, then wraps around. With the default config the space is about 3 × 8 × 12 × 14 ≈ 4,000 queries, about 100 days of new ground at 40 a day.

Hits are routed as follows:
- **company**: anything not listed below. Added to `companies`.
- **signal**: marketplace, tender or social hosts. Added to `buyer_signals`. Restricted hosts are marked `restricted=1` and never opened.
- **skip**: directories, encyclopedias, job boards and ad redirects.

## Crawler
- One Chromium per stage, `concurrency` pages in parallel across sites.
- Same registered domain only. Images, fonts and media are blocked for speed.
- Priority: contact 100 › about 80 › products 60 › infrastructure 55 › vendor/tender 50 › other links from the homepage 10. Each page is scrolled four times for lazy content.
- "Next" pagination is followed up to three times.
- Each URL is checked against robots.txt. There is a 1–2.5 s delay between pages, and each site has a 150 s overall budget (it returns what it has read so far).
- Private, loopback and metadata IPs are rejected (`net.is_public`).

## Scoring
`fit.score()` runs on every read, so editing weights in YAML re-ranks instantly. Traders are capped at 15. A do-not-contact match scores 0 and gets tier X.

## Scheduling
- **OS level** (`schedule install`): Windows Task Scheduler with `-StartWhenAvailable` (catches up after sleep or shutdown) and `-MultipleInstances IgnoreNew`. On Linux/macOS, `schedule show` prints a cron line.
- **App level** (`serve`): a heartbeat thread checks every 60 s and starts a run once the daily time has passed if none has run today.
- The engine lock (`data/engine.lock`, stale after 6 h) makes both safe to enable together.

## Security
- The dashboard binds to 127.0.0.1 and has no auth, so don't expose it. Static file serving is confined to `web/`.
- All page-derived text is escaped in the UI, and only http(s) links are rendered.
- Page content is treated as data. It is never executed or followed as instructions.
