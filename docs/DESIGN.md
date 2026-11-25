# Design

## Dashboard (`http://localhost:8000`)
One page, no build step, works offline.

```
┌ MetalScout · My Metals Co ─────────────── [last run ok] [Find leads now] [Download Excel] ┐
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 8 Leads │ 6 Tier A │ 2 Tier B │ 8 New today │ 8 Buyer signals │ 0 Queued │ Next run 06:30 │
├ Leads │ Buyer signals │ Runs & log │ Add sites ──────────────────────────────────────────┤
│ [search…] [tier▾] [metal▾] ☐ New today ☐ Has email/phone ☐ Show traders     8 shown      │
│ Tier Score Company        Metals          Quantity      Email (source) Phone (source) Why  │
│  A   100   Emerson Forge  steel, copper…  9000 MTPA     info@…  source +91…  source   …    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
          click a row ─► right drawer: every fact with its source link and quoted evidence,
                         registrations, contact/vendor page, pipeline stage, notes [Save]
```

**Principles**
- **Evidence one click away.** Every email, phone and quantity shows a `source` link. The drawer quotes the sentence the quantity came from.
- **Why, not just a score.** The reasons column says why ("manufacturer / end user; uses steel; quantity: 9000 MTPA; company email").
- **Honest state.** The run pill shows running / last status. The Runs tab shows per-stage counts and errors, and the log tails the engine log.
- **One button.** "Find leads now" spawns a background run. The page polls every 5 s and refreshes leads while it runs.

**Colour:** navy header `#1f3864`, Tier A green `#16a34a`, B amber `#d97706`, C grey `#94a3b8`, action blue `#2563eb`.

## Spreadsheet (`exports/leads_latest.xlsx`)
| Tab | Contents |
|---|---|
| Leads | End users only (traders excluded), sorted by score. Each contact column is followed by its source column |
| All companies | Everything profiled, including traders and failures |
| Buyer signals | Marketplace, tender, social and CSV rows with intent hits, metals, quantity and contacts |
| Runs | Run history with stats and errors |
| README | How to read the sheet; scoring; compliance reminder |

Header navy with white bold text, frozen header row, auto-filter, wrapped cells, 26-wide columns. Leads columns: Tier, Score, Company, Type, Metals, Quantity, Quantity evidence, Quantity source, Email, Email source, Phone, Phone source, Website, Contact page, Vendor page, GSTIN, CIN, Udyam, IEC, Certifications, Why, Found via, First seen, Last checked, New today, Stage, Notes.

## Config (`metalscout.yaml`)
Everything a non-developer would want to change is in the YAML: what you sell, the search grid, domain lists, crawl politeness, score weights, schedule time, export targets and the do-not-contact list. Nothing is hard-coded that a seller would want to tune.
