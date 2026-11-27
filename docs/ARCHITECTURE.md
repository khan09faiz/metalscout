# Architecture

## Principles
1. **Deterministic core, optional agents.** Search, crawl, regex and a scoring formula run with no model and at zero marginal cost. The agent crew (docs/AGENTS.md) is an extra stage on free models; every agent fact must quote the crawled page.
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
├── agents/         optional crew: llm.py (free-model router), crew.py (orchestrator + agents), ground.py (quote check)
├── prompts/agents/ the agents' Markdown prompts (package data, so they ship in the wheel)
├── scheduler.py    in-app heartbeat + Windows Task Scheduler / cron
├── export.py       xlsx (5 tabs), csv, Google Sheets
├── server.py       stdlib HTTP JSON API + static files
└── web/            index.html, app.js, app.css (no build step)
```

## Run lifecycle
```
            ┌──────────── engine.run(trigger) ────────────┐
 Lock ─► start_run ─► DISCOVER ─► PROFILE ─► SIGNALS ─► AGENTS ─► EXPORT ─► finish_run(ok|partial|failed) ─► unlock
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
| `companies` | domain (unique), website (the homepage, `scheme://host/`), name, status, stage, found_via (the query), source (`search:<hit URL>` / `manual:<URL>` / `csv`), last_profile_run, agents_run, agent_attempts | status: new/profiled/failed/challenged; stage: lead/contacted/replied/quoted/won/lost/not_fit |
| `observations` | company_id, run_id, signal, value, num, source_url, evidence | append-only per run; latest run per company is the current view. After each profile, runs older than the company's last `pipeline.keep_profile_runs` (default 3) are deleted, their `AGENT_*` facts included |
| `buyer_signals` | url (unique), kind, metals, quantity, emails, phones, intent, restricted, opened, agent_checked, agent_attempts | marketplace/tender/social/csv |
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
- Starts at the homepage (`scheme://host/`): discovery and "Add sites" store that rather than the deep page a search hit or a paste pointed at.
- Same registered domain only. Images, fonts and media are blocked for speed.
- Priority: contact 100 › about 80 › products 60 › infrastructure 55 › vendor/tender 50 › other links from the homepage 10. Each page is scrolled four times for lazy content.
- "Next" pagination is followed up to three times.
- Each URL is checked against robots.txt. There is a 1–2.5 s delay between pages, and each site has a 150 s overall budget (it returns what it has read so far).
- Private, loopback and metadata IPs are rejected (`net.is_public`).

## Read model
`leads.build()` reads the shown companies and their latest-profile observations in **two queries**: one for the companies, one join `observations ⋈ companies ON company_id AND run_id = last_profile_run` (served by `ix_obs`), grouped in Python. `leads.summary()` uses the same two queries for the dashboard's counts, so `/api/status` (polled every 5 s) never builds every lead.

## Scoring
`fit.score()` runs on every read, so editing weights in YAML re-ranks instantly. Traders are capped at 15. A do-not-contact match scores 0 and gets tier X.

## Scheduling
- **OS level** (`schedule install`): Windows Task Scheduler with `-StartWhenAvailable` (catches up after sleep or shutdown) and `-MultipleInstances IgnoreNew`. On Linux/macOS, `schedule show` prints a cron line.
- **App level** (`serve`): a heartbeat thread checks every 60 s and starts a run once the daily time has passed if none has run today.
- The engine lock (`data/engine.lock`, stale after 6 h) makes both safe to enable together.

## Storage backends
`db.DB` uses SQLite (`data/metalscout.db`) unless `DATABASE_URL` is a Postgres URL (free Neon in the cloud). Postgres runs in autocommit, so reads never hold locks. Schema DDL runs only when `kv.schema_version` is older; `MIGRATIONS` add columns idempotently.

## Deployment
Local: `serve` + Task Scheduler. Cloud (docs/DEPLOY.md): GitHub Actions `engine.yml` runs the engine against Neon; Vercel serves `api/index.py` (the same handler) with `DASHBOARD_PASSWORD`, and "Find leads now" calls the GitHub `workflow_dispatch` API.

## Security
- The local dashboard binds to 127.0.0.1. It answers only requests whose `Host` is `localhost`, `127.0.0.1` or `web.host` (with the port), plus any names in `web.allowed_hosts`; this blocks DNS-rebinding pages. On Vercel the platform routes by host, so this check is skipped there.
- CSRF: every POST must be `Content-Type: application/json`, and a request carrying an `Origin` header must come from the dashboard's own host. Anything else gets 403.
- `DASHBOARD_PASSWORD` turns on HTTP Basic auth (required on Vercel). Ten failed logins per client IP in 10 minutes give 429 until the window passes, even for the right password. The counter is in memory, per process.
- Run requests accept only the stage names in `engine.STAGES` (server 400, CLI exit 2). The Actions workflow passes inputs through `env:` and validates them in bash; it never interpolates `${{ }}` into a script. Actions are pinned to commit SHAs.
- A 500 returns `{"error": "internal error"}`; the exception is written to the log, never to the client.
- SSRF: `net.host_is_public()` (cached per host) rejects private, loopback, link-local, CGNAT, metadata and unspecified addresses. It is applied to the seed URL, to robots.txt (each redirect hop is checked *before* it is requested), to every in-browser request through a Playwright route handler, and to `page.url` after every navigation: a redirect that lands on a private host is discarded and the site's crawl stops. `crawl.allow_private_hosts: true` turns all of this off (tests only).
  - Residual: Playwright does not run route handlers on redirect hops, so a site that redirects into a private address still causes one blind GET to it (the response is thrown away). Chromium also resolves DNS separately from our check. For hard isolation, run the engine where it has no route to internal networks (GitHub-hosted runners have none).
- Static file serving is confined to `web/`. All page-derived text is escaped in the UI, and only http(s) links are rendered.
- Page content is treated as data. It is never executed or followed as instructions.
