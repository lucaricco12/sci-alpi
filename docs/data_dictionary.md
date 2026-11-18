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
| `net_earnings_year_eur` | float | EUR per year | Eurostat `earn_nt_netft` | Net earnings, single person without children, 100 % of average wage ✅ |
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
| `winter`, `snow_days_30cm` | integer | year / days | MeteoSwiss | Same definition as `snow_winters` ✅ |

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
Status: ✅ Finalized (17 attributes, 300 complete records across CH, IT, AT, FR)

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