# Data dictionary

One row per variable. Keep names in `snake_case`, units in the name when useful (`_m`, `_km`, `_eur`).
Status: ✅ defined · 🔄 to be confirmed after the pilot test (step 1, 11 Nov 2026).

#### Table `resorts_features.csv` (`data/processed/resorts_features.csv`) — owner: Lorenzo (scraping), repaired by Luca in notebook `02.4`
**Status:** ✅ repaired on 28 November 2026 · **293 ski areas** (one row per Skiresort URL; AT 75, IT 74, CH 73, FR 71) · 36 columns · `resorts_clean.csv` holds the first 21 columns (no coordinates, distances, hotels).

The first version had 300 rows with 12 rows added by hand (every number = national median), a fabricated hotel column, an artefact lift count and a lost-coordinate merge. What was wrong and how it was repaired is in `docs/integration_log.md` and in `data/processed/resorts_repair_audit.csv`. The status columns say which variables are verified; **a populated value is not proof of a verified value**.

| Variable | Type | Unit | Source | Description | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `resort_id` | text | – | Skiresort URL | Last part of the Skiresort URL (stable key; names contain invisible characters, never join on names). | ✅ |
| `resort_name` | text | – | skiresort.com | Commercial name. | ✅ |
| `country` | text | ISO 3166-1 | skiresort.com | `CH`, `AT`, `FR`, `IT`; the country of the listing. The 75-per-country quota is **not** kept (it removed real resorts and created cross-border duplicates). | ✅ |
| `country_memberships` | text | – | Matthias's roster | Countries of cross-border systems, separated by `;` (for example `FR;IT`). | ✅ |
| `cross_border` | boolean | – | derived | True if `country_memberships` has more than one country. | ✅ |
| `url` | text | – | skiresort.com | Source page. | ✅ |
| `elevation_base_m`, `elevation_top_m` | integer | m a.s.l. | skiresort.com | Lowest and highest lift station. | ✅ |
| `slope_km` | float | km | skiresort.com | **Slope length.** The first parser took the *ski-routes* figure; this value is only used when `slope_status = reparsed`. | 🔄 until `python src/reparse_skiresort.py` is run |
| `ski_routes_km` | float | km | skiresort.com | Ski routes (all runs including unprepared); filled by the re-parse. | 🔄 |
| `slope_status` | text | – | derived | `unverified_old_parser` or `reparsed`. | ✅ |
| `lifts_count` | integer | count | skiresort.com | Number of lifts; the first version had 12 for every CH and IT row (artefact), now empty until re-parsed. | 🔄 |
| `rating_stars` | float | 1–5 | skiresort.com | Editorial rating. | ✅ |
| `price_day_raw` | float | currency of the listing | skiresort.com | Adult day pass as scraped. | ✅ |
| `currency` | text | – | skiresort.com | `EUR` or `CHF`. | ✅ |
| `price_day_eur` | float | EUR | derived | CHF converted with a fixed 1.05 (a single rate for the group is still to be decided; the 2025 average rate gives +1.6 %). | ✅ |
| `price_source` | text | – | derived | `scraped` (291) or `manual_entry` (2, official price typed by hand). | ✅ |
| `in_alpine_candidate_set` | boolean | – | Matthias's roster | 275 areas in his Alpine candidate set. | ✅ |
| `in_alpine_analysis_set` | boolean | – | derived | **269 areas used for analysis**: candidate set without the 6 areas that are outside the Alps by geography. | ✅ |
| `scope_decision` | text | – | Matthias's roster | His scope decision. | ✅ |
| `alps_review_flag` | text | – | derived | Reason when an area is outside the Alps by geography (Hochficht, Abetone, Lelex-Crozet, Saint-Lary-Soulan, Font-Romeu, Cimone); empty otherwise. | ✅ |
| `latitude`, `longitude` | float | deg (WGS84) | Nominatim + review | Position, joined by `resort_id`. See `coordinate_check` for how reliable it is. | 🔄 |
| `coordinate_method` | text | – | derived | `source_first_listed_lift_access` (Skiresort access point), geocoding method, or `manual_correction_approximate`. | ✅ |
| `coordinate_check` | text | – | derived | `verified_access_point` (compared with the source page), `access_point_within_7km_review`, `manual_correction` (20 approximate corrections), `geocoders_agree_not_independent` (two name-based geocoders agree; **not** independent proof), `two_geocodes_differ_review`, `single_geocode_only`. | ✅ |
| `geocode_difference_km` | float | km | derived | Distance between the two geocoding runs. | ✅ |
| `nearest_other_resort_km` | float | km | derived | Distance to the nearest other resort of the table (isolation screen: every analysis area has one within 40 km). | ✅ |
| `dist_zurich_km`, `dist_geneva_km`, `dist_milan_km`, `dist_turin_km`, `dist_munich_km`, `dist_lyon_km` | float | km | derived | Great-circle distance to the city centre. | ✅ |
| `dist_nearest_city_km` | float | km | derived | Minimum of the six. | ✅ |
| `hotels_4_5_star_10km` | integer | count | OpenStreetMap Overpass | 4- and 5-star hotels within 10 km. **Empty until `python src/fetch_hotels_overpass.py` is run**; the first version was a formula of slope and price, not a count. | 🔄 |
| `hotels_status` | text | – | derived | `not_measured` or `openstreetmap_overpass`. | ✅ |

