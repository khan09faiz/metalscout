# Roadmap

## Shipped
- **v1.0:** discover → browser profile → score → dashboard + Excel, daily schedule, buyer signals, CSV import, do-not-contact list.
- **v1.1:** optional **agent crew** on free models (Sorter, Analyst, Writer, Scout) behind the grounding gate; named people and titles from the Analyst (`AGENT_PERSON`); free cloud deploy (GitHub Actions + Neon + Vercel); **dashboard password** (`DASHBOARD_PASSWORD`, required on Vercel).
- **v1.2:** hardening. Security (workflow injection, CSRF/DNS rebinding, SSRF past the seed URL, login rate limit, pinned actions), the wheel ships the agents and prompts, stricter grounding (quotes must support the fact; unverified numbers in drafts are flagged), agent retry limits, no N+1 in the read model, observation retention, run heartbeats, warnings vs errors, `MetalScoutBot` identity, ruff + mypy + lock files. See CHANGELOG.md.

## Next: better contacts
- Named people from team/about pages by deterministic title matching (purchase head, plant head, MD), alongside the Analyst's
- Optional Hunter.io domain search (50 free/month) behind a config flag, tagged `verified|risky|guess`
- MX check on found email domains

## Then: more sources (all public, no bypass)
- GeM public bid-listing adapter (bid no., item, quantity, buyer office) if its pages stay public and its terms allow
- PLI specialty-steel beneficiary lists (steel.gov.in) and trade-show exhibitor lists as seed importers
- Google Maps / Places listings via the official API (paid tier, has phone + website)

## Then: workflow
- Duplicate merge by GSTIN/CIN across domains
- Change detection: "capacity increased", "new vendor page" between profiles, flagged as *Why now* (the last `pipeline.keep_profile_runs` profiles are kept for this)
- Email/CSV daily digest of new Tier A leads

## Out of scope
- Sending outreach. Drafts are written, never sent.
