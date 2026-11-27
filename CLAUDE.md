# Notes for AI assistants working on this repo

- Python 3.10+, no framework. Entry point `python -m metalscout`. Tests: `python -m pytest -q` (needs `pip install -e .[engine,dev]` and `playwright install chromium`; Postgres tests use `pgserver` or `TEST_DATABASE_URL`, and skip if neither exists).
- **The deterministic core must work with no model at all.** Discover → profile → score → export use no LLM. The agent crew (`metalscout/agents/`) is an optional stage that is skipped when no provider is configured. Never make the core depend on it.
- **Free only.** Models come from free tiers or local Ollama through `agents/llm.py`. Don't add paid-only providers to the default order.
- Every stored fact is an observation with `source_url`. Contacts (emails, phones) come **only** from regex extractors on printed page text, never from a model.
- Every agent fact must pass `agents/ground.locate()` (its quote exists in the crawled digest) before it's stored. Keep that gate in front of any new agent output.
- Don't add CAPTCHA solving, login automation, or crawling of hosts in `domains.restricted`.
- Stages chain through DB queries (`companies_needing_profile`, `signals_to_open`, `companies_for_agents`, `signals_for_agents`), not in-memory lists.
- SQL must run on both SQLite and Postgres. Use `?` params and `INSERT OR IGNORE` / `INSERT OR REPLACE INTO kv` only; `db._pg_sql` translates those. No SQLite-only functions.
- Scoring lives only in `fit.py` and is computed on read; don't persist scores.
- The web dashboard must import without Playwright, selectolax or ddgs (Vercel installs `requirements.txt` only). Import `browser` lazily.
- UI is plain HTML/JS in `metalscout/web/`. Escape every page-derived string (`esc`, `safeUrl`).
- Agent prompts are Markdown in `metalscout/prompts/agents/` (shipped as package data).
- Docs to update when behaviour changes: README, docs/ARCHITECTURE.md, docs/SIGNALS.md, docs/AGENTS.md, docs/DEPLOY.md, CHANGELOG.md.
