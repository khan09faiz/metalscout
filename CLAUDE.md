# Notes for AI assistants working on this repo

- Python 3.10+, no framework. Entry point `python -m metalscout`. Tests: `python -m pytest -q` (needs `playwright install chromium`).
- **No LLM calls in the runtime.** The engine must stay deterministic and free to run. Don't add model or API dependencies to the default path.
- Every stored fact is an observation with `source_url`. Never add code that produces a contact value that was not printed on a page.
- Don't add CAPTCHA solving, login automation, or crawling of hosts in `domains.restricted`.
- Stages chain through DB queries (`db.companies_needing_profile`, `db.signals_to_open`), not in-memory lists.
- Scoring lives only in `fit.py` and is computed on read; don't persist scores.
- UI is plain HTML/JS in `metalscout/web/`. Escape every page-derived string (`esc`, `safeUrl`).
- Docs to update when behaviour changes: README, docs/ARCHITECTURE.md, docs/SIGNALS.md, CHANGELOG.md.
