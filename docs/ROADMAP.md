# Roadmap

## v1.0 (this release)
Discover → browser profile → score → dashboard + Excel, daily schedule, buyer signals, CSV import, do-not-contact list.

## v1.1: better contacts
- Named people from team/about pages (purchase head, plant head, MD) with title matching
- Optional Hunter.io domain search (50 free/month) behind a config flag, tagged `verified|risky|guess`
- MX check on found email domains

## v1.2: more sources (all public, no bypass)
- GeM public bid-listing adapter (bid no., item, quantity, buyer office) if its pages stay public and its terms allow
- PLI specialty-steel beneficiary lists (steel.gov.in) and trade-show exhibitor lists as seed importers
- Google Maps / Places listings via the official API (paid tier, has phone + website)

## v1.3: workflow
- Duplicate merge by GSTIN/CIN across domains
- Change detection: "capacity increased", "new vendor page" between profiles, flagged as *Why now*
- Email/CSV daily digest of new Tier A leads
- Optional dashboard password for LAN use

## Ideas parked
- LLM summarisation of company profile (optional, off by default to keep the system independent)
- Outreach sending: out of scope by design