`data/processed/data_status.json` stores the set of `slope_status` and `hotels_status` values. The notebooks read it and mark every result as **PROVISIONAL** while a variable is unverified. `tests/test_resort_data_integrity.py` checks that the flags match the columns.

Other files of the repair: `resorts_repair_audit.csv` (every removed, changed or flagged item with the reason, columns `item`, `action`, `reason`), `resorts_scraped_before_quota.csv` (original scrape before the quota), `resorts_features_25nov_before_repair.csv` (the faulty version, kept as evidence), `resort_coordinate_verification.csv` (created by `src/verify_resort_coordinates.py`; one row per resort with the distance to the nearest access point of the source page and the status `confirmed` ≤ 5 km, `review` 5–7 km, `mismatch` > 7 km).

*Removed columns: `snow_cannons` (0 for every resort, parsing failure).*

## Table `snow_winters` (one row per resort × winter) — owner: Matthias

| Variable | Type | Unit | Source | Description |
| --- | --- | --- | --- | --- |
| `resort_id` | text | – | key | Link to `resorts` ✅ |
| `winter` | integer | year | – | Year in which the winter ends (1995 = winter 1994/95) ✅ |
| `period` | text | – | derived | `past` (1986–1995) or `recent` (2016–2025) ✅ |
| `snow_days_30cm` | integer | days | Open-Meteo (ERA5-Land) | Days 1 Dec–15 Apr with daily max snow depth ≥ 0.30 m at base elevation ✅ |
| `elev_query_m` | integer | m | – | Elevation sent to the API ✅ |

## Table `country_stats` (one row per country × year) — owner: Luca

| Variable | Type | Unit | Source | Description |
| --- | --- | --- | --- | --- |
| `country` | text | ISO code | Eurostat | CH, IT, AT, FR ✅ |
| `year` | integer | year | Eurostat | Reference year ✅ |
| `pli_eu27` | float | index, EU27 = 100 | Eurostat `prc_ppp_ind` | Price level index, actual individual consumption (A01) ✅ |
| `net_earnings_year_eur` | float | EUR per year | Eurostat `earn_nt_net` | Net earnings, single person without children, 100 % of average wage ✅ |
| `net_earnings_hour_eur` | float | EUR per hour | derived | Annual net earnings / 1,760 hours (assumption: 220 days × 8 h) ✅ |

## Table `fx_rates` (one row per day) — owner: Luca

| Variable | Type | Unit | Source | Description |
| --- | --- | --- | --- | --- |
| `date` | date | – | Frankfurter | ECB reference date ✅ |
| `eur_chf` | float | CHF per 1 EUR | Frankfurter | ECB reference rate ✅ |

## Table `stations` (MeteoSwiss) — owner: Matthias

| Variable | Type | Unit | Source | Description |
| --- | --- | --- | --- | --- |
| `station_id` | text | – | MeteoSwiss | Station abbreviation 🔄 |
| `lat`, `lon`, `elev_m` | float | degrees / m | MeteoSwiss | Station location ✅ |
| `winter`, `snow_days_30cm` | integer | year / days | MeteoSwiss | Winter ending year; days 1 Dec–15 Apr with the 06:00 UTC measurement ≥30 cm. This is a morning reading, whereas the original resort pilot uses a daily maximum. ✅ |

## Table `closures` (Legambiente, Italy) — owner: Luca

