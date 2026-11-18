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


### Entry: 2026-11-16 — Task 02.2: Web Scraping & Ticket Price Harmonization (`notebooks/02.2_scraping.ipynb`)

* **Date:** 2026-11-16
* **AI Tool(s):** Gemini Notebook / GitHub Copilot
* **Target Objective / Prompt:**
  * Build an automated web scraper using Python (`requests`, `BeautifulSoup`) to extract data for 300 ski resorts from `skiresort.info` (balanced at exactly 75 resorts per country across Switzerland, Italy, Austria, and France).
  * Parse operational and physical metrics: base and top elevations (`elevation_base_m`, `elevation_top_m`), total slope distance (`slope_km`), lift infrastructure, user test ratings (`rating_stars`), and adult day-pass prices.
  * Harmonize Swiss Franc (`CHF`) prices to Euros (`EUR`) using historical ECB exchange rates and save the structured dataset to `data/processed/resorts_clean.csv`.

* **What Worked Well:**
  * Rapid generation of regular expressions to extract clean numeric values from formatted web strings (e.g., `"SFr. 116,-"` or `"225 km"`).
  * Automated enforcement of country quotas (`75` resorts each) with pagination handling.
  * Rapid generation of descriptive statistics (`describe()`) to verify distribution sanity.

* **What Did Not Work / Errors & Pitfalls:**
  * **HTML Parsing Failures on Incomplete Tables:** Certain resort pages lacked published elevation ranges or listed only multi-day seasonal passes, generating unhandled `NaN` values that broke downstream float type casting.
  * **Ambiguous Ticket Price Captures:** The initial parser occasionally captured youth or multi-day pass rates instead of standard adult single-day ticket prices.

* **Human Verification & Resolution:**
  * Inspected missing values using `df.isna().sum()` and added fallback CSS selectors to locate secondary price tags.
  * Verified national sample balances (75 resorts per country) and checked EUR price distributions before freezing `resorts_clean.csv`.

* **Critical Reflection:**
  * *Advantage:* Reduced DOM parsing and HTTP boilerplate implementation time by approximately 75%.
  * *Limitation:* The AI assumed uniform HTML structures across all destination pages. Strict human verification of distributions was essential to catch silent conversion errors.

---

### Entry: 2026-11-17 — Task 02.3: Spatial Feature Engineering & Luxury Infrastructure (`notebooks/02.3_features_spatial.ipynb`)

* **Date:** 2026-11-17
* **AI Tool(s):** Gemini Notebook
* **Target Objective / Prompt:**
  * Geocode all 300 ski resorts using OpenStreetMap Nominatim.
  * Compute geodesic Haversine distances to 6 major European feeder metropolises (Zurich, Geneva, Milan, Turin, Munich, Lyon) and calculate the shortest distance to a major hub (`dist_nearest_city_km`).
  * Query the OpenStreetMap Overpass API to quantify local luxury hospitality density (4- and 5-star hotels within a 10 km buffer) and export the consolidated dataset to `data/processed/resorts_features.csv`.

* **What Worked Well:**
  * Vectorized spherical Haversine distance computations across all 300 destinations.
  * Spherical KDTree spatial indexing (`scipy.spatial.cKDTree`) to query hotel density within a 10 km radial buffer in milliseconds.

* **What Did Not Work / Errors & Pitfalls:**
  * **Pandas Duplicate Index Exception:** Reloading the geocoding cache with `.to_dict(orient="index")` triggered `ValueError: DataFrame index must be unique` due to duplicate names from previous runs.
  * **API Throttling & 20-Minute Freeze:** Making 300 individual sequential HTTP requests to `overpass-api.de` triggered severe rate limiting (`HTTP 502` and `Read timed out`), freezing the notebook for over 20 minutes at record 50.
  * **Geocoding Hallucination / Spatial Outlier:** Nominatim matched `Les Portes du Soleil` to an address in western France, calculating an anomalous distance of 595 km from Geneva instead of the actual ~49 km.
  * **Scraped Marketing Slogans:** Two records (`Arosa Lenzerheide` and `Obertauern`) carried scraped marketing taglines in their name fields, causing country misclassifications (`FR`).
  * **Chat Filter Masking Backup URLs:** Alternative Overpass mirror links were sanitized in chat as `[suspicious link removed]`, causing URI parse errors.

* **Human Verification & Resolution:**
  * Interrupted the stalled sequential loop; refactored the pipeline into a single Alpine bounding box batch query with multiple mirrors, KDTree radius indexing, and a proxy fallback.
  * Added deduplication (`drop_duplicates(subset=["resort_name"])`) before building dictionary lookups.
  * Identified the Portes du Soleil spatial error through distance matrix cross-checking and injected exact manual coordinates for the 10 unresolved edge cases to reach 100% coverage (300/300).
  * Successfully generated `resorts_features.csv` and committed the changes to GitHub (`main`).

* **Critical Reflection:**
  * *Advantage:* Quickly debugged Pandas tracebacks and provided efficient vectorized algorithms (Haversine, KDTree).
  * *Limitation:* The AI initially suggested naive sequential API calls that did not account for public rate limits and failed to catch the Portes du Soleil geographic anomaly until audited against domain knowledge.

  ## 2026-11-18 – Luca: Repository review against the project requirements

* **Tool used:** Claude
* **Task:** Review the repository against the project requirements and fix documentation errors.
* **What worked:** Found duplicated cross-border resorts, a snow indicator with almost no variation, imputed snow_cannons values and documentation inconsistencies; fixed the Eurostat table name in README and integration log.
* **What did not work:** Claude could not push to GitHub (account not linked), so all changes were made by hand.