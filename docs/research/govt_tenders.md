# Indian government and PSU tender sources for raw-metal procurement

Research depth note: about 15 tool calls. Many official portals could not be fetched or verified directly. Several claims come from search-result summaries or third-party pages and are flagged. Nothing here was tested against live portals.

## Which portals exist, how to access them, and what is free

### Takeaway
Most public-sector metal buying sits on a handful of platforms: GeM, CPPP (NIC GePNIC), state GePNIC portals, MoD's defproc.gov.in, IREPS, and PSU-specific portals. Listings are generally free to view, but gated by captchas, and sometimes by login. Some PSU tenders migrate to GeM.

### Cited Findings
- GeM bid pages (bidplus.gem.gov.in) show bid number (GEM/YEAR/B/number), status, quantity, start/end/opening dates, and Ministry/Department/Organisation/Office. Bid end dates are often extended. — [IIT Kanpur GeM bid PDFs](https://iitk.ac.in/data/tender/file/Ext-GeM-Bid-Finalization-8138878-21-10-26.pdf); search summary of bid pages
- The CPPP site mirrors GeM bids as a public table (start date, end date, bid number with total quantity, product category, organisation, department). It has a keyword search and an image captcha. Quantity is combined with the bid number. — [eprocure.gov.in GeM listing](https://eprocure.gov.in/cppp/gemtender?page=50)
- bidplus.gem.gov.in robots.txt disallows only `/resources/` and three `/bg_emd/epbgservice/` endpoints (summarised by fetch tool). eprocure.gov.in/robots.txt returned 404. — [GeM robots.txt](https://bidplus.gem.gov.in/robots.txt)
- GeM Global Tender Enquiries are on a separate surface (bidplus-global.gem.gov.in). — [Apify GeM Global scraper](https://apify.com/automation-lab/gem-global-tender-scraper.md)
- CPPP (eprocure.gov.in) hosts GePNIC, which is also used by state governments. It is being rolled out across 31 states/UTs. — [CPPP annual report 2022-23](https://eprocure.gov.in/cppp/sites/default/files/eproc/Annualreports/Annual_Report_2022_23.pdf); [search summary of state adoption](https://eprocure.gov.in/cppp/sites/default/files/brochure/GePNIC_Brochure.pdf)
- State platforms: Maharashtra adopted GePNIC in 2010. Tamil Nadu, Rajasthan, West Bengal, Punjab, Kerala, Odisha, Haryana and others are listed as GePNIC. Gujarat uses nProcure; Karnataka uses KPPP; Andhra Pradesh and Telangana use their own eGP systems. UP was not confirmed in results. — [BidEasy portal list, via search summary](https://tenders.infralens.in/portals) (third-party and undated)
- MoD portal: defproc.gov.in/nicgep/app. Public menu items include Active Tenders, Tenders by Closing Date, Corrigendum, Results of Tenders, Tenders by Location and Archive. — [defproc screen-reader page](https://www.defproc.gov.in/nicgep/app); [India.gov.in entry](https://www.india.gov.in/defence-eprocurement-portal)
- Defence procurement moved off eprocure.gov.in to defproc.gov.in after April 2019. — [Indian Embassy Berlin notice](https://indianembassyberlin.gov.in/Announcement?id=NTc1)
- IREPS: guides say login is needed to view tenders on the official portal; some zones publish PDF lists of live tenders. Helpline numbers are listed on aggregator pages. — [TendersPlus IREPS login guide](https://tendersplus.com/blogs/ireps-login-process); [PLW tender list PDF](https://plw.indianrailways.gov.in/uploads/list%20of%20published%20tenders(1).pdf)
- PSU portals (from search results, not verified by visiting): SAIL https://sailtenders.co.in/ ; BHEL https://tenders.bhel.com and eprocurebhel.co.in ; NTPC https://ntpctender.ntpc.co.in ; Coal India https://coalindiatenders.nic.in . — [Ministry of Steel PSU page](https://steel.gov.in/psu); [BHEL tenders](https://tenders.bhel.com)
- GAIL, ONGC, BEL, HAL, AWEIL, MIL portal URLs were not found in my searches. Unverified.
- MSTC runs scrap and ferrous/non-ferrous e-auctions at www.mstcecommerce.com. It is a Mini Ratna Cat-I PSU under the Ministry of Steel. Lot catalogues list "FERROUS SCRAP" and require inspection. — [MSTC](https://mstcindia.co.in/content/tender_auction_services.aspx); [IBM auction catalogue](https://ibm.gov.in/writereaddata/files/174247388267dc0a9ae3f17Lot_No_39_Auction_Catalogue.pdf)
- Some BHEL tenders require submission through GeM only. — search summary of BHEL notices; [BHEL tenders](https://tenders.bhel.com)

### Inferences
- Metal buyers that want a broad view should treat GeM plus CPPP/GePNIC as the core, then add SAIL, NTPC, Coal India, BHEL, MSTC and defproc individually.
- Metal-specific demand may also appear as GeM catalogue purchases (direct purchase or reverse auction) that never show as a tender listing. This was not verified.

### Gaps
- Official URLs for GAIL, ONGC, BEL, HAL, AWEIL and MIL were not found.
- UP, Gujarat and Maharashtra portal URLs were not directly verified (maharashtra: mahatenders.gov.in is recalled from general knowledge, unverified).
- Whether IREPS public pages expose tender lists without login was not confirmed beyond guides.
- GeM's own Terms of Use text could not be retrieved.

## Aggregators: free vs paid, and what they show

### Takeaway
Aggregators show tender ID, title, closing date, value and state publicly, but generally hide buyer name, contact details and documents behind subscription or sign-in.

### Cited Findings
- TenderDetail PSU listing publicly shows tender ID, title (sometimes with quantity), status, closing date, estimated value, sector label, document tags and state. It does not show a named buyer or contact on the listing page; login, subscription and "request sample" are offered. — [TenderDetail PSU listing](https://www.tenderdetail.com/tenders/ownership/boards-undertakings-psu/91)
- BidAssist tender pages show "Unlock the tender details for free", so details and contact sit behind registration. — [BidAssist example](https://bidassist.com/assam-tenders/northeast-frontier-railway/detail-cf92631e-cc22-4f38-9313-d41d81a9c410/amp)
- BidEasy (tenders.infralens.in) claims free search across 250+ portals but requires free sign-in. — [BidEasy](https://tenders.infralens.in/portals)
- TendersOnTime sells subscription plans. BidDetail offers a free trial keyed on keywords. — [TendersOnTime](https://www.tendersontime.com/how-it-works/); [BidDetail](https://www.biddetail.com/free-tenders)
- Tender247 and TenderWatch: no reliable pricing or field information found.
- TendersPlus and Tata NexArc also list IREPS tenders. — [TendersPlus](https://tendersplus.com/ireps-tenders/active); [Tata NexArc](https://www.tatanexarc.com/t/india-state-tenders/ireps-tenders/)

### Inferences
- Aggregators likely suit alerting on keywords, but are poor sources of buyer contact data. Contact details come from the original NIT/tender document.

### Gaps
- Free-tier limits of Tender247, TenderWatch, TenderDetail not found.

## Buyer contact details and quantities

### Takeaway
Contact name and address appear in GePNIC tender data per the Apify actor; quantity is usually in the title, in the BOQ, or (on GeM) a dedicated field. Email and phone mostly live in the tender document.

### Cited Findings
- A GePNIC (CPPP/state/defence) scraper outputs: source portal, tender ID, title, organisation and department, tender type, category, product category, estimated value, EMD, published date, bid end, bid opening date, location, contact name, contact address, document URL, status. No quantity field. — [Apify CPPP scraper](https://apify.com/jungle_synthesizer/india-eprocure-tender-scraper)
- GeM listing and bid pages expose quantity; the buyer is shown as ministry/department/organisation/office. No contact email or phone seen in the retrieved examples. — [IIT Kanpur GeM PDFs](https://iitk.ac.in/data/tender/file/Ext-GeM-Bid-Finalization-8138878-21-10-26.pdf)
- MSTC catalogues give an inspection contact. — [IBM catalogue](https://ibm.gov.in/writereaddata/files/174247388267dc0a9ae3f17Lot_No_39_Auction_Catalogue.pdf)

### Inferences
- For lead generation, GeM gives quantity and buyer organisation; GePNIC gives contact name and address; email/phone requires opening the NIT PDF.

### Gaps
- No evidence found of buyer email/phone as structured fields on any portal.

## Open data, RSS and API feeds

### Takeaway
I found no official OCDS feed, RSS or public API for Indian central tenders. Third-party scrapers fill the gap.

### Cited Findings
- No official OCDS or API found on data.gov.in or CPPP in search. — search summary; see [OCP India page](https://www.open-contracting.org/country/india/)
- CivicDataLab converted Himachal Pradesh health procurement to OCDS by scraping; no longer updated. — [OCDS registry](https://data.open-contracting.org/en/publication/77); [GitHub](https://github.com/CivicDataLab/himachal-pradesh-health-procurement-OCDS)
- World Bank's Open Government Contracts Platform reportedly shows India tenders near real time; API details not found. — [OGP](https://www.opengovpartnership.org/?p=3584)
- Third-party tools: [switchr24/mcp-india-tenders](https://github.com/switchr24/mcp-india-tenders) (MIT; CPPP, eProc Rajasthan, defproc; 4 commits, 2 stars, GeM only planned; unclear captcha handling); Apify actors [CPPP scraper](https://apify.com/jungle_synthesizer/india-eprocure-tender-scraper) (CPPP, IOCL, Maharashtra, UP, TN, MP, WB, Jharkhand, Defence; from about $2 per 1,000 records), [foxlabs](https://apify.com/foxlabs/india-government-tenders), [nexgendata](https://apify.com/nexgendata/gem-tenders-india).
- Conflicting reports on CPPP: one actor says its org-based listing needs no captcha; another says the CPPP list is now encrypted and captcha-gated. — [jungle_synthesizer](https://apify.com/jungle_synthesizer/india-eprocure-tender-scraper) vs [nexgendata](https://apify.com/nexgendata/gem-tenders-india)

### Inferences
- Treat scraper availability as fragile. Do not plan on captcha bypass; use official alerts, manual exports or licensed aggregators where captchas exist.

### Gaps
- Whether GeM has an official data API (it has a seller/buyer API for registered users in general knowledge, not verified here).

## Legal, robots and ToS constraints

### Takeaway
GeM's robots.txt is permissive for listing pages, but ToS text was not retrieved. Captchas indicate the operators do not intend bulk automated access.

### Cited Findings
- GeM robots.txt blocks only a few paths (see above). — [GeM robots.txt](https://bidplus.gem.gov.in/robots.txt)
- No GeM clause specifically banning scraping was found; GeM Terms of Use at https://gem.gov.in/termsCondition not read. — search summary; [GeM GTC](https://assets-bg.gem.gov.in/resources/pdf/GTC_on_GeM_v1.10_31Jan19.pdf)
- Apify CPPP actor says it uses short delays to respect NIC server limits. — [Apify](https://apify.com/jungle_synthesizer/india-eprocure-tender-scraper)

### Inferences
- Tender notices are public by policy, but aggregator content has its own ToS. Re-using personal contact data raises DPDP Act 2023 questions (general knowledge, not researched here).

### Gaps
- ToS/robots for IREPS, defproc, state portals and aggregators were not read.

## Example search keywords
Not sourced from a single page; suggested from product categories seen in listings: "MS plate", "HR coil", "CR sheet", "TMT bar", "structural steel", "SS 304 sheet", "aluminium ingot/busbar", "copper cathode / wire rod / strip", "zinc ingot", "brass rod / ingot", "nickel", "ferro manganese / silico manganese / ferro silicon", "pig iron", "ferrous scrap / MS scrap" (the last for MSTC/e-auction, which is sell-side).
