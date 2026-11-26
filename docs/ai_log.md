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

## 2026-11-24 – Luca: SQLite database and SQL queries (`notebooks/05_sqlite_database.ipynb`)

* **Tool used:** Claude (connected to the GitHub repository)
* **Task:** Build the SQLite database `db/sci_alpi.db` from the existing CSV files and answer project questions with SQL queries run from Python (`JOIN`, `LEFT JOIN`, `GROUP BY`, `HAVING`, `WITH`, a view).
* **What worked:** Creating the tables with primary keys, foreign keys and `CHECK` rules before loading; comparing the row count of each CSV file with its table; recomputing SQL results with pandas; the SQL snow result reproduced Matthias's published values (55.3 to 33.1 and 106.5 to 99.5 days).
* **What did not work:** The pair (`resort_id`, `country`) is not unique in `resorts` (two repeats within one country), so a surrogate key `row_id` was used. Five of the ten pilot snow resorts do not match any roster ID, so no foreign key is possible for the pilot tables. PostgreSQL was not tested, because there is no PostgreSQL server in the AI workspace.
* **Human verification:** Luca ran the notebook with Run All in his own Codespace on 2026-11-24 (Python 3.14.2). All cells ran, the check cell printed "All checks passed.", and no rows were lost in any table.

## 2026-11-24 – Luca: PostgreSQL database and SQL queries (`notebooks/05.2_postgresql_database.ipynb`)

* **Tool used:** Claude (connected to the GitHub repository)
* **Task:** Repeat the database of notebook 05 in PostgreSQL (extra points: PostgreSQL with joins and aggregations from Python) and write the setup script `src/setup_postgres_codespace.sh` for the Codespace.
* **What worked:** Testing the notebook on a real PostgreSQL 16 server in the AI workspace; adapting the SQL syntax (`STRING_AGG`, `FILTER`, `::numeric` for `ROUND`); the results are identical to SQLite and the row counts match in all 8 tables; two PostgreSQL-only queries (window function `RANK() OVER`, median with `percentile_cont`).
* **What did not work:** The first run failed with an encoding error, because the test server used ASCII and the resort names contain long dashes. Fixed by creating the database with UTF-8 and setting `client_encoding` in the connection. The `apt-get install` part of the setup script could not be tested in the AI workspace, only in the Codespace.
* **Human verification:** To be completed by Luca: run the setup script in the Codespace, run the notebook with Run All, check that "All checks passed." is printed.

## 2026-11-24 – Luca: Affordability matrix, ANOVA and correlations (`notebooks/05.3_affordability_and_tests.ipynb`)

* **Tool used:** Claude (connected to the GitHub repository)
* **Task:** Step 4 of the plan, the part that does not depend on the snow data: hours of work per day pass for every origin and destination country (SQ4), one-way ANOVA of day-pass prices by country, and correlations of the price with resort features, each test with a p-value.
* **What worked:** The data come from the SQLite database with SQL (`CROSS JOIN`, `WITH`, the view `v_latest_earnings`); the F statistic and eta squared were recomputed by hand; the diagonal of the matrix equals the result of notebook 05; the matrix was checked with the median price instead of the mean.
* **What did not work / limits:** The variances of the countries are unequal (Levene p < 0.001), so the Welch ANOVA and Kruskal-Wallis were added; the earnings are nominal and not corrected for price levels. The chi-squared test (SQ5) and the ANOVA of snow loss were not done, because there is no valid snow-risk class for all resorts and the Legambiente sites are not geocoded yet.
* **Human verification:** To be completed by Luca: run the notebook with Run All, check that "All checks passed." is printed, and read the interpretation under the matrix, the ANOVA and the correlation table.

## 2026-11-25 — Matthias: finish both checkpoints today

