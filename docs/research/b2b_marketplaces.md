# India B2B marketplaces, buy-lead platforms and directories for finding raw-metal BUYERS (manufacturers/end users)

Research date 2026-11-25. About 15 tool calls. Many platforms could not be verified in depth (see Gaps). Anything not backed by a URL is labelled as an inference.

## Which platforms show buyer requirement text with quantity?

### Takeaway
ExportersIndia's public buyer page and IndiaMART buy leads expose requirement text and quantity. ExportersIndia shows it openly, with the phone masked. IndiaMART gates contact details behind paid lead consumption. For other platforms (TradeIndia, Alibaba RFQ, Tradewheel, EC21, Global Sources) I confirmed only membership-gated models, not field-level detail.

### Cited Findings
- ExportersIndia public buyer page (fetched 2026-11-25) shows per lead: a headline, a verified icon, city/state, posting date, a one-sentence requirement, buyer name, a masked mobile (e.g. "+91-70******60") and quantity (e.g. "2 Ton", "1000 piece"). Some leads add timing ("Urgent", "Within 2 Weeks"), purchase frequency and payment mode. The "Contact Buyer" button is JavaScript-driven, and the page does not state what full access costs. Sample leads were not metal, so a metal-keyword filter is needed. — [ExportersIndia buyers](https://www.exportersindia.com/buyers/)
- IndiaMART buy leads: before consuming, a seller sees products of interest, what the buyer sells on IndiaMART (if anything), total requirements posted, and member-since date. After consuming, name, phone, email and address (if available) appear. — [IndiaMART help: information in buy lead](https://help.indiamart.com/knowledge-base/information-in-buy-lead)
- IndiaMART advises sellers to check specs, recency, buyer location, order quantity, approximate order value and requirement frequency before consuming a lead, so quantity/value fields exist on leads. — [IndiaMART help: buylead-check](https://help.indiamart.com/knowledge-base/buylead-check)
- IndiaMART buy leads are credit/subscription-based (leads are allocated and can be purchased). A 2012 launch article cites "pay per seen lead" from Rs 50, which is historical. No current rate card was found. — [IndiaMART help: manage buyleads](https://help.indiamart.com/article-categories/selling-on-indiamart/bulead-enquiries/manage-buyleads); [2012 launch](https://corporate.indiamart.com/2012/11/06/b2b-buy-sell-service-for-smes-launched)
- Alibaba RFQ is free for buyers. Sellers need a paid plan with monthly quote quotas (India pricing page). RFQs are reviewed before going live. Alibaba claims more than 20,000 new requests a day (marketing claim). — [Alibaba seller RFQ](https://seller.alibaba.com/rfq); [Alibaba India pricing](https://seller.alibaba.com/in/pricing); [Alibaba RFQ guide](https://seller.alibaba.com/businessblogs/how-to-use-rfq-a-detailed-guide-with-examples-px97m41v)
- Tradewheel offers keyword/category trade alerts for new trade leads, with a paid tier for connecting to buyers. — [Tradewheel learning center](https://www.tradewheel.com/learning-center/)
- EC21 offers trade leads, company directories and catalogs, with free and paid premium membership. — [globaledge EC21](https://globaledge.msu.edu/global-resources/resource/672)
- Global Sources introduced a "Verified Buyer" system in 2011, and its focus is China-sourcing by international buyers. — [Global Sources brochure](https://s.globalsources.com/IMAGES/website/image/corporate/CorporateBrochure_EN.pdf)
- TradeIndia: no official buy-lead page was retrieved. It has a payments FAQ page. One 2022 Trustpilot reviewer calls it low in real leads (single anecdote). — [TradeIndia FAQs](https://www.tradeindia.com/ti-pay/faqs.html); [Trustpilot](https://trustpilot.com/review/tradeindia.com?page=4)
- Moglix is mainly an industrial MRO/fasteners/electricals marketplace. OfBusiness and Power2SME are the sourcing platforms for SME raw-material procurement (steel, TMT, metals). These are buyer-side procurement platforms. They are not lead boards, but their customers are manufacturers. — [Inc42 Moglix](https://inc42.com/startups/moglix-manufacturing-industry-supply-chain-b2b/); [World Bank blog](https://blogs.worldbank.org/en/psd/productive-technology--how-a-startup-revolutionized-indian-b2b-c)
- Udaan is described as wholesale for retailers. No steel/raw-metal vertical was found. — same Moglix/Udaan search; no primary source.

### Inferences
- Best volume of metal buy leads is probably IndiaMART (paid), then ExportersIndia and TradeIndia. Many of these leads will come from traders, so they need classification.
- Alibaba, EC21, Global Sources and Tradewheel are export-oriented. They are weak for domestic Indian end users, though a few Indian buyers post.
- Moglix, Udaan, JustDial and Sulekha are unlikely to give metal buyer requirements. JustDial and Sulekha can still serve as directory lookups for local fabricators (unverified).

### Gaps
- TradeIndia buy-lead field detail, pricing and verification model not retrieved.
- Udaan, JustDial and Sulekha terms/structure not found.
- Current IndiaMART credit prices not found. A seller-account demo is needed.
- BigMint/SteelMint, Metal.com and Kitco are price/news services, not buyer lead sources (see the last section). No buyer directory was found.

## Which show verified phone/email/GST/CIN?

### Takeaway
IndiaMART shows a green-tick for verified mobile and email before purchase, then the full contact after purchase. GST/CIN come from external registries. GST (gst.gov.in), the MCA master data on data.gov.in, Udyam, Tofler/Zauba and TheCompanyCheck are the identity layer.

### Cited Findings
- IndiaMART: green tick against Mobile and Email icons when the buyer's contact is verified, visible before consuming. — [IndiaMART help](https://help.indiamart.com/knowledge-base/information-in-buy-lead)
- ExportersIndia claims buyers are checked for authenticity (own marketing claim, method undisclosed). — [ExportersIndia buyers](https://www.exportersindia.com/buyers/)
- GST public Search Taxpayer works without login, with a captcha. It shows legal name, trade name, registration date, constitution, status and taxpayer type. Searching by PAN lists all registrations. It is an identity check, not due diligence. — [GST tutorial](https://tutorial.gst.gov.in/userguide/taxpayersdashboard/Search_Taxpayer_manual.htm); [Tally](https://tallysolutions.com/gst/gst-pan-search/)
- MCA company master data (OGD) covers about 3.6-3.7M companies. Fields: CIN, name, registration date, RoC, registered address, state, capital, status, class, category, listing status and NIC. It excludes directors, DIN, charges and AGM dates, and is updated monthly. — [data.gov.in RoC-wise master data](https://www.data.gov.in/resource/registrars-companies-roc-wise-company-master-data); [Apify OGD wrapper](https://apify.com/nexgendata/ogd-india-companies-registry)
- NIC on MCA is a declared activity and is often not updated after pivots. — [corpintel NIC guide](https://corpintel.io/guides/nic-industry-codes-explained)
- Zaubacorp is free to browse and lists directors with DIN and a NIC code. It is light for bulk use, and some NIC entries look inconsistent. — [Zaubacorp sample](https://www.zaubacorp.com/company/U45200MH2010PTC203702); [companydata comparison](https://companydata.com/b2b-data-provider-comparisons/india/)
- TheCompanyCheck sells company and director databases (search by name, CIN, DIN; CSV/Excel/API for paid users). — [TheCompanyCheck databases](https://www.thecompanycheck.com/products/databases)
- Tofler builds reports from MCA filings. A third-party Apify scraper exists at $4 per 1,000 records. — [Apify Indian Company Data](https://apify.com/foxlabs/indian-company-data)
- Udyam: the portal has a state-wise product/activity search of MSME units. Data.gov.in/AIKosh carry "List of MSME registered units under Udyam" and district totals. Udyam metadata says records carry NIC-2008 activity. Udyog Aadhaar state datasets (e.g. West Bengal) include unit name, address, investment in plant and machinery, employment and NIC code. Data.gov.in availability varies (one resource last updated 2025-05-07). — [Udyam search](https://udyamregistration.gov.in/searchregistration.aspx); [data.gov.in Udyam list](https://data.gov.in/resource/list-msme-registered-units-under-udyam); [Udyam metadata](https://www.udyamregistration.gov.in/docs/Udyam_Metadata.pdf); [AIKosh WB](https://aikosh.indiaai.gov.in/home/datasets/details/west_bengal_registered_units_under_udyog_aadhaar_memorandum.html)
- Kompass India has per-country conditions and D&B India sells subscriptions (D&B Hoovers, D-U-N-S) under order forms. D&B's Data Cloud is claimed at 595M+ records. — [Kompass India conditions](https://in.kompass.com/l/general-conditions); [D&B India](https://www.dnb.co.in/); [D&B NSIC order form](https://www.dnb.co.in/nsic/files/NSIC-Order-Form.pdf)
- IndiaFilings has an online GST search page. — [IndiaFilings GST search](https://www.indiafilings.com/gst/search)

### Inferences
- A workable pipeline is: lead (name/city/phone) from IndiaMART or ExportersIndia, then GSTIN/legal name match, then MCA OGD (CIN, NIC, address), then Udyam (plant & machinery investment, employees).
- Registry data gives no phone or email for most firms. Phone and email come from marketplace leads, company websites or paid vendors (inference, not verified).

### Gaps
- Contact fields on Tofler, Zauba, IndiaFilings, TheCompanyCheck, Kompass and D&B (phone/email availability) were not verified.
- MCA V3 portal's own data and API access not verified. One site claims no official MCA bulk API.
- Association directories (ACMA, SIAM, IEEMA, FIEO, CII, AIA, state associations): my search returned no usable member-directory pages. Fetch each official site directly.

## Scrapability, ToS, captcha, paywall

### Takeaway
IndiaMART is the most restrictive: ToS bans systematic retrieval, robots.txt blocks many bots, and contacts are paywalled. GST has a captcha. Open government datasets (data.gov.in MCA, Udyam lists, AIKosh) are the lawful bulk route.

### Cited Findings
- IndiaMART ToS (Section VI) bars copying/downloading site content and "systematic retrieval" to compile content, "through robots, spiders, automatic devices or manual processes", without written permission. It also bars mass mailing and resale. It allows termination for unauthorized database access. — [IndiaMART ToU](https://m.indiamart.com/terms-of-use.html)
- IndiaMART robots.txt: User-agent * blocks `/proddetail1`, `/proddetail2`, `/company/view-catalog.html`, `/enquiry.html`, `/*/search.html` and many `/company/` paths. ClaudeBot, Bytespider, Scrapy, AhrefsBot and SemrushBot are fully blocked, and GPTBot and OAI-SearchBot are allowed. Buy-lead pages are not named. — [IndiaMART robots.txt](https://www.indiamart.com/robots.txt)
- Indian law: scraping is not explicitly regulated. Breach of ToS can found a contract claim, and robots.txt is generally non-binding. This is a secondary legal-blog view, not legal advice. — [Lawrato](https://lawrato.com/indian-kanoon/civil-law/is-web-scraping-legal-in-india-what-a-business-can-and-cannot-collect-3192)
- GST taxpayer search uses a captcha. — [GST tutorial](https://tutorial.gst.gov.in/userguide/taxpayersdashboard/Search_Taxpayer_manual.htm)
- MCA OGD is free under the national open data policy, with a monthly snapshot. AIKosh mirrors some datasets under the Open Government License, India. — [data.gov.in](https://www.data.gov.in/resource/registrars-companies-roc-wise-company-master-data); [AIKosh](https://aikosh.indiaai.gov.in/home/datasets/details/company_master_data.html)
- Zaubacorp and Tofler have unofficial paid scraper wrappers (Apify), which is a sign they are scrapable but their ToS were not checked. — [Apify](https://apify.com/foxlabs/indian-company-data)
- BigMint (ex-SteelMint) is paid. An old app listing showed INR 12,500/yr for Indian clients, which may be outdated. Coverage includes non-ferrous (Al, Cu, Zn, Pb, Ni, Sn). — [BigMint FAQ](https://bigmint.co/faqs); [BigMint prices](https://bigmint.co/prices); [App Store](https://apps.apple.com/us/app/id885759135)

### Inferences
- Prefer sanctioned routes: manual seller-panel use of IndiaMART, ExportersIndia and TradeIndia, plus bulk open data, rather than scraping. Check ToS for TradeIndia, ExportersIndia, JustDial and Sulekha before any automated collection.

### Gaps
- ToS/robots for TradeIndia, ExportersIndia, JustDial, Sulekha, Zauba, Tofler and Kompass were not fetched.
- Captcha behaviour on marketplaces not tested.

## Industries, metals and clusters

### Takeaway
Cluster evidence found: Jamnagar (brass), Moradabad (brassware), Rajkot (castings/forgings/brass fasteners), Ludhiana (fasteners), Howrah (foundry/re-rolling), Coimbatore (foundry). Industry-to-metal mapping below is mostly general knowledge, uncited.

### Cited Findings
- Jamnagar: about 80% of India's brass components (electrical, automobile, sanitary), with a stated brass consumption figure that is undated in the excerpt. — [BEE Jamnagar situation analysis](https://beeindia.gov.in/sites/default/files/SituationAnalysis_Jamnagar.pdf)
- Moradabad: roughly 40-50% of India's metal-craft exports originate there. — [ISID WP281](https://isid.org.in/wp-content/uploads/2025/06/WP281.pdf)
- Rajkot: castings and forgings, diesel engines, motors, and a brass-fastener hub. — [RBI cluster list](https://website.rbi.org.in/documents/87730/39016390/56MD29072022_A1.pdf); [Fastener World report](https://fastener-world.com/data/pdf_download/CFW_71_W_123.pdf)
- Ludhiana: an estimated 70% of national fastener production. — [Fastener World report](https://fastener-world.com/data/pdf_download/CFW_71_W_123.pdf)
- Howrah: MSME ministry lists a metal-casting (foundry) cluster and a re-rolling mills cluster. — [DC-MSME 411 clusters](https://dcmsme.gov.in/schemes/411%20clusters.pdf)
- Coimbatore foundry: about 535 units (another source says about 600). Raw materials are pig iron, steel, scrap and foundry returns. — [BEE SIDHIEE foundry](https://sidhiee.beeindia.gov.in/AboutUs/foundry)
- Cluster databases: [BEE SIDHIEE clusters](https://sidhiee.beeindia.gov.in/ClusterDetails), [DC-MSME CFC lists](https://www.dcmsme.gov.in/schemes/On-going%20CFC%20under%20MSE-CDP22032024.pdf), [Gujarat cluster development](https://ic.gujarat.gov.in/cluster-development.aspx).

### Inferences (general industry knowledge, not sourced here)
- Auto components, Pune-Chakan, Chennai and Aurangabad: steel bar/forging steel, aluminium ingots/alloys (die casting), brass and copper (terminals). Forgings: alloy/carbon steel billets. Castings/foundries: pig iron, scrap, ferroalloys, aluminium. Pipes/tubes: HR/CR coil, stainless coil. Fasteners: wire rod, brass rod, stainless wire. Wire and cable: copper and aluminium rods, and transformers: CRGO, copper and aluminium strip/wire. Utensils/cookware (Moradabad, Faridabad, Gujarat): stainless and aluminium sheet and circles. Sanitaryware and Jamnagar brass parts: brass rod/ingot, copper and zinc. Extrusion: aluminium billet. Galvanizers: zinc. Solar structures/EPC: HR steel, GI, aluminium. All of these are inferences and should be confirmed per cluster.

### Gaps
- No cited tonnage by metal per industry. No sources for Pune-Chakan, Chennai, Aurangabad or Faridabad were found.

## Classification: end-user manufacturer vs trader

### Takeaway
No source gave a validated rule set. The signals below are heuristics. Combine several because NIC and trade names are noisy.

### Cited Findings
- MCA/Udyam NIC is a self-declared activity and goes stale. — [corpintel](https://corpintel.io/guides/nic-industry-codes-explained)
- Udyam/Udyog Aadhaar records carry investment in plant & machinery, employment and NIC, which are usable manufacturer signals. — [AIKosh WB Udyog Aadhaar](https://aikosh.indiaai.gov.in/home/datasets/details/west_bengal_registered_units_under_udyog_aadhaar_memorandum.html)
- IndiaMART buy leads show "what the buyer sells on IndiaMART" and past requirements, and a repeat-frequency field. — [IndiaMART help](https://help.indiamart.com/knowledge-base/information-in-buy-lead)
- The GST profile includes the legal and trade name and constitution. — [GST tutorial](https://tutorial.gst.gov.in/userguide/taxpayersdashboard/Search_Taxpayer_manual.htm)

### Inferences (heuristics)
- Manufacturer signals: NIC manufacturing divisions (24 basic metals, 25 fabricated metal, 27 electrical, 28 machinery, 29 auto; NIC 46/47 means trade); an industrial-estate address (GIDC, MIDC, Focal Point, Chakan); Udyam plant and machinery data; the buyer sells finished goods on IndiaMART (not metal); requirement text with grade/spec and recurring monthly quantity; website with machine list, certifications (ISO/IATF), a product catalog of components.
- Trader signals: names with "Traders/Enterprises/Metals/Steel Corporation"; NIC 46xxx; the buyer also lists the same metal for sale; one-off or very large mixed lots; warehouse addresses; many unrelated categories.
- Weak signals: the trade name alone, and GST "trade name" often does not match the plant.

### Gaps
- No empirical accuracy numbers for any heuristic.
