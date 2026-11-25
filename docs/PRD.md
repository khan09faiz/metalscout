# PRD: MetalScout v1

## Problem
A raw-metal seller in India (steel, stainless, aluminium, copper, brass, zinc, pig iron, ferro alloys) needs a steady flow of **buyers who consume metal**: forgings, foundries, cable makers, auto-component plants, fabricators, PSU and private tenders. Today this means searching IndiaMART, Google and tender portals by hand in the evenings. Most results are **traders**, who are competitors, not customers. Contacts are scattered across sites, and nobody records where a number came from.

## User
One owner or a small sales team. They are not developers. They run Windows and use Excel or Google Sheets. They will call or email the top leads each morning.

## Goals
1. **Daily list of new end-user leads** with no manual work after setup.
2. **Every fact sourced**: email, phone, quantity and registration all carry the URL they came from.
3. **Traders filtered out** (or clearly marked).
4. **Contactable**: email and/or phone on most Tier A leads.
5. **Fully independent**: no LLM or paid API required. Runs offline from any AI service.

## Non-goals (v1)
- Sending email, SMS or WhatsApp. A human does outreach.
- Bypassing logins or CAPTCHAs, or scraping LinkedIn or IndiaMART pages.
- Guessing emails (pattern + SMTP probing). These are wrong too often and hurt sender reputation.
- Multi-user hosting. It is a local, single-user tool.

## Functional requirements
| # | Requirement | v1 |
|---|---|---|
| F1 | Discover companies via web search over metal × industry × city × template, rotating daily | ✅ |
| F2 | Browse each company site like a person (contact/about/products/vendor pages, pagination, lazy content) | ✅ |
| F3 | Extract emails (incl. obfuscated), Indian phones, GSTIN, CIN, Udyam, IEC, metals, quantities, certifications | ✅ |
| F4 | Classify manufacturer vs trader vs unknown, with the deciding phrases | ✅ |
| F5 | Score 0–100 with reasons; tiers A/B/C; configurable weights | ✅ |
| F6 | Buyer-signal capture from marketplace, tender and social search hits (restricted hosts: snippet only) | ✅ |
| F7 | Import tender and trade-show CSVs | ✅ |
| F8 | Daily schedule, catch-up after downtime, run history, lock, logs | ✅ |
| F9 | Dashboard: run button, KPIs, filters, lead drawer with evidence, stage and notes | ✅ |
| F10 | Excel (dated + latest), CSV, optional Google Sheet | ✅ |
| F11 | Re-profile sites every 30 days (facts become a time series) | ✅ |
| F12 | Do-not-contact list | ✅ |

## Success metrics
- ≥ 20 new profiled companies per daily run (DuckDuckGo); ≥ 50 with Serper.
- ≥ 60% of Tier A leads have an email **and** a phone.
- < 10% of Tier A leads turn out to be traders on manual review.
- Zero fabricated contacts: every value is traceable to a source URL.

## Risks
| Risk | Mitigation |
|---|---|
| Search provider throttling | Backoff and retry, stop after 5 failures, record it on the run; Serper option |
| Sites block bots | Real browser UA, polite delays; challenge pages recorded as `challenged`, not retried |
| Heuristic misclassification | Evidence phrases shown per lead; "Show traders" toggle; weights in config |
| Legal (DPDP, TRAI, ToS) | Restricted-host list, robots.txt, business contacts only; see COMPLIANCE.md |
