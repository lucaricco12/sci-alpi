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

## 2026-11-18 – Luca: Legambiente PDF to table (`notebooks/04_legambiente_closures.ipynb`)

* **Tool used:** Claude
* **Task:** Extract the lists of dismissed and temporarily closed ski facilities from the Legambiente report Nevediversa 2026 (359-page PDF) into `data/processed/legambiente_closures.csv`.
* **What worked:** Cutting each page into its three text columns and reading them in order; one row per site, using the `Comune` label as the start of each entry; checking the row count against the PDF and checking that each municipality appears on the cited page (181 of 184 found directly).
* **What did not work:** The page text mixed the three columns, so a first simple extraction scrambled the entries. The word "Comune" also appears inside descriptions, so a plain count of the word was too high (149 instead of 147 for dismissed). Claude could not download the PDF itself (the website blocked the download), so the PDF was downloaded by hand and provided.
* **Human verification:** The report counts lifts (273 dismissed) while our table counts sites (147 + 37); this difference was checked and documented in the integration log.

## 2026-11-22 – Matthias: Matched snow validation and next-step workflow

* **Tool used:** ChatGPT / Codex, with connected GitHub access and Python execution.
* **User task:** Identify and carry out the next steps of Matthias's snow-data/climate work after the 10-resort pilot.
* **Implementation:** Query ERA5-Land at the existing 20 MeteoSwiss station coordinates and elevations; match all 20 study winters at the station observation time (06:00 UTC). Add cached requests, full hourly coverage checks, one-to-one joins, bias/MAE/RMSE, period-change diagnostics, figures, a station/grid map, and a notebook that uses saved results by default.
* **Review work:** Preserve the 300-row resort feature input and export a separate identity/coordinate audit. Document duplicate source URLs, cross-border areas, out-of-scope/suspect coordinates, missing lift counts and source-price gaps. Correct the station-indicator description in the dictionary. Remove the accidentally pasted integration-log table row from `requirements.txt`.
* **Verification:** Run boundary/unit/time/missing-data/join/arithmetic checks, independently recalculate measured counts from the retained MeteoSwiss raw cache, and execute the added notebook in a Jupyter kernel. Inspect generated figures before delivery. The associated PR records the final check outcomes.
* **Limitations requiring group review:** A correlation is not a substitute for agreement; do not calibrate all resorts by subtracting a single pooled bias. The station changes are spatially related, and their nominal Pearson p-value is exploratory. Manual station observations are not a homogenised climate series. Resolve full-sample location quality, Alpine membership and cross-border units before bulk downloading and country/elevation inference. No final price or closure regression is claimed here.

## 2026-11-22 – Matthias: Explain the findings and test the location setting

* **Tool used:** ChatGPT / Codex.
* **User task:** Continue the work and explain it in simpler language.
* **Work:** Test `cell_selection=nearest` against the original land setting on all 20 stations and both existing pilot winters (1995 and 2025), holding the dates, elevation request, variable, units and observation time constant. Preserve the separate 400-case baseline. Check the provider's variable definitions, including its exclusion of snow depth from `isElevationCorrectable`. Prepare an independent measurements-only elevation summary, a before/after chart and a short explanation at the beginning of the notebook.
* **Finding:** In the 40 matched pilot cases, the nearest option reduced mean geographic distance but did not reduce count error. It was not promoted as an improved climate method. Entering an altitude is not evidence that snow has been corrected to that exact height.
* **Additional diagnostic:** Four fixed-grid API requests with downscaling disabled recorded the API's reported elevations. Independently compared the retained raw Davos and Weissfluhjoch responses: their complete hourly model snow-depth sequences are identical in all 20 study winters, despite station elevations of 1,594 m and 2,691 m. This illustrates the height-resolution limitation, without identifying every physical cause of the model's errors.
* **Measured result:** In the selected station records, the below-1,500 m group averaged a 22.25-day loss and the ≥1,500 m group a 6.98-day loss. These are descriptive subgroup means for 11 and 9 Swiss stations, not a four-country result or a causal elevation effect.
* **Limitations:** The small location test does not identify every physical cause of model error or replace the full 20-winter benchmark. The four-country research question remains open; it was not silently narrowed to Switzerland. The original model/observation panels and resort-feature inputs are preserved.

## 2026-11-22 — Matthias: implement on main and prepare expansion

* **User request:** Implement the prepared work directly in the GitHub project.
* **AI assistance:** Merged PR #1, configured new Codespaces, added a saved-data runner and notebook follow-up cells, reviewed flagged source locations and resort identities, screened CERRA against ERA5-Land on matched cases, and prepared direct CDS requests.
* **Evidence and checks:** 33 source pages / 211 access points; 293 unique areas with 18 outside-Alps exclusions; 40 matched cases per candidate; 20 tests, fresh dependency installation and nine offline notebook cells passed. Original team source/price data were preserved.
* **Limits:** 260 resort identities remain individually unreviewed; access points are not certified base elevations; CERRA screening does not validate full-period trends; authenticated CDS retrieval and four-country snow conclusions remain unfinished. Detailed provenance and reproduction are in docs/snow_expansion_status.md.
