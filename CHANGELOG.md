# Changelog

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
