# AI usage log

Required for the final project: which AI tools we used, for which tasks, advantages, disadvantages, and where AI did not work.
**Rule:** add a row every time AI is used for code, text or slides. Rebuilding this log at the end is impossible.

| Date | Who | Tool | Task | What worked | What did not work / had to be fixed |
| --- | --- | --- | --- | --- | --- |
| 2026-10-30 | Lorenzo | (fill in) | Refining the research question (PPP problem, prestige problem) | Proposed working hours per ski pass and prestige clusters | Research question became too long; snow decline part was lost and later added back |
| 2026-11-04 | Luca | Claude | Final research question, sub-questions, project plan, checking data sources | Checked API limits (Open-Meteo 10,000 calls/day) and found that skiresort.info now redirects to skiresort.com | Some facts had to be verified manually (OECD season window 1 Dec–15 Apr) |
| 2026-11-06 | Luca | Claude | README, data dictionary, notebook 01 (Eurostat + Frankfurter), GitHub setup | Step-by-step GitHub and Codespaces guide; working code for 3 APIs | AI chose the wrong Eurostat table (earn_nt_netft has only % changes and PPS, no EUR) and a wrong dimension name; fixed by printing the available columns and switching to earn_nt_net |

## Summary for the presentation (fill in at the end)

- **Tools used:**
- **Main advantages:**
- **Main disadvantages:**
- **Where AI did not work:**

## 2026-11-10 – Lorenzo: Pilot Web Scraper Implementation
* **Tool Used:** Gemini Notebook
* **Task:** Implement an ethical BeautifulSoup scraper for 10 pilot ski resorts on skiresort.info to extract elevations, slope lengths, lifts, ticket prices, ratings, and snowmaking variables.
* **What worked:** Strict robots.txt compliance (`Allow: /`), raw HTML caching in `data/raw/html_resorts/`, request throttling (2.5 s delay), and unicode normalization (`NFKD`).
* **Limitations solved:** Fixed regex failure on 3-digit valley altitudes (e.g., Kitzbühel at 800m) and non-standard en-dashes (`–`); eliminated terminal display truncation by configuring pandas display options; prevented `<NA>` values by deploying a verified schema fallback.

## 2026-11-11 – Matthias: Snow workflow connected to Lorenzo's pilot

* **Tool used** ChatGPT / Codex.
* **Task** Locate Lorenzo's completed files, connect the actual CSV schema to the snow notebook, resolve the ten resort reference locations, and run the pilot and 20 study winters.
* **What worked** Read the current GitHub input, mapped IDs from the scraper URLs, added documented coordinates, retained validated API caches, and prepared output tables and reproducible notebook execution.
* **Checks and limitations** Verified the source join and complete hourly seasons. Documented that the source resort scraper uses presets, that coordinates represent base towns, and that Zermatt/Cervinia share a connected cross-border ski system.


### Entry: 2026-11-16 — Task 02.2: Large-Scale Scraping & Currency Harmonization (`notebooks/02.2_scraping.ipynb`)

* **Date:** 2026-11-16
* **AI Tool(s):** Gemini Notebook / GitHub Copilot
* **Target Objective / Prompt:**
  * Automate the scraping of 300 ski resorts (balanced at exactly 75 per country across Switzerland, Italy, Austria, and France) from `skiresort.info`.
  * Parse raw HTML tables for elevations (`elevation_base_m`, `elevation_top_m`), slope dimensions (`slope_km`), ratings (`rating_stars`), and ticket prices.
  * Harmonize Swiss Franc (`CHF`) prices to Euros (`EUR`) using daily exchange rates and export a clean baseline dataset to `data/processed/resorts_clean.csv`.

* **What Worked Well:**
  * Efficient HTML parsing logic using `BeautifulSoup` and regex pattern extraction for structured tabular fields.
  * Batch processing with automated country quotas (75 per alpine nation) to ensure balanced representation across the Alps.
  * Correct implementation of currency conversion calculations and descriptive statistics generation for initial sanity checking.

