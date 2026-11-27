# Data dictionary

One row per variable. Keep names in `snake_case`, units in the name when useful (`_m`, `_km`, `_eur`).
Status: ✅ defined · 🔄 to be confirmed after the pilot test (step 1, 11 Nov 2026).

#### Table `resorts_features.csv` (`data/processed/resorts_features.csv`) — owner: Lorenzo

**Current scope:** 280 unique source URLs, 70 resorts per country (CH, IT, AT, FR). Values are taken from Skiresort.com listing cards; missing values are retained rather than filled with country averages. The table contains 31 columns.

| Variable | Type | Unit | Source / definition |
| :--- | :--- | :--- | :--- |
| `resort_name` | string | – | Resort name as shown on the source listing. |
| `country` | string | ISO 3166-1 alpha-2 | Analysis country code: `CH`, `IT`, `AT`, or `FR`. Cross-border areas are assigned once using documented slug rules. |
| `url` | string | URL | Canonical Skiresort.com resort page. Unique within this sample. |
| `elevation_base_m` | float | m a.s.l. | Base elevation reported on the listing card. |
| `elevation_top_m` | float | m a.s.l. | Top elevation reported on the listing card. |
| `slope_km` | float | km | Total ski slope length reported on the listing card. |
| `lifts_count` | float | count | Number of ski lifts reported on the listing card. |
| `price_day_raw` | float | source currency | Adult day-ticket price as displayed by the source. |
| `currency` | string | ISO 4217 | Currency of `price_day_raw` (EUR or CHF). |
| `price_day_eur` | float | EUR | EUR price shown by the source. For Swiss resorts this uses the explicitly displayed approximate EUR price when available; it is not converted using a fixed exchange-rate assumption. |
| `rating_stars` | float | stars | Reserved compatibility field. Not supplied in the listing cards used for this extraction; currently missing. |
| `snow_cannons` | float | count | Reserved compatibility field. Not supplied in the listing cards used for this extraction; currently missing. |
| `price_method` | string | – | `source_eur` or `source_approx_eur`, identifying how the EUR price was displayed by the source. |
| `price_imputed` | boolean | – | True only if a price was imputed. No price imputation is performed in this workflow. |
| `manually_added` | boolean | – | True only for manually inserted resorts. No manually inserted resorts are used in this sample. |
| `observed_field_count` | integer | count | Number of non-missing values among base elevation, top elevation, slope length, lift count and raw ticket price. |
| `scrape_source` | string | – | Source listing from which the record was extracted. |
| `source_page` | string | URL | Country listing page used to discover the resort. |
| `source_retrieved_at_utc` | datetime | UTC | Timestamp when the source page was retrieved. |
| `latitude`, `longitude` | float | decimal degrees | WGS84 resort point from the geocoding cache or Nominatim. Check `geocode_source` for provenance. |
| `geocode_source` | string | – | Indicates Nominatim or a legacy cached coordinate. Legacy cache coordinates are explicitly marked as not independently revalidated. |
| `dist_zurich_km` | float | km | Great-circle Haversine distance to Zurich city centre. |
| `dist_geneva_km` | float | km | Great-circle Haversine distance to Geneva city centre. |
| `dist_milan_km` | float | km | Great-circle Haversine distance to Milan city centre. |
| `dist_turin_km` | float | km | Great-circle Haversine distance to Turin city centre. |
| `dist_munich_km` | float | km | Great-circle Haversine distance to Munich city centre. |
| `dist_lyon_km` | float | km | Great-circle Haversine distance to Lyon city centre. |
| `dist_nearest_city_km` | float | km | Minimum of the six city distances above. These are straight-line distances, not road travel distances. |
| `hotels_4_5_star_10km` | integer | count | Number of OSM-mapped 4- and 5-star hotel objects within 10 km of the resort coordinate. This is a point-radius proximity measure, not a resort-boundary count or a verified census of distinct hotel businesses; duplicate OSM representations may remain. |
| `hotel_data_source` | string | – | OpenStreetMap Overpass when a hotel count could be calculated; missing when resort coordinates are unavailable. |

Supporting outputs:
- `resorts_scrape_candidates.csv`: discovered listing candidates before the balanced 70-per-country selection.
- `resorts_geocoded_cache.csv`: geocoding cache, including query/status and available OSM result metadata.
- `hotels_cache.csv`: individual OSM hotel objects (node, way or relation), star tag, coordinates and retrieval timestamp. Counts reflect mapped objects and may include duplicate representations of the same establishment.


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
| `altitude_text`, `facility_type`, `year_built`, `year_closed` | text | – | Legambiente | Free text as written in the report; not cleaned yet ✅ |
| `source_page` | integer | page | Legambiente | PDF page where the entry appears ✅ |
| `lat`, `lon` | float | degrees | Nominatim | Geocoded location 🔄 (next step) |
| `matched` | boolean | – | derived | True if geocoding succeeded 🔄 (next step) |

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
| `resorts` | 300 | `row_id` | `resort_id` → `resort_roster` | Scraped resort features and prices (same columns as `resorts_features.csv`, plus `row_id`, `resort_id`) ✅ |
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
