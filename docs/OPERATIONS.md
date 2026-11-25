# Operations

## Install (Windows)
```powershell
python -m venv .venv ; .venv\Scripts\activate
pip install -e .            # or: pip install -r requirements.txt
python -m playwright install chromium
python -m metalscout init
```
Optional: `setx SERPER_API_KEY <key>` for Google results via Serper (2,500 free queries; about $1 per 1,000 after that).

## Daily schedule
| Option | Command | Runs when |
|---|---|---|
| **Windows Task Scheduler** (recommended) | `python -m metalscout schedule install` | Daily at `schedule.daily_at`; runs at next wake if missed; dashboard not needed |
| In-app heartbeat | `python -m metalscout serve` | While the dashboard process is open |
| Linux/macOS | `python -m metalscout schedule show` → paste into `crontab -e` | Daily |

Remove: `python -m metalscout schedule remove`. Check: Task Scheduler → *MetalScout Daily* → History.

A typical daily run: 40 searches (about 3 min) + 60 sites × about 40 s / 3 parallel (about 15 min) + signals + export. **About 20–30 minutes.**

## Files
| Path | What |
|---|---|
| `metalscout.yaml` | your config (gitignored) |
| `data/metalscout.db` | everything (SQLite, WAL). **Back this file up**; it is the asset |
| `data/engine.lock` | present while a run is active; stale after 6 h |
| `logs/metalscout.log` | rotating 2 MB × 5 |
| `exports/` | `leads_YYYY-MM-DD.xlsx` (kept 30 days), `leads_latest.xlsx`, `leads_latest.csv` |

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Run status `partial`, errors "search failed 3x" | DuckDuckGo throttling. Lower `queries_per_run`, or set `SERPER_API_KEY` |
| "another run is in progress" | A run is active, or one crashed. Delete `data/engine.lock` if no python process is running |
| Many `failed` companies | Sites down or slow. Raise `site_timeout_s`; they are retried after `reprofile_after_days` |
| `challenged` companies | Cloudflare or similar bot wall. Not bypassed by design; open the site manually |
| No leads after a run | Check the Runs tab: `queries` > 0? `new_companies` > 0? Then check the log |
| Playwright error "Executable doesn't exist" | `python -m playwright install chromium` |
| Port 8000 busy | `python -m metalscout serve --port 8010` |

## Tuning
- More leads per day: raise `queries_per_run` and `profile_per_run` (and use Serper).
- Fewer false manufacturers: raise `fit.tier_a`, or add trader words in `extract.TRADER`.
- New region or industry: edit `search.clusters` / `search.industries`. The cursor wraps, and new combinations are searched as it goes.
