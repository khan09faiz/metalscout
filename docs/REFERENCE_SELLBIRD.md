# Reference: Sellbird (formerly "Harvey")

**Repo:** https://github.com/ethanplusai/sellbird. It was called Harvey until v0.4.0 and has about 7.3k stars. It is an open-source autonomous outreach platform for small local businesses.
**License:** AGPL-3.0-only from v0.4.0; MIT for ≤ 0.3.x.

## Clean-room statement
MetalScout contains **no code from Sellbird**. The Sellbird repository was cloned read-only and its public documentation (`docs/how-it-works.md`, `docs/signals-and-pipeline.md`) and a few short modules (`pipeline.py`, `fit.py`) were read to understand the *architecture*. All MetalScout code, docs and prompts were written from scratch for a different domain (raw-metal B2B buyers in India). Ideas and architecture are not copyrightable. Code is, and none was copied, so the AGPL does not apply to this repository.

## What Sellbird does
A local Python service with a heartbeat (wake → quiet hours? → budget? → decide → act → log → sleep, every 15 min). It decides deterministically: reply > send > write > prospect > idle. It discovers local businesses (OpenStreetMap, Serper, DataForSEO, Scavio), profiles their websites with plain HTTP, finds owners, learns email patterns, verifies addresses, writes emails using the user's Claude or Codex *subscription* CLI, gates every send, and shows it all on a FastAPI dashboard. Skills and prompts are editable Markdown.

## Ideas adopted
| Sellbird idea | MetalScout version |
|---|---|
| Deterministic decisions, model only where judgment is needed | **No model at all**: search, crawl, regex and formula |
| Stages independently re-runnable, chained by DB queries | `companies_needing_profile()` drives PROFILE, so crashed runs resume |
| Observations with evidence; re-observe on a schedule into a time series | `observations` table, `reprofile_after_days: 30` |
| Fit score computed on read with reasons, weights in config | `fit.score()` with the reasons shown in the UI and Excel |
| "A failure is an observation, not silence" | `UNREACHABLE`/`CHALLENGED` observations, run errors, `partial` status |
| Challenge pages reported, not retried or bypassed | `extract.is_challenge` → `status=challenged` |
| Junk/directory filtering of search hits | `sources.route()` with skip/signal/restricted lists |
| Never read sites whose terms forbid scraping (LinkedIn, Crunchbase…) | `domains.restricted`: snippet only |
| Never invent contacts; tag honestly | Only printed emails; placeholders dropped; source on every value |
| SSRF guard on crawled URLs | `net.is_public()` |
| Plain-HTML dashboard, no build step | `metalscout/web/` |
| Editable Markdown prompts and skills | `prompts/master_prompt.md`, all docs |
| Export a sequencer-ready file even if you never send | `leads_latest.csv` / `.xlsx` |

## Deliberately different
| Sellbird | MetalScout | Why |
|---|---|---|
| Writes and sends email via an LLM subscription | No outreach. A human contacts leads | The brief asked for a lead list; avoids sending risk and AI dependence |
| HTTP profiler (3 requests per site, no browser) | Playwright browser, up to 12 pages | Indian SME metal sites are often JS-heavy, with contacts deep on the contact page |
| ICP: owner titles, hiring, ad pixels, agencies | ICP: manufacturer vs trader, metals, **tonnage**, GST/CIN, vendor pages | Different market |
| Email pattern learning + verification | Not in v1 | Indian SME sites mostly publish role inboxes; guessing is risky (see ROADMAP) |
| 15-minute heartbeat daemon | Once-a-day run, via the OS scheduler or the in-app heartbeat | Lead lists don't need minute-level freshness |
