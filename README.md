# Climate Change, Snow Economics, and Ski Pass Pricing across the Alps

Data Analytics project, ZHAW School of Management and Law, HS2026 (Dr. Mario Gellrich).

**Team:** Luca · Lorenzo · Matthias

## Matthias's November 25 / December 2 checkpoints

Open **[notebooks/03.3_matthias_checkpoints.ipynb](notebooks/03.3_matthias_checkpoints.ipynb)** and choose **Run All**. It uses saved inputs and shows the exploration, regressions, station checks, map and database handover. No API download is needed by default.

Start with [the short group explanation](docs/matthias_group_update.md) or [the detailed checkpoint report](docs/matthias_checkpoint_report.md). The [interactive map](docs/ski_resorts_closures_map.html) opens after downloading the HTML file; its libraries and country outlines are bundled. A static version is included in the report.

The measured result covers 20 Swiss stations. The four-country regression is a separate **24-area unvalidated model demonstration**, not a completed full-resort climate-risk result. This limitation is retained in the outputs and SQL tables.

```bash
python -m pip install -r requirements.txt
python src/run_snow_checkpoints.py
```

The runner adds qualified checkpoint tables to the existing SQLite database while preserving the original team tables. The pilot-ID crosswalk fixes the mismatched source identifiers. The earlier notebook `03.2_snow_analysis.ipynb` retains the full validation details.

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

- **Target snow reliability**: number of days per winter with at least 30 cm of natural snow depth between 1 December and 15 April, at the resort's base elevation. A resort is "snow-reliable" with at least 100 days (100-day rule, Witmer 1986).
- **Periods**: winters 1985/86–1994/95 vs 2015/16–2024/25 (10 winters each). A winter is named after the year in which it ends.
- **Risk class** (recent period): reliable (≥ 100 days), at risk (60–99), critical (< 60). The 60/99 thresholds are our own choice.
- **Price**: adult one-day pass, main season, same source and same collection date for all resorts.
- **Design**: prices are cross-sectional (one season). We assume today's prices reflect the climate risk accumulated over time; without historical prices this cannot be tested. Results are associations, not causal effects.

**Current snow-data limitation:** the API's raw snow depth is a grid estimate. Requesting the base elevation does not establish snow depth at that exact height; the provider does not mark snow depth for elevation correction. The matched Swiss validation found substantial error and weak reproduction of observed changes. Raw pilot classifications have not been validated as resort risk labels. See [Matthias's plain-English explanation](docs/matthias_simple_explanation.md) for the measured findings and the unresolved four-country snow method.

## Data sources

| Source | Method | Content |
| --- | --- | --- |
| skiresort.com (formerly skiresort.info) | Web scraping | Elevation, slope km, lifts, day-pass price, snowmaking, ratings |
| Nominatim (OpenStreetMap) | Web API | Coordinates of resorts, closed facilities and large cities |
| Open-Meteo Historical (ERA5-Land) | Web API | Hourly snow depth, 1985–2025 winters |
| MeteoSwiss Open Data | CSV download | Measured daily snow depth at Swiss stations |
| Eurostat (`prc_ppp_ind`, `earn_nt_net`) | Web API | Price level index, average net earnings |
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

## How to run Matthias's results

**Open [the checkpoint notebook](notebooks/03.3_matthias_checkpoints.ipynb) and choose Run All.** It uses saved data and shows the results under its cells. You do not need to run the scraping notebooks first.

For an existing Codespace, run these commands once in its terminal:

```bash
git pull --ff-only origin main
python -m pip install -r requirements.txt
```

Then open `notebooks/03.3_matthias_checkpoints.ipynb`, choose a Python kernel and **Run All**. The charts also appear in [the short explanation](docs/matthias_simple_explanation.md).

New Codespaces install the requirements and Python/Jupyter extensions automatically. The notebook is selected as the opening file. The container configuration can also be applied to an existing Codespace with **Codespaces: Rebuild Container**.

To rebuild the saved snow tables and figures from the terminal:

```bash
python src/run_snow_checkpoints.py
```

The VS Code task **Snow: reproduce saved results** runs the same command. No API download is needed. Other team notebooks remain separate workflows; some make live downloads.

### Current expansion status

The follow-up includes a source review of all flagged resort identities, a deduplicated climate roster, a matched CERRA screening and a direct Copernicus download plan. The full four-country snow analysis remains pending a suitable full-period snow method and further location checks. See [the expansion status](docs/snow_expansion_status.md) and [Matthias's plain-English explanation](docs/matthias_simple_explanation.md).