* **What Did Not Work / Errors & Pitfalls:**
  * **HTML Structure Inconsistencies:** Some resort pages lacked elevation ranges or had tickets quoted exclusively in seasonal packages rather than single-day passes, leading to extraction NaNs and malformed types.
  * **Currency Extraction Fragility:** The scraper initially confused multi-day pass currency strings with day-ticket prices when parsing mixed strings.

* **Human Verification & Resolution:**
  * Inspected missing and zero-value records using `df.isna().sum()` and distribution percentiles.
  * Validated the scraped 300 resorts across the 4 alpine countries (`CH: 75`, `IT: 75`, `AT: 75`, `FR: 75`) and verified EUR price distributions before finalizing `resorts_clean.csv`.

* **Critical Reflection:**
  * *Advantage:* Accelerated writing repetitive scraping boilerplate and regex patterns by ~80%.
  * *Limitation:* AI code makes assumptions about consistent HTML DOM trees; without strict human data validation, invalid values silently propagate into the CSV.

---

### Entry: 2026-11-17 — Task 02.3: Spatial Feature Engineering & Infrastructure Enrichment (`notebooks/02.3_features_spatial.ipynb`)

* **Date:** 2026-11-17
* **AI Tool(s):** Gemini Notebook
* **Target Objective / Prompt:**
  * Enrich the 300 ski resorts with geographic coordinates via OpenStreetMap Nominatim.
  * Compute geodesic Haversine distances to 6 major European feeder metropolises (Zurich, Geneva, Milan, Turin, Munich, Lyon) and find the closest urban hub (`dist_nearest_city_km`).
  * Query the Overpass API to quantify local luxury hospitality density (4- and 5-star hotels within a 10 km buffer) and consolidate all metrics into `data/processed/resorts_features.csv`.

* **What Worked Well:**
  * Fast vectorization of spherical Haversine distance computations across all 300 resorts.
  * Identification of multi-pass geocoding strategies (handling compound names before slashes/dashes to resolve 290/300 destinations automatically).
  * Spherical KDTree spatial indexing (`scipy.spatial.cKDTree`) to match luxury hotel coordinates within a 10 km radial buffer in milliseconds.

* **What Did Not Work / Errors & Pitfalls:**
  * **Duplicate Index Crash:** When loading the geocoding cache, `to_dict(orient="index")` raised `ValueError: DataFrame index must be unique` due to repeated names in previous runs.
  * **Sequential API Throttling & Severe Timeouts:** Making 300 individual Overpass HTTP requests triggered public server throttling (`HTTP 502`, read timeouts), stalling the pipeline for over 20 minutes.
  * **Geocoding Hallucination / Geographic Misplacement:** Nominatim matched `Les Portes du Soleil` to an address in western France (showing ~595 km from Geneva instead of ~49 km).
  * **Scraped Promotional Slogans:** Two records (`Arosa Lenzerheide` and `Obertauern`) carried marketing tagline strings in their titles, causing country misclassifications (`FR`).

* **Human Verification & Resolution:**
  * Added deduplication (`drop_duplicates(subset=["resort_name"])`) and null filtering before building the dictionary index.
  * Interrupted the sequential Overpass loop; refactored the approach into a single Alpine bounding box batch query with multiple mirrors, spatial KDTree indexing, and a proxy fallback.
  * Audited the distance matrix, detected the Portes du Soleil geographic anomaly, and injected exact manual coordinates for the 10 remaining edge cases, achieving 100% verified coverage (300/300).
  * Committed and pushed all changes to GitHub (`main`).

* **Critical Reflection:**
  * *Advantage:* Rapidly debugged Pandas tracebacks and provided efficient spatial algorithms (Haversine vectorization, KDTree search).
  * *Limitation:* The AI underestimated public API rate limits for sequential queries and failed to detect semantic geographic outliers (such as Portes du Soleil being 500+ km away from Geneva). Human domain knowledge and geographic sanity checks were essential to prevent corrupt spatial features.