| Variable | Type | Unit | Source | Description |
| --- | --- | --- | --- | --- |
| `facility_name` | text | – | Legambiente | Name of the facility or locality, as written in the report ✅ |
| `comune` | text | – | Legambiente | Municipality of the facility ✅ |
| `province` | text | – | Legambiente | Province code (e.g. `TO`, `VCO`); empty for 2 rows ✅ |
| `region` | text | – | Legambiente | Italian region ✅ |
| `status` | text | – | Legambiente | `dismesso` (dismissed) or `chiuso temporaneamente` (temporarily closed) ✅ |
| `altitude_text`, `facility_type`, `year_built`, `year_closed` | text | – | Legambiente | Free text as written in the report. `altitude_text` is parsed to numbers in notebook `08` (lower and upper station; the dot in `3.486 m` is a thousands separator); the others are not cleaned (`year_closed` has entries like "anni '90", "n.d.") ✅ |
| `source_page` | integer | page | Legambiente | PDF page where the entry appears ✅ |
| `latitude`, `longitude`, `geocode_status`, … | float / text | degrees | Nominatim (Matthias) | Not in this table: the municipality-level positions (181 of 184; 3 unresolved) are in `data/processed/legambiente_closure_locations.csv` and the SQL table `checkpoint_closure_locations`. They are approximate (municipality, not the lift) ✅ |

#### Table resorts_features
The single, current description of `resorts_features.csv` is at the top of this file (repaired version of 28 November 2026).

## Matched snow validation — owner: Matthias

All winter counts use 1 December–15 April inclusive. Winter is named by its ending year. Each of 20 stations has ten past and ten recent winters (400 unique station–winter keys). No measured input rows are removed in the model join.

| Output / variable | Unit | Meaning |
| --- | --- | --- |
| `station_model_winters.csv` | one row per station × winter | Validated model seasons, with request URLs and SHA-256 hashes of raw responses. |
| `model_days_06utc` | days/winter | ERA5-Land days with the 06:00 UTC snow-depth reading ≥0.30 m. Primary validation indicator. |
| `model_days_daily_max` | days/winter | Same model season counted using the maximum of all 24 UTC hours each day. Sensitivity indicator; matches the original resort aggregation rule. |
| `model_observed_days`, `model_hours` | days, hours | Complete season length and hourly coverage. |
| `query_elev_m` | m above sea level | Station elevation sent to the API. It is not evidence of snow-depth downscaling to exact point elevation. |
| `grid_lat`, `grid_lon`, `grid_distance_km` | degrees, km | Returned model grid point and its distance from the requested station. |
| `snow_station_validation.csv` | one row per station × winter | One-to-one matched station and model tables. |
| `observed_days_06utc` | snow days/winter | MeteoSwiss `hto000d0` morning readings ≥30 cm. |
| `observed_days` | observed calendar days | Total number of measurement days in the complete season, not a snow-day count. |
| `error_days` | days/winter | `model_days_06utc` minus `observed_days_06utc`. Positive means model overcounting. |
| `daily_max_extra_days` | days/winter | `model_days_daily_max` minus `model_days_06utc`. |
| `snow_validation_metrics.csv` | one row per all/past/recent grouping | Bias, MAE, RMSE (days/winter), descriptive count correlation and model saturation. No pooled p-value treating the 400 records as independent stations. |
| `snow_station_changes.csv` | one row per station | Observed/model period means and losses. Loss = past minus recent; positive means fewer recent snow days. |
| `loss_error_days` | days/winter | Modelled loss minus measured loss. |
| `snow_validation_trend_metrics.csv` | one row for the station panel | Change diagnostics. The Pearson p-value uses 20 station changes and is nominal; spatial dependence is not adjusted. |
| `snow_resort_input_review.csv` | one row per original feature row | Canonical URL slug, original source row and review flags. No automatic deletion or coordinate correction. |
| `outside_alpine_screening_box` | boolean | Outside 43–49° N, 4–17° E. Screening flag only; not a validated Alpine polygon or proof of a wrong location. |

The measured manual series are not certified homogenised climate series. Check site histories and representativeness before long-term attribution or extrapolation beyond this Swiss >1,000 m subset. Methods and source URLs are in `docs/matthias_next_steps.md`.

## Snow expansion follow-up (22 November 2026)

