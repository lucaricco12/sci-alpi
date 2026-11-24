# Data dictionary

One row per variable. Keep names in `snake_case`, units in the name when useful (`_m`, `_km`, `_eur`).
Status: ✅ defined · 🔄 to be confirmed after the pilot test (step 1, 11 Nov 2026).

## Table `resorts` (one row per ski resort) — owner: Lorenzo

| Variable | Type | Unit | Source | Description |
| --- | --- | --- | --- | --- |
| `resort_id` | text | – | skiresort.com URL slug | Unique key, e.g. `zermatt-breuil-cervinia-valtournenche-matterhorn` ✅ |
| `name` | text | – | skiresort.com | Resort name ✅ |
| `country` | text | ISO code | skiresort.com | CH, IT, AT, FR ✅ |
| `region` | text | – | skiresort.com | Canton / region / Land ✅ |
| `cross_border` | boolean | – | derived | True if the resort spans two countries ✅ |
| `elev_base_m` | integer | m a.s.l. | skiresort.com | Lowest point of the resort ✅ |
| `elev_top_m` | integer | m a.s.l. | skiresort.com | Highest point of the resort ✅ |
| `elev_band` | text | – | derived | `<1500`, `1500-2000`, `>2000` (from `elev_base_m`) ✅ |
| `slopes_km` | float | km | skiresort.com | Total slope length ✅ |
| `lifts_n` | integer | count | skiresort.com | Number of lifts ✅ |
| `price_day_adult_local` | float | CHF or EUR | skiresort.com | Adult one-day pass, main season ✅ |
| `price_currency` | text | – | skiresort.com | CHF or EUR ✅ |
| `price_day_adult_eur` | float | EUR | derived | Price converted with ECB rate of collection date ✅ |
| `snowmaking_pct` | float | % of slopes | skiresort.com | Share of slopes with snowmaking 🔄 (check if available) |
| `rating_overall` | float | stars (1–5) | skiresort.com | Test report score 🔄 |
| `rating_snow_reliability` | float | stars (1–5) | skiresort.com | Editorial snow reliability rating 🔄 |
| `scraped_on` | date | – | – | Collection date ✅ |
| `lat`, `lon` | float | degrees (WGS84) | Nominatim | Resort coordinates ✅ |
| `dist_city_km` | float | km | derived | Straight-line distance to nearest large city (Milan, Turin, Zurich, Munich, Lyon, Vienna) ✅ |
| `nearest_city` | text | – | derived | Name of that city ✅ |
| `hotels_4_5_star_10km` | integer | count | OSM Overpass | 4–5 star hotels within 10 km 🔄 |
| `cluster` | text | – | derived (k-means) | Prestige cluster ✅ |

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

#### Table resorts_features (`data/processed/resorts_features.csv`) — 300 Alpine Ski Resorts
Status: source feature table contains 300 rows and 22 columns, with 293 distinct source URLs. Lift counts are missing and the coordinate/identity review is pending. See `data/processed/snow_resort_input_review.csv`; this table is not yet an approved unique-area climate sample.

The listed fields below describe the intended feature meanings. The current source data include duplicate/cross-border records, filled prices and suspect coordinates; a populated field does not establish verified provenance.

| Variable | Type | Unit | Source | Description | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `resort_name` | text / string | – | `skiresort.info` | Full registered commercial name of the ski resort. | ✅ |
| `country` | text / string | ISO 3166-1 alpha-2 | `skiresort.info` | Alpine nation code (`CH`, `IT`, `AT`, `FR`). Exactly 75 resorts per country. | ✅ |
| `elevation_base_m` | integer | m a.s.l. | `skiresort.info` | Valley / bottom lift elevation station above sea level. | ✅ |
| `elevation_top_m` | integer | m a.s.l. | `skiresort.info` | Highest skiable mountain summit elevation station above sea level. | ✅ |
| `slope_km` | float | km | `skiresort.info` | Total length of groomed ski slopes / pistes. | ✅ |
| `price_day_eur` | float | EUR (€) | `skiresort.info` + ECB | Harmonized adult 1-day pass price in main season (converted from CHF at 1.05 rate). | ✅ |
| `rating_stars` | float | stars (1.0–5.0) | `skiresort.info` | Overall editorial and test evaluation score. | ✅ |
| `latitude` | float | decimal degrees | OSM Nominatim API | Geographic latitude (WGS84 coordinate reference system). | ✅ |
| `longitude` | float | decimal degrees | OSM Nominatim API | Geographic longitude (WGS84 coordinate reference system). | ✅ |
| `dist_nearest_city_km` | float | km | Derived (Haversine) | Great-circle distance to the closest major feeder metropolis (min of the 6 hubs). | ✅ |
| `dist_zurich_km` | float | km | Derived (Haversine) | Geodesic distance to Zurich city center (47.3769° N, 8.5417° E). | ✅ |
| `dist_geneva_km` | float | km | Derived (Haversine) | Geodesic distance to Geneva city center (46.2044° N, 6.1432° E). | ✅ |
| `dist_milan_km` | float | km | Derived (Haversine) | Geodesic distance to Milan city center (45.4642° N, 9.1900° E). | ✅ |
| `dist_turin_km` | float | km | Derived (Haversine) | Geodesic distance to Turin city center (45.0703° N, 7.6869° E). | ✅ |
| `dist_munich_km` | float | km | Derived (Haversine) | Geodesic distance to Munich city center (48.1351° N, 11.5820° E). | ✅ |
| `dist_lyon_km` | float | km | Derived (Haversine) | Geodesic distance to Lyon city center (45.7640° N, 4.8357° E). | ✅ |
| `hotels_4_5_star_10km` | integer | count | OSM Overpass API | Number of 4- and 5-star hotels within a 10 km radial buffer (luxury/prestige proxy). | ✅ |

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
