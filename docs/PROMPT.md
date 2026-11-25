# From prompt to product

This project was built from a conversation. The requests are kept here, in order and lightly cleaned up, because they are the real requirements.

## 1. The original brief

> Design a prompt with research to help me build a scraper and a sheet that identifies **manufacturers / end users that require raw metals, not traders**, to whom I can sell.
> - Always mention the **source** where the information was found.
> - Search the whole web: multiple sites, social media, **government tenders, private tenders**.
> - Always include a way to contact them: **email, phone number, company site, registration**, all if possible.
> - **Quantity** should be mentioned if there is one.
> - A good end-to-end system that fetches me the clients.

Clarifications given: **all metals** (ferrous, non-ferrous, stainless, alloys), **India (domestic)**.

## 2. Follow-ups that shaped the build

1. *"Use all the skills at your disposal to research and make things."* This led to four parallel research tracks: government tenders, B2B marketplaces, private/social/capex signals, and enrichment/legal. They are in `docs/research/`.
2. *"The scraper should be better and able to surf through sites; open-source or from scratch."* This led to a from-scratch Playwright surfer: best-first link priority, pagination, lazy-load scrolling, robots.txt.
3. *"Make a small website where you just click a button to find leads."* This led to the one-page dashboard.
4. *"Build a full engine that can run daily; no Claude needed; a fully independent system."* This led to the deterministic pipeline, run history, lock, scheduler and daily exports.
5. *"There is a project called Harvey on GitHub; reverse-engineer it and build something like it, a full private repo, end to end from prompt to all md files, design, code structure and final result."* This led to this repository. See `REFERENCE_SELLBIRD.md`.

## 3. The research prompt (for running with an AI assistant)

`prompts/master_prompt.md` is the standalone prompt. Paste it into Claude or another assistant with web search to do a one-off manual research pass. MetalScout is the automated, repeatable version of the same brief.

## 4. How the brief maps to the build

| Requirement | Where it lives |
|---|---|
| End users, not traders | `extract.classify` (manufacturer vs trader phrases), `fit.py` caps traders at 15 points; the Leads tab excludes traders |
| Source for every fact | `observations.source_url` on every row; source columns in Excel; "source" links in the dashboard |
| Whole web, tenders, social | `sources.py` query space and routing; buyer-signals table; `import` for tender exports |
| Email / phone / site / registration | `extract.emails/phones/registrations` (GSTIN, CIN, Udyam, IEC) |
| Quantity | `extract.quantities` (MT, TPA, kg, quintal, per period; ignores equipment tonnage) |
| End to end, daily, independent | `engine.py`, `scheduler.py`, Windows Task Scheduler, no LLM calls |
| Sheet at the end | `export.py`: dated xlsx, latest xlsx/csv, optional Google Sheet |