| File | Row unit and key | Meaning |
| --- | --- | --- |
| `resort_location_evidence.csv` | Resort ID × access-point index (211 points, 33 areas) | Listed lift-access coordinates in decimal degrees, source URL, UTC retrieval time, SHA-256 hash, destination and own-region breadcrumb. |
| `resorts_snow_roster.csv` | Canonical source URL (293 areas) | Original/selected coordinates, movement in km, country memberships and cross-border category. Eighteen reviewed non-Alpine areas are excluded from the 275-area candidate set; 260 identities have not been individually reviewed. |
| `station_model_candidates.csv` | Model × station × winter (80 rows) | Complete ERA5-Land/CERRA responses for 20 stations in winters 1995 and 2021, with counts, grid, URL and response hash. |
| `snow_candidate_validation.csv` | Model × station × winter (80 rows) | Candidates matched to measured counts; error is model minus observation, in days. |
| `snow_candidate_metrics.csv` | Model (2 rows) | Matched screening bias, MAE, RMSE and descriptive correlation; not a validation of the 20-winter trend. |
| `snow_model_availability.csv` | Model × probe station × winter (4 probes) | Expected/returned/non-null hours, response unit, URL and hash. `missing_not_zero` means unavailable data. |
| `data/config/resort_scope_decisions.csv` | Resort ID (33 reviewed identities) | Explicit `in_alps` / `outside_alps` decisions and reasons for every originally flagged identity. |
| `data/config/cerra_cds_download_plan.json` | Monthly request | Prepared physical snow-depth requests at 06:00 UTC for pilot and target winters; authenticated download remains untested. |

Roster coordinates marked `source_first_listed_lift_access` are representative source-page points; other coordinates retain `original_geocode_not_rechecked`. The five multi-country systems use `country_for_analysis=cross_border`. `base_elevation_at_point_verified` and `snow_method_validated` remain false. The original feature/price files are preserved.

## Follow-up method check and measured elevation summary

| Output / variable | Unit | Meaning |
| --- | --- | --- |
| `station_model_nearest_pilot.csv` | one row per station × pilot winter | 40 fresh requests using `cell_selection=nearest` for all 20 stations in winters 1995 and 2025. Source URLs and raw-response hashes are retained. |
| `snow_grid_selection_pilot.csv` | one row per station × pilot winter | Identical 40 measured cases joined to the original land-setting and nearest-setting model counts. The two model settings have explicit suffixes. |
| `snow_grid_selection_metrics.csv` | one row per selection option | Descriptive count-error and grid-distance metrics for the 40 pilot cases. These are not ten-winter period means or a replacement for the full validation. |
| `same_grid_point` | boolean | Both settings return the same latitude and longitude, within 1e-6 degree. |
| `absolute_error_change_nearest_minus_land` | days/winter | Absolute count error under nearest minus absolute error under land. Positive means the nearest option is worse for that case. |
| `snow_measured_elevation_summary.csv` | one row per all-station/elevation grouping | Each station's ten-winter measured means are averaged equally across stations. The below-1,500 m group has 11 stations; the ≥1,500 m group has 9. These are descriptive measured results for this Swiss subset. |
| `snow_grid_elevation_examples.csv` | one row per illustrative station | Four fixed-grid diagnostic requests for 1 Jan 2025, using `elevation=nan` to disable downscaling. Contains station elevation, API-reported elevation, their difference, grid coordinates, URL and response hash. These are diagnostic examples, not another climate panel. |

The provider's `isElevationCorrectable` definition excludes snow depth. Changing query elevation therefore does not establish snow at the requested physical height. The base/top pilot is a sensitivity check of requests and returned grid points. The evidence and pinned source revision are in `docs/snow_method_check.md`.

## SQLite database `db/sci_alpi.db` (built by `notebooks/05_sqlite_database.ipynb`) — owner: Luca

