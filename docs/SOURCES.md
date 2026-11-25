# Where Indian metal buyers are, and how MetalScout uses each source

Summary of `docs/research/` (four research tracks, November 2026, mostly from search-level evidence; see each note for citations and gaps).

| Source | What it gives | MetalScout handling |
|---|---|---|
| **Company websites** (found by web search) | Products, plant, capacity, emails, phones, GSTIN/CIN | **Automated**: discover → browser profile |
| **GeM** (bidplus.gem.gov.in) | Bid no., **quantity**, buyer ministry/office, dates; contacts are in the bid PDF | Search hits become buyer signals; bulk lists via `import` CSV |
| **CPPP** (eprocure.gov.in), state GePNIC portals, Gujarat nProcure, Karnataka KPPP, defproc | Tender title, value, dates; CAPTCHA on search | **Manual export → `import`**. No CAPTCHA bypass |
| IREPS (railways) | Login needed | Manual |
| PSU portals: SAIL, BHEL, NTPC, Coal India | Tender lists | Search hits become buyer signals; manual export |
| Tender aggregators: TenderDetail, BidAssist, Tender247, TendersOnTime | Listings; contacts usually paywalled | Search hits become buyer signals (opened if public) |
| **ExportersIndia** buy leads | Requirement text + **quantity**, buyer city; phone masked | Buyer signal, opened |
| TradeIndia | Buy leads | Buyer signal, opened |
| **IndiaMART** | Buy leads (paid to unlock); its terms forbid spiders | **Restricted**: snippet only, never opened |
| LinkedIn / Facebook / X / Instagram | "Looking for supplier of…" posts; LinkedIn litigates scrapers | **Restricted**: snippet only |
| Private procurement (Tata Steel, Reliance, Adani via SAP Ariba) | Supplier registration gates, not buyer lists | Shows up as `VENDOR_PAGE` on company profiles |
| mjunction, MSTC, Recycleinme | E-auctions (mostly sell-side) and buy offers | Buyer signal |
| Capex signals: PLI specialty-steel beneficiaries, PARIVESH clearances, MIDC/GIDC allotments, SEBI DRHPs | Who is building capacity | Manual research → `add`/`import` (see ROADMAP) |
| Trade shows: METEC India, Zak Aluminium Extrusions Expo, IMTEX | Exhibitor lists = manufacturers | Manual export → `import` |
| Import data: Volza, Seair (paid); DGCIS (free, no names) | Who imports your metal | Paid; `import` if you buy it |
| Registries: MCA master data (data.gov.in), GST search (CAPTCHA), Udyam, DGFT IEC | Verify a number you already have | Numbers are read off the site; verification is manual |

## Industrial clusters (default search grid)
Rajkot (castings, forgings, brass fasteners) · Jamnagar (about 80% of India's brass components) · Ludhiana (about 70% of fasteners) · Coimbatore (500+ foundries) · Howrah (foundries, re-rolling) · Moradabad (metal-ware) · Pune-Chakan, Chennai, Hosur, Aurangabad, Faridabad, Gurugram (auto components) · Ahmedabad, Kolkata.

## Industry → metal (default mapping, uncited general knowledge)
Forging/auto: alloy and carbon steel bars, billets · Foundry: pig iron, scrap, ferro alloys, aluminium ingot (ADC12, LM6) · Wire & cable: copper rod/cathode, EC-grade aluminium · Transformers: CRGO, copper, aluminium · Pipes & tubes: HR coil, stainless · Fasteners: wire rod · Utensils: stainless coils, aluminium circles · Extrusion: aluminium billet · Galvanizing: zinc ingot · Brass parts: brass scrap/ingot, copper, zinc.
