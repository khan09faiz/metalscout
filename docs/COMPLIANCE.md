# Compliance (practical notes, not legal advice)

## What MetalScout does by design
- Respects `robots.txt` on every page (as `MetalScoutBot`, see below) and waits 1–2.5 s between pages. Reads at most 12 pages per site.
- **Never bypasses** CAPTCHAs, logins, paywalls or bot challenges. Challenged sites are recorded and left alone.
- **Never opens** hosts whose terms forbid automated access or which actively litigate scraping: IndiaMART (terms bar "systematic retrieval" by robots), LinkedIn (Proxycurl injunction, hiQ settlement), Facebook, Instagram, X, JustDial, Alibaba. It keeps only the search-engine snippet.
- Collects **business contact data published by the business itself** and records the source URL, so you can show where you got it.
- Never guesses or SMTP-probes email addresses.
- Has a do-not-contact list (`compliance.do_not_contact`) that zeroes a company's score. An entry is an email address or a domain; a domain entry matches that company's site and subdomains, and any email at that domain or its subdomains wherever it was found.

## Crawler identity (user agent)
MetalScout identifies itself as **`MetalScoutBot/<version> (+https://github.com/khan09faiz/metalscout)`** (`crawl.user_agent`).
- **robots.txt** is fetched with that UA and matched against it, so a site can write rules for `User-agent: MetalScoutBot`. (Before 1.2 the crawler matched as `Mozilla`, so only `*` rules applied.)
- **The browser** (Playwright) needs a UA that sites will render for. By default it sends Chrome's UA **with the bot UA appended** (`crawl.browser_user_agent: ""`), the same approach search-engine crawlers use: pages render as in Chrome, and the site's logs and firewalls can still see and block MetalScoutBot.

| `crawl.browser_user_agent` | Effect |
|---|---|
| `""` (default) | Chrome UA + `MetalScoutBot/…`. Honest and identifiable. A few sites that block anything containing "bot" will refuse or challenge it; those are recorded as failed/challenged and left alone |
| plain Chrome UA | More sites load, but the crawler is no longer identifiable in their logs while robots.txt is still matched as MetalScoutBot. Use only if you accept that trade-off; it does not make bypassing blocks acceptable |
| your own bot string | Set `user_agent` too, with a URL or email where site owners can reach you |

MetalScout never rotates user agents or proxies to get past a block.

## Your obligations when you use the leads
| Rule | What it means in practice |
|---|---|
| **DPDP Act 2023 + DPDP Rules** (notified Nov 2025; main duties from about May 2027) | The public-data exemption is read narrowly. Keep to role and business addresses (info@, sales@, purchase@), keep the source, honour opt-outs immediately (add to do-not-contact), don't sell the list |
| **TRAI TCCCPR** (2025 amendment) | Promotional calls/SMS must use 140-series headers. Check DND/NCPR for mobile numbers before calling. B2B is not a blanket exemption |
| **WhatsApp Business policy** | Message only people who gave you their number and opted in. A scraped number is not opt-in |
| **IT Act s.43 / contract (ToS)** | Scraping against a site's terms can bring civil claims. That's why the restricted list exists. Extend it if a site's terms say no |
| **Email** | Identify yourself, give a clear opt-out, send low volume from a warmed domain |

Sources: `docs/research/enrichment_legal_stack.md`, `docs/research/private_social_signals.md`, `docs/research/b2b_marketplaces.md`.
