# Private tenders, social media and signal sources for Indian metal end-user buyers

Note: research used about 17 searches, mostly search-snippet level; few pages were fetched in full. Vendor claims are marketing. Legal points are not legal advice. Dork and query templates are the researcher's own constructions (not from sources) and are labelled as inferences.

## (a) Private tender / RFQ / supplier-registration sources

### Takeaway
Large corporates (Tata Steel, Adani, Reliance) run supplier-registration portals, but these are onboarding gateways for sellers, not public lists of live RFQs or buyer contacts. The practically open buyer-intent channels are B2B marketplaces (IndiaMART buy leads, mjunction auctions, Recycleinme) and tender aggregators. Whether these are useful depends on being a registered supplier.

### Cited Findings
- Tata Steel vendor registration: third-party guides describe a "Vendor Partner sign-up" for new suppliers (business profile plus documents, reviewed by Tata) and "Vendor Zone" for existing suppliers. PAN and email are needed. Guides are third-party, so verify on Tata's own site. — [TataNexarc guide](https://blog.tatanexarc.com/da/tata-steel-vendor-registration), [TenderShark guide, Apr 2026](https://www.tendershark.com/blogs/tata-steel-eprocurement-registration-login-and-eligibility-complete-guide)
- Tata Steel's European units (UK, Netherlands) use SAP Ariba, with registration by invitation only. — [Tata Steel UK Ariba FAQ](https://www.tatasteeluk.com/suppliers/ariba), [Tata Steel Nederland](https://products.tatasteelnederland.com/suppliers/ariba)
- Tata aggregator pages list "Tata Steel Limited tenders" (third-party aggregator). — [TataNexarc tender page](https://www.tatanexarc.com/t/authority/tata-steel-limited-tsl-tenders/eproc-tata-steel-login/)
- Adani: onboarding runs via a supplier toolkit, self-registration forms and SAP Ariba invitations by email. — [Adani Supplier Toolkit](https://www.adanienterprises.com/supplier-toolkit), [Adani Enterprises Ariba guide](https://www.adanienterprises.com/-/media/Project/Enterprises/Home/Supplier-Expression-of-Interest-user_guide), [Adani Power vendor manual](https://adanipower.com/-/media/Project/Power/Commercials/Manual-VendorRegistration.pdf)
- Reliance: new-supplier registration via preliminary qualification questionnaire at scm.ril.com (document marked internal; currency uncertain). — [Reliance PQQ doc](https://scm.ril.com/Vendor/NewSupplierRegistration-PQQRPMG.pdf)
- Vedanta group: Cairn Oil and Gas uses a "Smart source" vendor portal. No group-wide Vedanta URL was found. — [Cairn supplier page](https://www.cairnindia.com/?p=2941)
- JSW Steel: no official vendor-registration portal found in search. It publishes a supplier code of conduct and runs a supply chain assessment, and operates a steel-for-MSME buying site (buyer channel, 2020 report). — [JSW supply chain sustainability](https://www.jswsteel.in/supply-chain-sustainability), [YourStory on JSW MSME site](https://yourstory.com/smbstory/jsw-steel-msmes-website)
- mjunction (SAIL/Tata Steel JV): B2B e-auction platform for steel, scrap, ores. It claims 6,000+ buyers regularly buy scrap; claims are self-reported. M&M scrap auction (9,000 t, FY19) is an example. Mjunction sells steel to end-users via auction. — [mjunction FAQ](https://www.mjunction.in/faq/), [Autocar Pro](https://www.autocarpro.in/news-national/mjunction-sells-9-000-tonnes-of-mahindras-automotive-steel-scrap-42936?amp=1), [mjunction flat steel selling PDF](https://www.mjunction.in/wp-content/uploads/2021/08/Selling-Steel-Flat-Steel.pdf)
- MSTC is a comparable government e-auction platform for ferrous scrap. — [Ministry of Steel MSTC note](https://steel.gov.in/sites/default/files/2026-01/MSTC%20Write%20Up.pdf)
- SAP Business Network Discovery (formerly Ariba Discovery): buyers post sourcing needs free; matching suppliers are notified; suppliers historically paid fees to respond (COVID waiver ended Dec 2020; current fees unverified). Postings are matched, not clearly public. — [SAP India page](https://www.sap.com/india/products/business-network/find-suppliers.html), [TechTarget](https://www.techtarget.com/searchsap/news/252480371/SAP-Ariba-Discovery-opened-to-all-buyers-and-suppliers), [SAP blog 2020](https://blogs.sap.com/2020/05/21/sap-ariba-supplier-connection-may-2020/)
- IndiaMART BuyLeads: buyers post requirements, IndiaMART filters and routes to sellers; consuming a lead reveals buyer contact; verified contacts get green tick; metal postings show material, quantity, order value. Pay-per-lead (2012 report: from Rs 50; current price not found). — [IndiaMART buy lead help](https://help.indiamart.com/knowledge-base/buy-lead), [IndiaMART buy leads](https://corporate.indiamart.com/buy-leads/), [Business Standard 2012](https://www.business-standard.com/article/sme/b2b-buy-sell-service-for-smes-launched-112110600072_1.html)
- Recycleinme lists scrap buy offers (e.g. 1,000 MT/month mild steel scrap, Delhi-NCR). — [Recycleinme example](https://www.recycleinme.com/rim-jatinpathi/buyoffer-54906)
- ExportersIndia buyer requirement scrapers exist on Apify (metals buy leads). Third-party scraping of that site; ToS not checked. — [Apify metals buyers](https://apify.com/scrapers_lat/exportersindia-buyers-scraper/examples/export-metals-buy-leads-india.md)

### Inferences
- Large-corporate portals give registration for you as supplier, which then yields RFQ invitations; they do not leak contacts. The cheapest early-stage path is marketplaces (IndiaMART, mjunction, Recycleinme, ExportersIndia, TradeIndia) plus aggregator alerts.
- Scraping marketplace buy leads is likely a ToS breach (not verified); buying leads inside the platform is the compliant route.

### Gaps
- L&T supplier portal: no result. JSW official portal: not found. Mjunction access/fees, current IndiaMART metal lead pricing, and Tender247/TenderTiger/BidAssist (aggregator) pricing not researched.
- Which private tender aggregators carry private-sector (non-government) tenders was not verified.

## (b) Social media sources

### Takeaway
Little reliable, citable evidence exists for open WhatsApp/Telegram metal groups; invite links are not indexed publicly. LinkedIn is the main findable channel, but scraping carries real litigation risk.

### Cited Findings
- LinkedIn sued Proxycurl (Jan 2025) over fake accounts and mass profile scraping; a permanent injunction followed and Proxycurl reportedly shut down. A secondary blog dates the shutdown July 2026 (low reliability). — [LinkedIn news](https://news.linkedin.com/2025/linkedin-takes-legal-action-to-defend-member-privacy), [LinkedIn win announcement](https://news.linkedin.com/2025/LinkedInWinsLegalBattleToProtectMemberData), [StartupHub](https://www.startuphub.ai/ai-news/startup-news/2025/the-1-linkedin-scraping-startup-proxycurl-shuts-down), [DEV post](https://dev.to/zackrag/linkedin-scraping-is-dead-5-legal-tos-safe-alternatives-that-actually-work-in-2026-3f36)
- hiQ v LinkedIn ran 2017-2022 and settled; court said scraping public data can be allowed in certain circumstances but breach-of-contract claims remain possible. — [Bloomberg Law](https://news.bloomberglaw.com/ip-law/linkedin-battles-online-scrapers-in-perpetual-struggle-over-data)
- LinkedIn also sued ProAPIs over scraping. — [Security Affairs](https://securityaffairs.com/183001/security/linkedin-sues-proapis-for-15k-month-linkedin-data-scraping-scheme.html)
- Searches for Telegram/WhatsApp metal trading groups returned only marketplace listings, a WhatsApp rates channel, and dealer profiles, no invite links. — [WhatsApp rates channel](https://www.whatsapp.com/channel/0029VaKBmL56rsR1L9t3z10n)
- India DPDP Rules were notified 13 Nov 2025. The public-data carve-out is narrow (data made public by the person or under legal obligation); no confirmed B2B outreach exemption. — [Hogan Lovells](https://www.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-), [EY POV](https://www.ey.com/content/dam/ey-unified-site/ey-com/en-in/pdf/2025/11/ey-india-dpdp-act-2023-and-rules-2025-pov.pdf), [PIB document](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)

### Inferences
- Use manual/native LinkedIn search (own account, within ToS) and Sales Navigator alerts rather than scraping tools. Facebook, X, Reddit, Quora, YouTube were not researched; expect low volume and high noise for Indian industrial metals.
- Given DPDP, keep to business role contacts, document legitimate-purpose basis, and honour opt-outs.

### Gaps
- No evidence found on Facebook groups, X, Reddit, Quora, YouTube for Indian metal buyers; no verified WhatsApp/Telegram groups; LinkedIn Sales Navigator pricing not checked.

## (c) Expansion / capex signals

### Takeaway
Primary government and exchange sources are rich, mostly free, and name companies and capacities, but only paid products or scraping give structured feeds. Import-data vendors give importer names; official DGCIS data does not appear to.

### Cited Findings
- PARIVESH (parivesh.nic.in) hosts EAC/SEIAA agendas and minutes, Form-1 documents, and tracking of proposals; crossed 50,000 clearances (Jan 2026). Documents are individual PDFs (e.g. expansions of thermal and cement plants), not a consolidated new-plant list. — [ThePrint](https://theprint.in/india/centres-parivesh-portal-crosses-50000-clearances-milestone/2208864), [PARIVESH sample doc](https://parivesh.nic.in/utildoc/1213242088_1767372079816.pdf), [EC Form-1 manual](https://environmentclearance.nic.in/writereaddata/UserManual/EnvironmentClearanceForm1(Part-AandPart-B).pdf)
- PLI specialty steel: round 1.1 launched Jan 2025 with 42 MoUs with 25 companies; round 1: 19 companies, Rs 27,106 cr committed; round 2: 25 companies, Rs 17,000 cr; Rs 23,022 cr invested and 2.33 Mt produced till Oct 2025; 75 applications received in a round; third round (1.2) reportedly 85 projects with 55 companies. States: AP, Gujarat, Haryana, Jharkhand, Karnataka, Maharashtra, Odisha, Punjab, TN, UP, WB. Company-wise lists are in parliament answers/annexures. — [Ministry of Steel PLI](https://steel.gov.in/pli), [Parliament reply Dec 2025](https://steel.gov.in/sites/default/files/2025-12/lu%20319.pdf), [Free Press Journal](https://www.freepressjournal.in/business/pli-for-specialty-steel-sees-investments-worth-23022-crore-till-october-centre), [SMM](https://news.metal.com/en/newscontent/104044001-india-clears-inr42-billion-in-pli-incentives-specialty-steel-auto-components-among-major-beneficiaries), [Outlook Business](https://www.outlookbusiness.com/news/govt-receives-75-applications-under-pli-scheme-for-specialty-steel-news-224170)
- Industrial parks: MIDC publishes Land Allotment Committee minutes and an Enterprise GIS plot view; GIDC posts allotment advertisements and uses auctions in saturated estates; UPSIDA says available-plot lists are public on its site. No consolidated allottee list found; SIPCOT nothing found. — [MIDC allotment guidelines](https://land.midcindia.org/Images/GuidelinesOnLandAllotment.pdf), [GIDC allotment](https://gidc.gujarat.gov.in/Pages/Contents/allotment%20of%20properties), [UPSIDA SOP](https://eservices.onlineupsida.com/doc/sop_for_industrial_land_allotment.pdf), [CAG UPSIDA audit](https://cag.gov.in/webroot/uploads/download_audit_report/2025/Performance-Audit-Report--UPSIDA-0699820ec843a03.09443929.pdf)
- DRHPs are on SEBI, NSE Emerge and BSE sites; the "Objects of the Issue" section holds capex breakdowns (including plant and machinery); final RHP prevails. — [SEBI sample DRHP](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787804373286.pdf), [NSE Emerge example](https://nsearchives.nseindia.com/emerge/corporates/content/Registration_20022025193950_DRHPFINALMRIL.pdf)
- Exchange announcements: NSE and BSE sell corporate-announcement data as subscription products; one forum report quotes about Rs 3 lakh/year from a vendor for BSE announcement data (unverified). Public JSON endpoints and Apify scrapers exist; exchange terms on scraping were not confirmed. — [NSE corporate data subscription](https://nseindia.com/market-data/corporate-data-subscription), [BSE market data products](https://www.bseindia.com/market_data_products.html?flag=eod), [BSE T&C](https://bseindia.com/static/about/Terms_condition.htm), [TradingQnA thread](https://tradingqna.com/t/corporate-announcement-data-api/178154), [Apify NSE/BSE scraper](https://apify.com/nexgendata/nse-bse-announcements)
- Trade shows: IMTEX Forming 2026 ran 21-25 Jan 2026 (Bengaluru), next 21-27 Jan 2027; METEC India 2026 is 30 Nov-2 Dec 2026 (Mumbai); Zak Aluminium Extrusions Expo listed 10-12 Dec 2026 (New Delhi); Bharat Steel 2026 was 16-17 Apr; Metal Forming Expo 9-11 Apr 2026 (Pune). Exhibitor lists were not confirmed; "Aluminium India" not found as an event. Exhibitors are mostly suppliers/machinery makers, so end-user buyers are better found in visitor/delegate data (not public). — [Construction World on IMTEX](https://www.constructionworld.in/policy-updates-and-economic-news/imtex-forming-2026-to-showcase-global-metal-forming-innovations/82153), [METEC India 2026](https://www.industrialautomationindia.in/events/metec-india-2026), [TradeFairDates](https://www.tradefairdates.com/Trade-Fairs-for-Metal-Working-India-FSL238-L103-S1.html), [Showsbee](https://www.showsbee.com/fairs/86507-IMTEX-India-2026.html), [2exhibitions](https://www.2exhibitions.com/?p=19113)
- Import-export data: Volza and Seair sell India import records (HS code, shipment date, description, port, value, quantity, buyer/supplier names), with marketing claims such as "98 verified buyers" on one narrow HS 7208 slice; Seair says monthly updates. ImportGenius also sells India data with consignee names. No pricing found. — [Volza HSN 7208](https://www.volza.com/p/Wind/import/hsn-code-7208/), [Seair India import data](https://www.seair.co.in/india-import-data.aspx), [ImportGenius India](https://importgenius.com/how-it-works/our-datasets/india)
- Official DGCIS/trade-analytics data is free by HS code/country/port; importer names not shown in sources found; transaction-level DGCIS data is sold on a fee basis. — [Tradestat](https://tradestat.commerce.gov.in/eidb/commodity_wise_import), [Trade Analytics](https://trade-analytics.commerce.gov.in/public/de), [DGCIS fee structure](https://dgciskol.gov.in/data_dissemination_fee_structure.aspx)

### Inferences
- Best-value free stack: PARIVESH agendas (filter steel, aluminium, cement, power, auto, EV) plus exchange announcements and DRHP objects pages plus state park allotment minutes plus PLI annexures. Import vendors turn "who imports HS 7208/7601/7403" into named buyers with quantities, at paid-subscription cost.
- Capex signals precede metal demand by 12-24 months; EC/DRHP give capacity and sometimes equipment spend, from which metal quantity can be estimated.

### Gaps
- PARIVESH bulk/API access and ToS not verified; SIPCOT not found; Volza/Seair/Zauba pricing and Zauba status not found; exhibitor lists not retrieved; BSE/NSE scraping ToS not confirmed; Panjiva India coverage not researched.

## (d) Search patterns and buyer-intent detection

### Takeaway
No source gave tested dorks; the templates below are researcher-constructed and need testing. Intent detection depends on first-person demand language, quantities and delivery terms versus supplier language.

### Cited Findings
- IndiaMART buy leads carry structured intent fields (material, quantity, order value, verified contact tick), which is the clearest ready-made buyer-intent signal found. — [IndiaMART buy lead info](https://help.indiamart.com/knowledge-base/information-in-buy-lead)

### Inferences (constructed templates, untested)
Google dorks:
- `site:linkedin.com/posts ("looking for" OR "requirement" OR "need" OR "RFQ") ("HR coil" OR "aluminium ingot" OR "copper cathode") India`
- `site:linkedin.com/feed/update "urgently required" ("CRC" OR "HR coil" OR "billets") MT`
- `("buy requirement" OR "we are looking for" OR "inquiry") ("copper cathode" OR "aluminium ingot" OR "zinc ingot") India -manufacturer -supplier`
- `site:recycleinme.com buyoffer "per month" MT` and `site:trade.indiamart.com "buyer" "quantity" "aluminium"`
- `filetype:pdf (tender OR RFQ OR "request for quotation") ("HR coil" OR "aluminium") "plant" site:co.in`
- `site:parivesh.nic.in ("steel" OR "aluminium") "expansion" filetype:pdf 2026`
- `site:nseindia.com OR site:bseindia.com "capacity expansion" ("steel" OR "aluminium" OR "copper") 2026`
LinkedIn search strings (own account): `"looking for" AND ("HR coil" OR "aluminium ingot")`, `"RFQ" AND "MT"`, plus job titles "Head Procurement", "Purchase Manager", "GM Procurement" with industry filters (auto components, cables, pipes, appliances).
Intent versus seller markers:
- Buyer: "looking for", "required", "need quotes", "RFQ", "inquiry", monthly or quarterly MT volume, delivery location, payment terms, grade/spec asked, poster is procurement/purchase title at a manufacturer.
- Seller: "available", "ready stock", "offering", "we supply/manufacture", price lists, "DM for rates", trader/stockist titles, many-product catalogues, stock photos.
- Score higher for named plant, specific grade, quantity, deadline, and corroborating capex signal (EC, DRHP, announcement).

### Gaps
- Templates not tested against live results; Google ToS on automated dorking not researched.