* **User request:** Complete the November 25 exploration/map and December 2 climate regression/model–station checkpoints now, in the existing GitHub project.
* **Context used:** Original group plan and Luca's shared task summary updated November 24. User confirmed no Copernicus account had been configured.
* **Work:** Added source-checked 24-area model demonstration, full 480-winter panel, measured Swiss elevation regression, country/elevation interactions with five-fold checks, station-level Pearson/Spearman/change-error tests, EDA, standalone Folium map, ID crosswalk and qualified SQLite handover. No messages were sent to teammates.
* **What needed correction:** Nominatim JSONv2 uses `category`, not `class`; initial false unresolved matches were corrected and tested. A generated colour legend introduced a remote D3 dependency; the offline dependency check caught it and it was replaced by an HTML legend.
* **Checks:** All 480 new raw responses matched their hashes/counts; 33 tests and nine notebook cells passed. Plots reviewed; original eight database tables independently compared and unchanged.
* **Interpretation limits:** Real measured claims remain a selected Swiss subset. The 24-area model sample is not the original full-resort analysis and is not validated for risk labels or country climate effects. Three closure locations remain unresolved. New country models, data checks and maps are implemented; reliable all-resort scientific conclusions still need appropriate snow data and further location review.

## 2026-11-25 — Matthias: prepare the correct CERRA-Land test

* **Tool used:** ChatGPT Codex, official ECMWF/CDS documentation and public catalogue/form/constraints.
* **User request:** Check which parts of the shared CERRA-Land instructions were already completed, continue in English and prepare the remaining work within the project.
* **Work:** Distinguished the existing ordinary-CERRA plan from CERRA-Land; retained dated public metadata snapshots and hashes; checked all 100 original-period monthly requests; added a private interactive token setup, a one-field recent-file probe, streaming GRIB checks and optional same-winter comparison against all 20 measured stations and ERA5-Land.
* **Corrections:** CERRA-Land snow is forecast output: 09 UTC + 3 hours is noon; 03 UTC + 3 hours matches 06 UTC measurements. The current form exposes no area subset. Current metadata includes 2025, despite older guide text ending in 2021. A documented recent 12-bit packing issue must be checked, not assumed resolved from its promised correction date.
* **Checks:** 49 tests passed, including synthetic regular-grid and Lambert-grid GRIB round trips, actual low-precision/missing/duplicate-field rejection, calendar/UTC rules and private credential permissions. Default plan and status ran with HTTP blocked. These synthetic files are tests, not snow observations.
* **What needed correction:** Python file buffering initially left the descriptor beyond the GRIB header read by ecCodes. Unbuffered reading fixed this; real GRIB round-trip tests verify it.
* **Still pending:** The account owner must create/sign into CDS, accept the CERRA-Land licence and configure the token privately. No authenticated CERRA-Land snow file was retrieved here. No CERRA-Land accuracy or resort risk is claimed, and published results/database tables were preserved.

## 2026-11-25 — Matthias: make CDS setup and failures actionable

* **Tool used:** ChatGPT Codex; official CDS account/licence instructions and installed ECMWF client source.
* **Issue:** The single generic download error did not distinguish rejected credentials, an unaccepted dataset licence, an invalid selection or a service failure. The setup also needed a supported way to replace a changed key and clearer guidance about hidden input versus the shell prompt.
* **Changes:** Added `setup_cds.py --replace` with atomic owner-only replacement, preservation on invalid input, and symlink protection. Added fixed error messages based on HTTP status and licence indicators. Provider exception strings and response bodies are not echoed; only allowlisted selection-field names can appear. Clarified key-entry and recovery instructions.
* **Validation:** All 58 tests passed. New tests cover replacement permissions/preservation, symlink handling, HTTP 401/403 distinction, rate/service/transport failures, secret-free diagnostics and preservation of published files after a simulated failed download.
* **Limits:** The user must complete licence acceptance in the browser and enter their current key privately. No live account diagnosis, authenticated download or CERRA-Land snow result is claimed by these tests.

## 2026-11-25 — Matthias: correct CDS credential-file quoting

* **Tool used:** ChatGPT Codex and the installed official CDS API parser/credential resolver.
* **Bug found:** The earlier setup wrote `json.dumps(token)` into the key field. CDS uses a simple key/value reader and retains those literal quotes, so even a correct token can be sent with extra characters and rejected with HTTP 401. Previous local tests mistakenly expected that quoted representation instead of checking compatibility with the provider reader.
* **Correction:** Fresh and replacement configurations now write the unquoted value. Added non-interactive `--repair` for old private files, preserving other settings and rejecting malformed, ambiguous or linked configurations. New input cannot silently save literal surrounding quotes. No private key is displayed or included in the repository.
* **Validation:** All 65 tests passed. New tests reproduce the original misread and verify fresh setup, replacement and legacy repair with the real `cdsapi.api.read_config` and `get_url_key_verify` functions, with HTTP blocked. Repair also preserves other fields, is idempotent and keeps owner-only permissions.
* **Limits:** The format defect is reproduced and fixed. A live download still needs a retry in the account owner's Codespace; token validity, licence acceptance and CERRA-Land accuracy are not established by local configuration tests.

