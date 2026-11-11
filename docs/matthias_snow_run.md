# Matthias's snow-data run

The input is Lorenzo's `data/processed/pilot_resorts_10.csv`, committed on 10 November 2026 in commit `950cc799c2467e86a76d9d85225367641a8ad41d`. His scraper is in `notebooks/02_scraping_pilot.ipynb`.

The snow notebook reads Lorenzo's column names directly. Resort IDs are the URL slugs in his scraper. The companion `data/processed/pilot_resort_locations.csv` adds coordinates matched by resort name and country. It records the selected OpenStreetMap place and the reason for each location choice.

The coordinates are reference points in the base towns. Valtournenche represents the lower Italian gateway for the Cervinia entry. Aprica uses the village node. The “Chamonix” entry uses Les Houches, matching Lorenzo's source URL. Les 2 Alpes uses Mont-de-Lans, matching the low end of its stated elevation range. These choices represent the locations supplied to the weather model.

Open-Meteo requests use ERA5-Land, hourly `snow_depth` in meters, `cell_selection=land`, and UTC. Each season runs from 1 December through 15 April, inclusive. The notebook checks every expected hourly timestamp and rejects missing snow values before calculating a daily maximum and counting days at or above 0.30 m. Leap years receive an additional day.

The base/top pilot covers winters 1994/95 and 2024/25. Both requests use the same coordinates and change the elevation parameter. The returned grid coordinates and full hourly series are compared. The 20-winter dataset uses the base requests for winters ending in 1986–1995 and 2016–2025. A positive `lost_snow_days` in the summary means the recent mean is lower than the past mean.

The measured station CSV contains 20 Swiss stations above 1,000 m with complete observations in all 20 winters. MeteoSwiss `hto000d0` is snow depth in centimeters measured at 06:00 UTC. A future model–station comparison must use the model value at the same hour, coordinates and date.

The original resort CSV has a provenance limitation. Lorenzo's scraper initializes records from preset numeric values and only replaces some fields when its parsing finds a match. The `snow_cannons` and `snow_making_pct` fields always come from the presets in that notebook. Other numeric fields have no saved per-field provenance. The snow workflow carries the input elevations through and records the elevation sent to the API. The source resort properties require verification before use in the final analysis.

Zermatt and Cervinia are two pilot entries on opposite sides of the same connected ski system. The pilot retains all ten supplied entries. The final sample needs a consistent rule for cross-border systems before the statistical analysis.

© OpenStreetMap contributors. Coordinates are provided under ODbL. The one-time Nominatim queries were cached, used a project User-Agent, and ran sequentially at no more than one request every 1.2 seconds. Usage policy https://operations.osmfoundation.org/policies/nominatim/

Weather data are from Open-Meteo using ECMWF/Copernicus ERA5-Land, CC BY 4.0. Hourly data were aggregated as described above. Documentation https://open-meteo.com/en/docs/historical-weather-api

Measured snow data source is MeteoSwiss. Documentation https://opendatadocs.meteoswiss.ch/a-data-groundbased/a5-manual-precipitation-stations

To rerun, install requirements.txt from the project root, open notebooks/03_snow_pilot.ipynb, and run all cells. The first run downloads historical data. The local data/raw/ cache makes repeat runs faster and is ignored by the group repository.

Completed outputs for this run are 20 base-only pilot rows, 20 base/top comparisons, 200 study resort winters, 10 resort summaries and 400 measured station winters. The base/top check found 12 identical series out of 20.

Open-Meteo's documentation warns that ERA5-Land snow depth tends to be overestimated and that its spatial resolution is limited. These outputs are model estimates for the chosen reference locations. The measured-station comparison remains part of SQ2 before interpreting the pilot estimates as evidence about actual snow reliability across the Alps.
