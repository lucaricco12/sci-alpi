# Matthias's snow-data pipeline

**Both checkpoints:** open `notebooks/03.3_matthias_checkpoints.ipynb` and Run All. [Short explanation](docs/matthias_group_update.md) · [Full report](docs/matthias_checkpoint_report.md) · [Interactive map, download to open](docs/ski_resorts_closures_map.html). The new workflow includes the 20-station measured regression and a clearly labelled 24-area four-country model demonstration.

**New to this project? Start with [the plain-English explanation](docs/matthias_simple_explanation.md).** It explains the question, the result from real measurements, why the weather estimates need care, and what is still needed for the four-country study.

## Earlier workflow: model–station validation

Open `notebooks/03.2_snow_analysis.ipynb`, select the Python kernel and **Run All**. It uses the committed station-model tables, so no API download is needed by default. Results appear below the code cells. The notebook rebuilds the validation tables, input audit, figures and findings report.

For an existing Codespace, first run `git pull --ff-only origin main` and `python -m pip install -r requirements.txt` in its terminal. New Codespaces install the tools automatically. You can also rebuild all saved results with `python src/run_snow_analysis.py`.

Read [the expansion status](docs/snow_expansion_status.md) for the new resort roster, alternative-model check and next download step. Read `docs/matthias_next_steps.md` for the full validation. Figures are in `docs/figures/`; numerical outputs are in `data/processed/` (`snow_station_validation.csv`, `snow_validation_metrics.csv`, `snow_station_changes.csv`, `snow_validation_trend_metrics.csv`). The full-resort review is `snow_resort_input_review.csv`.

The comparison uses ERA5-Land at each of the 20 measured station coordinates and requested elevations, with snow depth at **06:00 UTC** to match MeteoSwiss. The original resort pilot below uses the **daily maximum**, so it is a separate indicator. The returned model grid point is retained and shown on the station map.

To refresh missing raw station-model seasons from the terminal: `python src/snow_validation.py --download`. Completed API responses are cached locally. A failed or rate-limited batch preserves the published model table. To run the checks: `python -m unittest discover -s tests -v`.

## Original 10-location resort pilot

The notebook reads Lorenzo's ten-resort pilot from data/processed/pilot_resorts_10.csv and adds the location mapping in data/processed/pilot_resort_locations.csv.

From the repository root, install requirements.txt, open notebooks/03_snow_pilot.ipynb, select the Python 3 kernel, and run all cells. A first run downloads the historical snow data. Later runs reuse responses saved in data/raw/. The completed output CSVs are already available in data/processed/.

| File | Contents |
| --- | --- |
| snow_winters_pilot.csv | 20 base-elevation rows for the two test winters |
| snow_pilot_base_top.csv | 20 base/top comparisons with returned model-grid coordinates |
| snow_winters_10resorts.csv | 200 rows, one for each resort and study winter |
| snow_summary_10resorts.csv | Ten summaries comparing the two ten-winter means |
| meteoswiss_station_winters.csv | 400 rows from 20 Swiss stations with complete observations |
| pilot_resort_locations.csv | IDs, coordinates and documented location choices |

All seven notebook code cells completed successfully from the project folder. The outputs were checked for unique resort-winter keys, twenty winters per resort, ten winters per period, complete hourly seasons and agreement between overlapping pilot and study rows.

Read docs/matthias_snow_run.md for the source decisions and data-quality limitations. The source scraper uses preset values for some resort fields. The weather coordinates represent the base towns. Zermatt and Cervinia are two entries for opposite sides of one connected ski system.

The project's .gitignore excludes data/raw/, where API responses are cached locally.
