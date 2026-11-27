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
