# Matthias's snow-data pipeline

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
