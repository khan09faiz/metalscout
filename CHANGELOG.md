# Changelog

## 1.2.0 (unreleased)
### Security
- Engine workflow: `stages` and the trigger reach bash through `env:` only and are validated against `^[a-z,-]+$`; the dashboard and the `run --stages` CLI reject unknown stage names (400 / exit 2)
- Local dashboard: `Host` allowlist (DNS rebinding), POSTs must be JSON, cross-origin `Origin` refused (CSRF), all with 403; new `web.allowed_hosts` for LAN names
- SSRF: in-browser requests to non-public hosts are blocked, a navigation that ends on a private host is discarded and stops the crawl, robots.txt is never fetched from (or redirected to) a private host; DNS checks cached per host
- 500 responses no longer echo exception text (it is logged instead)
- Dashboard login: 10 failed attempts per IP per 10 minutes, then 429
- GitHub Actions pinned to commit SHAs
### Agents
- A Scout call that fails no longer marks the buyer signal as checked; it is retried next run (`agent_retry_later`)
- `agent_attempts` on companies and buyer signals (schema v3): rows that keep failing go to the back of the queue and are skipped after `agents.max_attempts` (default 3), so they can't use up the call budget
- Grounding gate checks that a quote *supports* the fact (`ground.supports`: metal regex, volume number, person name, product word), not just that it exists; failures count as rejected
- Writer drafts with numbers that aren't in the given facts are stored with `unverified numbers: …` and shown with a warning in the lead drawer
- Prompts state that page text is untrusted data and that instructions in it must be ignored; a test proves model output never becomes a crawl URL or a contact
### Performance and storage
- `leads.build()`: two queries (companies + one join on `run_id = last_profile_run`) instead of one query per company; 2,000 companies × 20 observations went from 2,001 queries to 2. `/api/status` counts come from `leads.summary()` over the same two queries, and company rows no longer load page digests
- `pipeline.keep_profile_runs` (default 3): older profile runs' observations, agent facts included, are deleted after each profile
- Postgres `connect_timeout=10`; DEPLOY.md says to use Neon's pooled (`-pooler`) string on Vercel
- New companies are crawled from their homepage; the search-hit or pasted URL is kept in `source`
### Robustness
- Runs beat a heartbeat (`runs.heartbeat`, schema v4); a `running` run silent for 20 minutes no longer blocks new runs or shows as running. New `mark-failed` command, run by `engine.yml` when the job fails or is cancelled
- Run status: `ok` = no stage failed, `partial` = some, `failed` = all. Per-site / per-signal / per-call problems are capped `warnings` in stats (shown on the Runs tab), not `errors`. A discover stage in which every search failed counts as a failed stage
- `schedule show` quotes paths in the cron line; the fit score gives a "phone" reason; a do-not-contact domain also blocks emails at that domain or its subdomains
### Packaging
- `metalscout.agents` is now in non-editable installs (`packages.find`), and the agent prompts moved to `metalscout/prompts/agents/` as package data. `prompts/master_prompt.md` stays where it was

## 1.1.0 (2026-11-26)
- **Agent crew** (optional, free models): a rules-based orchestrator routes each lead to the Sorter (small model), Analyst (large), Writer (large, Tier A/B only) and Scout (buyer-signal pages)
- **Model router** over free OpenAI-compatible providers: Groq, Cerebras, Gemini, OpenRouter `openrouter/free`, local Ollama. Models are discovered at run time, with fallback on rate limits and a per-run call budget; tiny models are never used for the large tier
- **Grounding gate:** every agent fact must quote the crawled page or it's rejected; rejections are counted per agent and model
- Page digests stored per company; agent facts become `AGENT_*` observations that feed the fit score
- **Free cloud deploy:** Postgres support (Neon) alongside SQLite; GitHub Actions daily engine (`engine.yml`); Vercel dashboard (`api/index.py`) with password and "Find leads now" dispatching the Actions run
- Dashboard: Agents tab (roster, providers, per-model stats), AI analysis in the lead drawer with a copyable email draft, Scout readings on buyer signals
- Split dependencies: `requirements.txt` (web + DB) and `requirements-engine.txt` (crawler); `pip install -e .[engine]`
- Tests: 29 to 31, including a fake-LLM crew test and real-Postgres tests

## 1.0.0 (2026-11-25)
- First release: deterministic daily pipeline (discover, profile, signals, export)
- Playwright site surfer with priority links, pagination, lazy-load, robots.txt, per-site timeout, SSRF guard
- Extractors: emails (incl. obfuscated and Cloudflare), Indian phones, GSTIN, CIN, Udyam, IEC, metals, quantities (equipment tonnage ignored), certifications, manufacturer/trader/intent
- Fit score with reasons; tiers; trader cap; do-not-contact
- Dashboard (stdlib server, no build step); Excel with 5 tabs; CSV; optional Google Sheets
- Windows Task Scheduler install, in-app heartbeat, run lock and history
- 22 tests, including a real-browser end-to-end crawl of a local fixture site