| Table | Rows | Primary key | Foreign key | Content |
| --- | ---: | --- | --- | --- |
| `resort_roster` | 293 | `resort_id` | – | One row per ski area (Matthias's roster); cross-border systems have `country_for_analysis = 'cross_border'` ✅ |
| `resorts` | 293 | `resort_id` | `resort_id` → `resort_roster` | Repaired resort features and prices (the columns of `resorts_features.csv`, see the top of this file); notebook `05` rebuilds it from the CSV ✅ |
| `closures` | 184 | `closure_id` | – | Legambiente closed facilities (see table `closures` above) ✅ |
| `country_stats` | 123 | `country`, `year` | – | Price level index and net earnings ✅ |
| `fx_eur_chf_daily` | 4,098 | `date` | – | CHF per 1 EUR ✅ |
| `station_winters` | 400 | `station_id`, `winter` | – | MeteoSwiss measured snow days, 20 stations ✅ |
| `snow_summary_pilot`, `snow_winters_pilot` | 10 / 20 | `resort_id` / `resort_id`, `winter` | none | Pilot snow results for 10 resorts (5 do not match the roster IDs) ✅ |
| `v_latest_earnings` (view) | 4 | – | – | Latest year with net hourly earnings per country ✅ |
| Snow table for all resorts | – | – | – | 🔄 Added when the snow indicator is agreed |

The same schema exists in **PostgreSQL** (database `sci_alpi`, user `sci`, local development only), built by `notebooks/05.2_postgresql_database.ipynb`. Differences to SQLite: `BOOLEAN` flags in `resort_roster`, `DATE` in `fx_eur_chf_daily`, `DOUBLE PRECISION` instead of `REAL`, and two indexes on `resorts` (`resort_id`, `country`). Row counts are identical in both databases. Server setup: `bash src/setup_postgres_codespace.sh` ✅

## Matthias's two checkpoint workflows (25 November 2026)

| File/table | Unit and meaning |
| --- | --- |
| `checkpoint_resorts_24.csv` | Six named source areas per country, fixed before outcomes; reviewed lift-access coordinates, source-listed base height, source URL/hash. Convenience model sample, not a representative resort survey. |
| `model_resort_winters_checkpoint.csv` | 480 area × winter rows; complete hourly ERA5-Land responses, ≥0.30 m counts at 06:00 UTC and daily maxima, returned grid, request URL and raw SHA-256. |
| `model_resort_summary_checkpoint.csv` | 24 old/recent ten-winter means and differences; positive loss means fewer recent snow days. `source_type=unvalidated_era5_land_model`, `risk_class_validated=False`; no validated risk labels. |
| `snow_checkpoint_regression_*.csv` | Measured Swiss elevation OLS and separate country/elevation model demonstrations; coefficients, nominal intervals/p-values, in-sample and five-fold errors, held-out predictions. One difference per site, not one independent row per winter. |
| `snow_checkpoint_station_tests.csv`, `snow_checkpoint_station_uncertainty.csv` | Pearson/Spearman and paired change-error tests use n=20 station summaries. Bootstrap resamples whole stations; spatial dependence and unhomogenised histories remain. |
| `snow_checkpoint_descriptive_statistics.csv`, `snow_checkpoint_anova.csv` | Exploratory distributions and nominal group tests. The three-band measured ANOVA is flagged insufficient because the ≥2,000 m group has one station; the 1,500 m split has 11/9 stations. |
| `legambiente_closure_locations.csv` | All 184 source records retained; 181 municipality/locality matches and 3 unresolved. Decimal-degree coordinates are approximate, not individual lift GPS. Includes search query, aliases, OSM/source URL and response hash. |
| `data/config/closure_query_aliases.csv` | Documented search variants or source-named parent municipalities. Source wording is preserved; mixed municipality records use the explicitly documented first representative municipality. |
| `checkpoint_map_resort_locations.csv`, `checkpoint_map_coverage.csv` | Map overlay for 275 candidates, including the reviewed 24-area sample; coordinate provenance updated for changed points. Other geocodes still require individual review. |
| `pilot_resort_id_crosswalk.csv`, `checkpoint_join_audit.csv` | All 10 pilot IDs resolve to 9 canonical areas; Zermatt/Cervinia remain separate gateways of one connected area. No records lost in documented joins. |
| `alternative_station_coverage_audit.csv` | ECA&D endpoint-coverage screen only, not observations or a daily-completeness validation. No Italian station >1,000 m qualified for both target endpoints in the reviewed catalogue. |

The SQLite additions use `checkpoint_` table names plus `pilot_resort_id_crosswalk`. Original eight team tables are preserved. Model-demonstration rows must not silently become validated risk, causal country effects or climate explanations for prices/closures. Full methods: `docs/matthias_checkpoint_report.md`.

## Result files of Luca's notebooks (28 November 2026)

| File | Notebook | Content |
| --- | --- | --- |
| `sq3_cluster_and_model_results.csv`, `sq3_model_comparison.csv`, `sq3_regression_coefficients.csv` | `07` | K-means groups and OLS models for the price (SQ3), with R², RMSE (5-fold cross-validation), robust standard errors. **PROVISIONAL** while slope length, lifts and hotels are unverified. |
| `sq3_status.json` | `07` | Features used, features excluded because unverified, sample size, seed. |
| `sq5_chi_squared_results.csv` | `08` | One row per chi-squared test of SQ5 (main test A, status test B, sensitivity rows): counts, chi², p-value (also Yates and Fisher), odds ratio with 95 % CI, Cramér's V, smallest expected count. |
| `sq5_status.json` | `08` | States that the risk class is an altitude proxy, not days with snow (**PROVISIONAL**). |
