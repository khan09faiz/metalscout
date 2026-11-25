# Changelog

## 1.0.0 (2026-11-25)
- First release: deterministic daily pipeline (discover, profile, signals, export)
- Playwright site surfer with priority links, pagination, lazy-load, robots.txt, per-site timeout, SSRF guard
- Extractors: emails (incl. obfuscated and Cloudflare), Indian phones, GSTIN, CIN, Udyam, IEC, metals, quantities (equipment tonnage ignored), certifications, manufacturer/trader/intent
- Fit score with reasons; tiers; trader cap; do-not-contact
- Dashboard (stdlib server, no build step); Excel with 5 tabs; CSV; optional Google Sheets
- Windows Task Scheduler install, in-app heartbeat, run lock and history
- 22 tests, including a real-browser end-to-end crawl of a local fixture site
