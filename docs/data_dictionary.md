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
| `facility_name` | text | – | Legambiente | Name of closed facility / locality ✅ |
| `region` | text | – | Legambiente | Italian region ✅ |
| `status` | text | – | Legambiente | `dismesso` (closed) or `chiuso temporaneamente` ✅ |
| `lat`, `lon` | float | degrees | Nominatim | Geocoded location 🔄 |
| `matched` | boolean | – | derived | True if geocoding succeeded ✅ |
