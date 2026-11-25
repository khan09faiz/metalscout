# Signal catalog

Every observation is `(signal, value, num, source_url, evidence)`. The profiler emits these per company per run.

| Signal | Value | Evidence / num | Used in score |
|---|---|---|---|
| `NAME` | og:site_name or `<title>` (before ` | `) | — | — |
| `PAGES_READ` | count | num = pages | — |
| `ORG_TYPE` | manufacturer / trader / unknown | phrases that decided it | manufacturer +30; trader caps at 15 |
| `MANUFACTURER_PHRASE` | e.g. "installed capacity", "foundry", "iso 9001" | page URL | via ORG_TYPE |
| `TRADER_PHRASE` | e.g. "stockists", "ready stock", "dealers" | page URL | via ORG_TYPE |
| `METAL` | steel / stainless / aluminium / copper / brass / zinc / nickel / pig_iron / ferro_alloy / lead_tin | matched sentence | +20 if in `business.sells` |
| `QUANTITY` | "120 MT per month", "2,400 TPA" | sentence; num = kg | +15 |
| `EMAIL` | address | "own domain" / "other domain" | +15 / +10 |
| `PHONE` | E.164 (+91…) | page URL | +10 |
| `GSTIN` `CIN` `UDYAM` `IEC` | registration number as printed | page URL | +5 |
| `CERTIFICATION` | ISO 9001, IATF 16949, BIS, IBR… | page URL | — |
| `BUYER_INTENT` | "vendor registration", "rfq", "tender", "requirement"… | page URL | +5 (with VENDOR_PAGE) |
| `VENDOR_PAGE` | URL containing vendor/supplier-reg/procure/tender/rfq | — | +5 |
| `CONTACT_PAGE` | contact page URL | — | — |
| `UNREACHABLE` | no page loaded | — | status=failed |
| `CHALLENGED` | bot-challenge page | — | status=challenged |

## Rules worth knowing
- **Emails** come only from the page: plain text, `mailto:`, `name [at] domain [dot] com`, and Cloudflare `data-cfemail`. Placeholders (`name@company.com`), image filenames and noreply addresses are dropped. Nothing is pattern-guessed.
- **Phones** are validated as Indian numbers by `phonenumbers` and normalised to E.164.
- **Quantities** on company sites must either carry a period (per month/year, TPA, TPM, MTPA) or sit near volume words (consumption, requirement, production, installed capacity, tender, qty). Equipment ratings next to *press, hammer, crane, furnace, load…* are ignored. On tender and marketplace text every volume counts.
- **Manufacturer** needs at least two manufacturer phrases and more of them than trader phrases. **Trader** needs at least two trader phrases and at least as many as manufacturer phrases. Anything else is **unknown**.
