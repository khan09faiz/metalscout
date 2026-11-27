# MetalScout

**Find manufacturers and end users in India that buy raw metal, not traders.** It runs every day by itself. The core needs no AI or API keys, and an optional crew of agents on **free** models adds deeper analysis and email drafts.
Every email, phone and quantity it reports carries the URL of the page it was read from.

```
search the web ─► open each company site in a real browser ─► extract facts with sources ─► score ─► dashboard + Excel
   (rotating        (contact / about / products / vendor pages,     (emails, phones, GSTIN, CIN,   (manufacturer?   (daily, dated,
    queries)         pagination, lazy-loading, robots.txt)           metals, MT/month, intent)      metal? qty?)      Google Sheet)
```

**Agents (optional, free):** a rules-based orchestrator sends each lead to a Sorter, Analyst, Writer and Scout, each on the right-sized free model (Groq, Cerebras, Gemini, OpenRouter free, or local Ollama). Every fact an agent reports must quote the company's own page, or it's rejected. See [docs/AGENTS.md](docs/AGENTS.md).

**Run it in the cloud for free:** GitHub Actions does the daily crawl, Neon Postgres stores the data, and Vercel hosts the password-protected dashboard. See [docs/DEPLOY.md](docs/DEPLOY.md).

## Quick start (Windows)

```powershell
git clone https://github.com/<you>/metalscout ; cd metalscout
python -m venv .venv ; .venv\Scripts\activate
pip install -e .[engine]
python -m playwright install chromium
python -m metalscout init            # creates metalscout.yaml: set your metals, industries, cities
python -m metalscout serve           # dashboard at http://localhost:8000  ->  click "Find leads now"
```

Run it daily with no window open:

```powershell
python -m metalscout schedule install   # Windows Task Scheduler, daily at schedule.daily_at, catches up if the PC was off
```

Or just double-click `scripts\start_dashboard.bat`.

## What you get

| Output | Where |
|---|---|
| Dashboard: leads by tier, new today, buyer signals, run history, log, pipeline stage and notes per lead | `http://localhost:8000` |
| Excel: Leads / All companies / Buyer signals / Runs / README tabs, a source column next to every contact | `exports/leads_YYYY-MM-DD.xlsx`, `exports/leads_latest.xlsx` |
| CSV for mail tools | `exports/leads_latest.csv` |
| Google Sheet mirror (optional) | `export.gsheet_id` in config |

## Commands

```
python -m metalscout run [--stages discover,profile,signals,agents,export] [--profile-limit N]
python -m metalscout serve [--port 8000] [--no-scheduler]
python -m metalscout add https://somecompany.in ...      # queue your own sites
python -m metalscout import tenders.csv                  # GeM/CPPP/trade-show exports (columns: website and/or url, title)
python -m metalscout export [--out file.xlsx]
python -m metalscout status
python -m metalscout mark-failed                         # close a run left 'running' by a crash
python -m metalscout schedule install|remove|show
```

## How it decides who is a lead

Scored 0–100 from the facts on the company's own site (weights are in `metalscout.yaml`):

| Signal | Points |
|---|---|
| Manufacturer / end user (plant, capacity, foundry, forging, ISO/IATF, CNC…) | 30 |
| Mentions a metal you sell | 20 |
| States a volume (`120 MT per month`, `2,400 TPA`). Press and hammer tonnage is ignored | 15 |
| Email printed on site (own domain 15, other 10) | 15 |
| Phone | 10 |
| GSTIN / CIN / Udyam / IEC printed | 5 |
| Vendor-registration / RFQ / tender wording | 5 |

Traders, dealers and stockists are capped at 15 points and left out of the Leads tab. Tier **A ≥ 65**, **B ≥ 40**.

## Documentation

| Doc | What's in it |
|---|---|
| [docs/PROMPT.md](docs/PROMPT.md) | The original brief and the prompts this project was built from |
| [docs/PRD.md](docs/PRD.md) | Product requirements, users, scope, success metrics |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modules, data model, pipeline, design decisions |
| [docs/DESIGN.md](docs/DESIGN.md) | Dashboard and spreadsheet design |
| [docs/AGENTS.md](docs/AGENTS.md) | The agent crew, free model providers, grounding gate |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Free cloud setup: GitHub Actions + Neon + Vercel |
| [docs/SIGNALS.md](docs/SIGNALS.md) | Every observation the profiler records |
| [docs/SOURCES.md](docs/SOURCES.md) | Where Indian metal buyers can be found, and what's automated vs manual |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Daily scheduling, logs, backups, troubleshooting |
| [docs/COMPLIANCE.md](docs/COMPLIANCE.md) | Scraping and outreach rules (DPDP, TRAI, ToS) |
| [docs/REFERENCE_SELLBIRD.md](docs/REFERENCE_SELLBIRD.md) | What was learned from Sellbird (formerly Harvey), clean-room notes |
| [docs/research/](docs/research/) | Source research notes with citations |
| [prompts/master_prompt.md](prompts/master_prompt.md) | The research prompt for running this with an AI assistant instead |

## Limits

- No CAPTCHA, login or paywall bypass. Government portals such as GeM and CPPP: export a list and `import` it.
- IndiaMART, LinkedIn, Facebook, X, JustDial and Alibaba are never opened by the crawler. Their terms forbid it, so only the search snippet is kept.
- DuckDuckGo search is free but rate-limited. Set `SERPER_API_KEY` (2,500 free Google queries) for more and better results.
- Scores are heuristics. Read a Tier A lead before you contact it.
