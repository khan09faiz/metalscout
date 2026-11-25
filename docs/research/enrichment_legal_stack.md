# Contact enrichment, company verification, scraping stack and legal/compliance for an India B2B metal-buyer lead scraper (as of 25 Nov 2026)

Note on evidence quality: web search returned summaries; many pricing/accuracy items come from vendor blogs (flagged). Nothing here is legal advice. Items I could not source are in Gaps.

## 1. Enrichment tools (Hunter, Apollo, Lusha, Snov, etc.) and free methods: cost/accuracy for Indian SMEs

### Takeaway
Paid databases are weak on Indian SMEs (vendor and independent comparisons both report sparse India data), so the cost-efficient pattern is: own-website crawl + Google Places for phone/website, then Hunter-style email finding/verification only for the residual. Hunter is cheap per verified email; Apollo/Lusha are better for named contacts at larger firms than for small metal traders.

### Cited Findings
- Hunter pricing (USD): Free $0 = 50 credits/mo; Starter $49/mo (2,000 credits; $34/mo billed yearly); Growth $149 (10,000); Scale $299 (25,000). Domain Search/Email Finder = 1 credit per email found; Verifier = 0.5 credit; no charge if nothing found; credits don't roll over on monthly plans — [Hunter pricing](https://hunter.io/pricing)
- Apollo: Free, Basic, Professional, Custom tiers; pooled credits that expire each cycle; free plan email limited to Gmail accounts; one-click export up to 10,000 leads; plans are for internal use, and use of data in external products/resale needs a separate agreement. Exact prices were not shown on the fetched page — [Apollo pricing](https://www.apollo.io/pricing)
- Accuracy claims: Apollo and Lusha both claim ~98% email accuracy (vendor-sourced); one third-party case study found 85%; another independent tester put pre-verification accuracy ~89-92% (Apollo) and ~88-91% (Lusha). A reviewer running India searches found both sparse on India; an India-focused vendor guide (Prospeo, competitor) reports ~70% India accuracy for Apollo — [Apollo vs Lusha](https://www.apollo.io/insights/apollo-vs-lusha), [Puzzle Inbox](https://puzzleinbox.com/compare/apollo-vs-lusha-2026), [Prospeo India guide](https://prospeo.io/s/b2b-database-providers-in-india) (all vendor/competitor sources; treat as directional)
- Snov.io claimed ~40% cheaper than Apollo Basic (competitor blog) — [Apollo Snov alternatives](https://www.apollo.io/insights/snovio-alternatives)
- SMTP verification limits: catch-all domains answer 250 to everything so mailbox probes carry no information; catch-all accuracy ~70-85% with secondary evidence per one vendor guide; Yahoo/AOL/some Microsoft setups restrict or generalise responses — [Snov catch-all](https://snov.io/blog/how-to-verify-catch-all-emails/), [Prospeo catch-all](https://prospeo.io/s/catch-all-email-verification), [Tomba how verification works](https://tomba.io/blog/how-does-email-verification-work)
- Google Places API (New): free monthly caps per SKU: Essentials 10,000 (India 70,000), Pro 5,000 (India 35,000), Enterprise 1,000 (India 7,000) — [Google pricing categories](https://developers.google.com/maps/billing-and-pricing/pricing-categories)
- Phone (`nationalPhoneNumber`, `internationalPhoneNumber`) and `websiteUri` are Enterprise-tier fields for both Place Details and Text Search; a mixed field mask bills at the highest SKU; India has separate SKU IDs and a separate India price list (rates not retrieved). Text Search "IDs Only" is Essentials — [Places SKU details](https://developers.google.com/maps/billing-and-pricing/sku-details/places.md.txt), India price list linked from [Google pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
- MCA: no official public MCA API found; MCA portal lookups are manual/captcha-gated. Free route: data.gov.in "RoC-wise Company Master Data" (~3.67M companies; CIN, status, capital, registered address), free API key; periodic snapshot, no directors/DIN/charges — [data.gov.in resource](https://www.data.gov.in/resource/registrars-companies-roc-wise-company-master-data), [Apify OGD actor](https://apify.com/nexgendata/ogd-india-companies-registry), [MCA data guide](https://www.globaldatabase.com/mca-master-data-company-search-how-to-find-information-on-indian-businesses)
- Udyam: official verification takes only the 19-digit Udyam number plus a verification code; no search by business name or PAN on the public form. Paid verification API exists (e.g. Cashfree) — [Udyam portal](https://udyamregistration.gov.in/searchregistration.aspx), [Xflow explainer](https://www.xflowpay.com/blog/udyam-registration-verification), [Cashfree Udyam API](https://www.cashfree.com/docs/api-reference/vrs/v2/udyam/verify-udyam)
- GSTIN: official portal "Search Taxpayer" works without login for any GSTIN (captcha each time); licensed GSP/GVS access via e.g. Protean; Cashfree/Surepass-type commercial APIs; Apify captcha-solving actors from ~$5/1,000 results (unofficial) — [GST portal manual](https://tutorial.gst.gov.in/userguide/taxpayersdashboard/Search_Taxpayer_manual.htm), [Protean GST services](https://www.proteantech.in/services/gst-services), [Cashfree GST](https://www.cashfree.com/gst-verification/), [Apify GSTIN actor](https://apify.com/mikolabs/gstin)
- IEC: DGFT "View Any IEC" is a public, free, captcha-gated check returning name, address, status; sources disagree on inputs (IEC + first 3 letters of firm name vs IEC/PAN); no search by company name alone — [Amazon India IEC guide](https://sell.amazon.in/grow-your-business/amazon-global-selling/blogs/iec-code-verification), [Xflow IEC](https://www.xflowpay.com/blog/iec-code-verification), [Razorpay IEC](https://razorpay.com/blog/iec-code-verification-online/) (commercial blogs, not DGFT docs)

### Inferences
- A GSTIN or CIN is not obtainable by name from official free sources; reverse-lookup (name -> GSTIN/CIN) must come from the company's own website footer/invoice pages, IndiaMART/TradeIndia listings, or paid APIs. Use official free sources to validate numbers you already have, not to discover them.
- Recommended enrichment order (cheapest first): (1) Places API text search with field mask limited to Pro fields, then Enterprise only for shortlisted leads, using India free caps (7,000 Enterprise calls/month free) ; (2) crawl company site /contact, /about, footer, mailto/tel and schema.org JSON-LD; (3) data.gov.in master data join on name+state to get CIN/status; (4) Hunter (verifier 0.5 credit) only for domains with no published email; (5) generic role mailboxes (sales@, info@, purchase@) are the realistic B2B target for Indian SMEs and are lower DPDP risk than named individuals.
- Hunter Starter ($49/mo) = ~4,000 verifications or 2,000 finds; Free 50 credits suffices only for pilot testing. Apollo/Lusha India-SME hit rates are likely low; test on 100 known domains before paying.
- Own pattern+SMTP verification: run only from a clean IP/VPS with proper rDNS; many consumer-hosted Indian SMEs sit on Gmail/Workspace or Microsoft 365 or catch-all hosts, so mark results "unverified/risky" rather than "valid".

### Gaps
- INR pricing for Apollo, Lusha, Snov, Kaspr, ScaleList, RocketReach; current Lusha/Snov/Kaspr/RocketReach plan details not retrieved. No independent India-SME benchmark found.
- Clearbit alternatives (Clearbit is now HubSpot Breeze Intelligence) not researched.
- Google Places per-1,000 prices (global and India) not retrieved; WHOIS usefulness (post-GDPR redaction, .in registry privacy) not researched; OpenCorporates India coverage/API terms not researched.
- GST portal and Udyam portal terms of use on automated access not found.
- Whether MCA open-data snapshot is current as of 2026 (refresh date) not verified.

## 2. Scraping stack for 2026 and recommended architecture

### Takeaway
Use free, self-hosted tools (Playwright + Scrapy or Crawl4AI) for company-site crawling, a cheap SERP API (Serper) for discovery, and Places API for phone/website; write results to Google Sheets with gspread via a batch pipeline. Avoid captcha-solving against government portals; use licensed APIs there.

### Cited Findings
- Crawl4AI: generally described as Apache-2.0, free to self-host (cost = servers, proxies, LLM tokens); Firecrawl core is AGPL-3.0 with paid hosted credits (~$99/mo for 100k credits per Firecrawl's own page; other sources cite cheaper entry plans). Sources conflict on Crawl4AI license (Apache vs MIT) and whether a hosted Crawl4AI tier exists — [Firecrawl vs Crawl4AI](https://www.firecrawl.dev/alternatives/firecrawl-vs-crawl4ai), [Apify comparison](https://blog.apify.com/crawl4ai-vs-firecrawl/), [DEV Community guide](https://dev.to/sharonbull_ca141b00035fd6/crawl4ai-vs-firecrawl-a-practical-decision-guide-for-ai-crawling-in-2026-be8)
- AGPL requires publishing source changes if you run a modified Firecrawl as a network service — [Scrappey](https://scrappey.com/qa/web-scraping-apis/crawl4ai-vs-firecrawl)
- Serper.dev: prepaid credits, ~$50 for 50,000 (~$1.00/1k) falling to ~$0.30/1k at volume; 2,500 free queries on signup; 11-100 results cost 2 credits; one source says public pricing page 404'd in July 2026. SerpAPI ~$25/1k list (lowest effective ~$9) — [ColdIQ Serper pricing](https://coldiq.com/blog/serper-pricing), [Serper pricing explained](https://apiserpent.com/blog/serper-pricing-credits-explained), [SERP API comparison](https://apiserpent.com/blog/serp-api-pricing-comparison)
- Captcha/automation: commercial solvers exist for GST portal (Apify actors), but official portals do not document permission for automated captcha bypass; licensed GSP/API routes are the sanctioned alternative — [Apify GSTIN actor](https://apify.com/mikolabs/gstin), [Protean](https://www.proteantech.in/services/gst-services)

### Inferences
- Recommended architecture (my design, not sourced): 
  1. Discovery: Serper queries ("<metal> traders/fabricators/manufacturers <city>") + Places Text Search (IDs-only Essentials free, then Details for shortlisted) + directory pages (IndiaMART/TradeIndia — check their ToS first).
  2. Queue + dedupe by normalised domain/phone/GSTIN in SQLite/Postgres (Sheets is output only; Sheets API quotas make it a poor system of record).
  3. Fetch: Scrapy/httpx for static sites; Playwright (or Crawl4AI) fallback for JS-heavy sites; respect robots.txt, 1-2 req/sec/domain, identify user-agent, cache.
  4. Extract: regex + mailto/tel + JSON-LD; LLM extraction only for messy pages (cost control).
  5. Verify: syntax -> MX -> optional SMTP/Hunter verifier; GSTIN checksum validate locally (free); CIN regex; validate against licensed API only for shortlisted leads.
  6. Score and write to Google Sheets with gspread batch `append_rows`/`update` (one call per batch to stay within quotas) plus provenance columns (source URL, fetch date, lawful-basis note).
- Proxies: Indian datacenter IPs suffice for company sites; residential proxies only if blocked, and that is an escalation signal to stop rather than evade for sites whose ToS forbid scraping.

### Gaps
- No sourced details on Playwright/Scrapy 2026 versions, gspread quota numbers, proxy vendor pricing for India, or Firecrawl current plan details.

## 3. Legal and compliance (DPDP, IT Act, TRAI/TCCCPR, WhatsApp, robots/ToS)

### Takeaway
DPDP Rules were notified 13 Nov 2025; substantive duties (notice, consent/legitimate use, rights, security) start 13 May 2027, so building compliant now is prudent but not yet enforceable. Phone/SMS outreach is the highest-risk channel (TRAI DND/140-series); WhatsApp requires opt-in; B2B email to role-based business addresses is the lowest-risk channel. Scraping is not specifically banned in India but is not blanket-permitted either.

### Cited Findings
- DPDP Rules notified 13 Nov 2025; three phases: Phase I (13 Nov 2025) institutional provisions (Data Protection Board etc.); Phase II (13 Nov 2026) consent manager provisions; Phase III (13 May 2027) substantive obligations (notice, consent, fiduciary duties, rights, cross-border). Some sources say 14 Nov dates; check Gazette — [AZB](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/), [YourStory](https://yourstory.com/2025/11/digital-personal-data-protection-dpdp-rules-2025-rollout-over-18-months), [PIB doc](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf), [Grant Thornton](https://www.grantthornton.in/en/insights/articles/dpdp-act-businesses-should-prepare-now-for-phased-obligations/)
- DPDP s.3(c)(ii) excludes personal data made public by the data principal herself or by someone legally obliged to publish it. Commentators say it is narrow: you must verify the source, document the basis, and the Act doesn't say aggregation/enrichment/profiling preserves the exemption; Rules add no clarity — [DPDP s.3 text](https://dpdpa.com/dpdpa2023/chapter-1/section3.html), [India Briefing](https://www.india-briefing.com/news/india-dpdp-act-publicly-available-personal-data-46899.html/), [IAPP](https://iapp.org/news/a/scraping-public-data-in-india-innovation-enabler-or-privacy-threat-), [Law School Policy Review](https://lawschoolpolicyreview.com/2026/01/13/publicly-available-data-under-the-dpdp-act-the-limits-of-exemptions-in-ai-driven-processing/)
- Scraping in India: no specific statute; IT Act s.43 gives civil liability for access/copying without owner permission, s.66 criminal only with dishonest/fraudulent intent; government told Parliament scraping public data may breach s.43; Copyright Act: facts unprotected but compilations/substantial database extraction can infringe; heavy load may fall under s.43 disruption limb — [Law.asia](https://law.asia/india-data-scraping-regulation/), [Mondaq](https://www.mondaq.com/india/copyright/900156/data-scraping-and-legal-issues-in-india), [Rajya Sabha PQ](https://rsdebate.nic.in/bitstream/123456789/758404/1/PQ_267_07022025_U558_p280_p280.pdf), [iPleaders](https://blog.ipleaders.in/data-scraping-legality/)
- TRAI TCCCPR Second Amendment (12 Feb 2025): 140 series for promotional calls, 1600 series for transactional/service calls; DND preferences govern 140 promotional calls; 1600 must not be used for promotional voice calls. TRAI directions (19 Nov 2025 for RBI/SEBI/PFRDA entities; 16 Dec 2025 for IRDAI) mandate 1600 series for their service calls. Draft Third Amendment issued 13 Mar 2026 (status not verified). Earlier reporting: 10-digit numbers banned for telemarketing — [TRAI PR 11/2025](https://cms.trai.gov.in/sites/default/files/2025-02/PR_No.11of2025.pdf), [Regulation 12 Feb 2025](https://trai.gov.in/sites/default/files/2025-02/Regulation_12022025.pdf), [Fone Arena](https://www.fonearena.com/blog/446114/trai-tcccpr-2025-tougher-rules-spam-calls-sms.html), [SCC Online](https://www.scconline.com/blog/?p=390749), [TRAI Direction 19 Nov 2025](https://www.trai.gov.in/sites/default/files/2025-11/Direction_19112025_0.pdf), [TRAI PR 91/2026](https://trai.gov.in/sites/default/files/2026-07/PR_No91of2026.pdf)
- WhatsApp Business policy: you may contact someone only if they gave you their number and opted in to your messages; separate opt-ins recommended per category; must honour opt-out/blocks; user blocks/reports can throttle or remove your access; unauthorised bulk messaging cited; outside 24h window only approved templates — [WhatsApp Business policy](https://whatsappbusiness.com/hi/policy/)
- WhatsApp India pricing: per-message billing since 1 Jul 2025; marketing rate raised to ~INR 0.8631 from 1 Jan 2026 (another source says ~1.09, likely includes markup); 18% GST extra — [AiSensy update](https://m.aisensy.com/blog/whatsapp-per-message-pricing-update-effective-january-1-2026/), [MyOperator](https://myoperator.com/blog/whatsapp-business-api-pricing-india-2026)

### Inferences (practical compliance checklist; my synthesis, verify with counsel)
1. Prefer company-level data: generic mailboxes, switchboard/office numbers, registered addresses, GSTIN/CIN. Avoid harvesting named individuals' personal mobiles/emails/social profiles; if collected, document source and why s.3(c)(ii) or a legitimate use applies.
2. Collect only what outreach needs; store provenance (URL, date), retention limit (e.g. 12 months), and a deletion/suppression process by 13 May 2027 at the latest.
3. Every email: identify sender/company, physical address, accurate subject, one-click unsubscribe, honour opt-outs within days; maintain a suppression list that survives re-scraping (CAN-SPAM-like practice; India has no direct CAN-SPAM equivalent found in my research).
4. Calls/SMS: scrub numbers against NCPR/DND before any promotional call or SMS; use registered telemarketer/140-series and DLT-registered headers/templates for SMS; don't use ordinary 10-digit numbers for telemarketing. Treat mobile numbers as DND-risky by default; prefer email first, phone for inbound/warm follow-up.
5. WhatsApp: cold outreach to scraped numbers breaches Meta policy and risks number ban; send only to contacts who opted in (e.g. IndiaMART enquiry, reply to email, click-to-WhatsApp).
6. Scraping hygiene: honour robots.txt, ToS and rate limits; do not bypass login or captcha; do not scrape sites whose ToS prohibit it (IndiaMART etc. — read their ToS); prefer official APIs/open data; don't wholesale copy a directory's database (compilation copyright).
7. Government portals: use data.gov.in and licensed APIs rather than captcha-solving.
8. Keep a simple DPIA-style note and a contact point for grievance/erasure requests.

### Gaps
- Whether DPDP s.7 "legitimate uses" covers B2B marketing: not found; likely it does not (s.7 lists specific uses), so consent/notice may be needed for named individuals after May 2027 — unverified.
- DPDP penalty amounts (up to INR 250 crore per Act schedule) not confirmed in my sources.
- NCPR/DND details for business-to-business calls (whether B2B numbers are exempt), DLT registration steps, and status of the Third Amendment 2026 not verified.
- robots.txt legal weight in India, enforceability of browsewrap ToS, and Indian case law on scraping not found.
- IT (Intermediary) Rules/Spam rules for email: nothing found.

## 4. Lead scoring for metal buyers (fit, quantity, recency, reachability)

### Takeaway
No sourced frameworks specific to metal buyers were found; the following is a proposed model.

### Cited Findings
- None (no sources searched for this question).

### Inferences (proposed model, 100 points)
- Fit (35): NIC/keyword match to end-use (fabrication, auto components, construction, forgings, pipes, electricals); product-grade match; state/region within delivery radius; entity type (Pvt Ltd/LLP via CIN > proprietorship); active GST/MCA status (+) and "strike off/inactive" (disqualify).
- Quantity (25): proxy signals only (employee/plant size from Udyam category medium/small, IEC holder = imports, multiple plants, tender/RFQ volumes, LinkedIn headcount, capital from MCA master data).
- Recency/intent (20): fresh RFQ/enquiry or tender < 30 days, new GST/incorporation < 24 months, website/product update, hiring for purchase roles; decay linearly after 90 days.
- Reachability (20): verified generic email on own domain (+8), switchboard phone from Places (+5), named purchase contact (+4), WhatsApp opt-in (+3); penalise catch-all-only or free-mail-only (-5) and DND-flagged mobile.
- Tiering: >=70 call/email now; 45-69 email nurture; <45 hold. Log score components in Sheets for auditability and calibrate weights after ~100 outcomes.

### Gaps
- No benchmark data on conversion by signal for Indian metal buyers; weights are unvalidated.
