# Deploy for free: GitHub Actions + Neon + Vercel

```
 GitHub Actions (free)             Neon Postgres (free)              Vercel (free Hobby)
 ┌──────────────────────┐  writes  ┌────────────────────┐  reads    ┌─────────────────────────┐
 │ engine.yml, daily     │────────►│ companies,          │◄─────────│ api/index.py dashboard   │
 │ crawl + agents        │          │ observations, runs, │          │ password-protected       │
 │ (Playwright, 20-40 m) │◄─────────│ agent_runs ...      │          │ "Find leads now" ────────┼──► workflow_dispatch
 └──────────────────────┘ dispatch └────────────────────┘          └─────────────────────────┘
        ▲ free model APIs: Groq / Cerebras / Gemini / OpenRouter (keys as GitHub secrets)
```

Why split it: Vercel's free functions stop after seconds, too short for a 20-minute browser crawl. GitHub Actions gives private repos 2,000 free minutes a month, and a daily run uses about 30. Neon's free Postgres is the shared memory both sides use.

## 1. Database: Neon (free)
1. Create a free project at neon.tech, or in Vercel: Storage → Create → Neon (it adds `DATABASE_URL` to the Vercel project automatically).
2. Copy the **pooled** connection string (`postgresql://...-pooler...neon.tech/...?sslmode=require`).

## 2. Engine: GitHub Actions
Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Required | Value |
|---|---|---|
| `DATABASE_URL` | yes | Neon connection string |
| `GROQ_API_KEY` / `CEREBRAS_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | at least one for agents | free keys from console.groq.com, cloud.cerebras.ai, aistudio.google.com, openrouter.ai |
| `SERPER_API_KEY` | optional | 2,500 free Google searches (otherwise DuckDuckGo) |

Then go to Actions → **engine** → Run workflow. It also runs daily at 01:00 UTC (06:30 IST). Each run's Excel file is kept as an artifact for 14 days.

## 3. Dashboard: Vercel
1. vercel.com → Add New → Project → import `khan09faiz/metalscout`. Framework: **Other**. Leave the build settings empty.
2. Environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | same Neon string (auto-added if you used the Vercel → Neon integration) |
| `DASHBOARD_PASSWORD` | any password; the browser asks for it (any username) |
| `GITHUB_REPO` | `khan09faiz/metalscout` |
| `GITHUB_DISPATCH_TOKEN` | fine-grained token for this repo only, permission **Actions: Read and write** |

3. Deploy. Open the URL, log in, and click **Find leads now**. That starts the GitHub Actions run, and the dashboard shows "running" until it finishes.

## Costs
| Piece | Free allowance | MetalScout use |
|---|---|---|
| GitHub Actions (private repo) | 2,000 min/month | ~30 min/day ≈ 900 min/month |
| Neon | 0.5 GB storage, auto-suspend | ~1–3 MB/day of observations + page digests |
| Vercel Hobby | personal, non-commercial use; generous function limits | a few requests per visit |
| Models | free tiers (see docs/AGENTS.md) | ≤150 calls/run (`agents.max_calls_per_run`) |

Vercel's Hobby plan terms are for personal, non-commercial use. If this becomes a business tool, check whether you need Pro, or self-host the dashboard (`python -m metalscout serve`) instead.

## Local mode still works
Without `DATABASE_URL` everything uses `data/metalscout.db` (SQLite). `python -m metalscout serve` runs the dashboard and the daily heartbeat on your PC, and Ollama gives free local models.