## 2026-11-26 — Matthias: diagnose the first monthly CERRA-Land rejection

* **Evidence:** The user's one-field probe passed file checks. The full-winter run reused it, then returned HTTP 400 for December 2024. The old wrapper hid the provider's reason and over-specifically called every HTTP 400 a selection failure.
* **Checks:** Current public form/constraints still permit the requested dates and time/lead. Anonymous provider costing returned 31 fields against a 90,000-field limit; one-day/noon controls were also below the limit. This is not proof that the archive can fulfil the retrieval. No user credential was used for these checks.
* **Change:** HTTP 400/422 can now show a bounded, redacted provider reason and uses neutral request-or-retrieval wording. The account key available to the client is used only for redaction; raw exceptions, private fields and signed URLs are not emitted. The same monthly request, scientific periods and measurement time remain unchanged.
* **Validation/limits:** 68 tests passed, including known-secret, nested-field, URL, identifier and plain-text redaction checks. Published snow tables/database are untouched. Exact cause and an authenticated monthly retry remain pending the user's provider error details; no unsupported download fix or model validation is claimed.

## 2026-11-26 — Matthias: retain the backend traceback and inspect existing failure

* **Finding:** The next error only showed `The job has been rejected`. The official SDK's error formatter explicitly uses separate `title`, `traceback` and `detail` fields; our first redacted summary retained only the generic detail. That diagnostic omission is corrected without assuming the monthly failure's cause.
* **Changes:** Preserve all useful error fields and the tail of long traces. Added read-only `--last-error`, which inspects existing failed CERRA-Land jobs and prints redacted recent logs/error. It handles HTTP errors and the official `ProcessingFailedError` without submitting or downloading another job.
* **Validation/limits:** 75 tests passed, including generic-detail-plus-traceback, trailing cause preservation, redacted server logs, SDK processing failure and assertions that submission/download methods are not called. The user's actual backend traceback is still needed; monthly settings and scientific results remain unchanged.


# AI Usage Log

---

### Entry: 2026-11-16 — Task 02.2: Data Harmonization & Quota Enforcement (`notebooks/02.2_scraping.ipynb`)

* **Date:** 2026-11-16
* **AI Tool(s):** Gemini Notebook
* **Target Objective:** Clean scraped ski resort data, harmonize currencies to EUR, impute missing adult ticket prices, and resolve cross-border resort overlap while strictly maintaining 75 resorts per country.
* **What Worked Well:** Automated parsing of structural slope metrics and country sample balancing.
* **Errors & Pitfalls:** Cross-border resort overlap (`La Thuile / La Rosière` and `Ischgl / Samnaun`) caused national quota imbalances.
* **Human Verification & Resolution:** Implemented 1:1 resort replacements (`Pila – Aosta` for IT, `Scuol – Motta Naluns` for CH) to lock national sample sizes at 75 resorts each (300 total). Imputed verified official 1-day adult pass prices for Alta Badia (€74.00) and Galtür (€56.50).

---

### Entry: 2026-11-17 — Task 02.3: Geocoding & Spatial Proximity (`notebooks/02.3_features_spatial.ipynb`)

* **Date:** 2026-11-17
* **AI Tool(s):** Gemini Notebook
* **Target Objective:** Geocode 300 resorts, compute geodesic distance matrices to 6 urban centers, and aggregate luxury hospitality density within 10 km.
* **What Worked Well:** Vectorized Haversine spherical distance calculations for urban proximity metrics.
* **Errors & Pitfalls:** Automated OSM Nominatim geocoding misplaced La Rosière near southwestern France.
* **Human Verification & Resolution:** Manually overridden La Rosière coordinates to Savoy, French Alps (45.6267° N, 6.8489° E) and verified all distance calculations.
