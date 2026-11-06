# Climate Change, Snow Economics, and Ski Pass Pricing across the Alps

Data Analytics project, ZHAW School of Management and Law, HS2026 (Dr. Mario Gellrich).

**Team:** Luca · Lorenzo · Matthias

## Research question

To what extent has natural snow reliability in Swiss, Italian, Austrian and French ski resorts declined between 1986–1995 and 2016–2025, how does this decline depend on elevation and country, and do day-pass prices reflect this climate risk once resort size, prestige and national price and wage levels are accounted for?

### Sub-questions

| # | Question | Method |
| --- | --- | --- |
| SQ1 Climate | How many days with ≥ 30 cm of natural snow has a typical winter lost? Is the loss larger below 1,500 m and in Italy? | Difference between periods per resort; ANOVA by country and elevation band; linear regression of the loss on elevation × country |
| SQ2 Data quality | Does the ERA5-Land reanalysis (Open-Meteo) show the same trend as MeteoSwiss station measurements? | Correlation with p-value, bias, RMSE |
| SQ3 Prices | Holding size, elevation and prestige cluster constant, are resorts with less reliable snow cheaper? | K-means (prestige clusters) + OLS regression of log price, compared across clusters |
| SQ4 Affordability | How many working hours does a day pass cost a local skier and a cross-border skier? | "Working hours per ski pass" index; 4 × 4 matrix country of origin × destination; EUR/CHF exchange rate |
| SQ5 Closures (Italy) | Do the ski facilities closed according to Legambiente fall into the "at risk" group? | Chi-squared test: status × snow-risk class |

## Definitions

- **Snow reliability**: number of days per winter with at least 30 cm of natural snow depth between 1 December and 15 April, at the resort's base elevation. A resort is "snow-reliable" with at least 100 days (100-day rule, Witmer 1986).
- **Periods**: winters 1985/86–1994/95 vs 2015/16–2024/25 (10 winters each). A winter is named after the year in which it ends.
- **Risk class** (recent period): reliable (≥ 100 days), at risk (60–99), critical (< 60). The 60/99 thresholds are our own choice.
- **Price**: adult one-day pass, main season, same source and same collection date for all resorts.
- **Design**: prices are cross-sectional (one season). We assume today's prices reflect the climate risk accumulated over time; without historical prices this cannot be tested. Results are associations, not causal effects.

## Data sources

| Source | Method | Content |
| --- | --- | --- |
| skiresort.com (formerly skiresort.info) | Web scraping | Elevation, slope km, lifts, day-pass price, snowmaking, ratings |
| Nominatim (OpenStreetMap) | Web API | Coordinates of resorts, closed facilities and large cities |
| Open-Meteo Historical (ERA5-Land) | Web API | Hourly snow depth, 1985–2025 winters |
| MeteoSwiss Open Data | CSV download | Measured daily snow depth at Swiss stations |
| Eurostat (`prc_ppp_ind`, `earn_nt_netft`) | Web API | Price level index, average net earnings |
| Frankfurter (ECB rates) | Web API | EUR/CHF exchange rate |
| OSM Overpass | Web API | 4–5 star hotels near each resort |
| Legambiente, Nevediversa 2026 | PDF report | Closed ski facilities in Italy |

## Repository structure

```
sci-alpi/
├── data/
│   ├── raw/          # raw HTML and API responses (not pushed to GitHub)
│   └── processed/    # cleaned CSV files
├── db/               # SQLite database
├── notebooks/        # 01_country_stats … 06_models
├── docs/             # ai_log.md, data_dictionary.md, integration_log.md
├── requirements.txt
└── README.md
```

## How to run

1. Open the repository in GitHub Codespaces.
2. In the terminal: `pip install -r requirements.txt`
3. Open the notebooks in `notebooks/` in numerical order and run all cells.
