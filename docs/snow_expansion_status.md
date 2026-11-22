# What is implemented, and what still needs data

The measured Swiss results, model checks and figures are on `main`. Open `notebooks/03.2_snow_analysis.ipynb` and choose **Run All**. Its default run uses saved tables, including the follow-up checks below, without internet access or a Copernicus account.

## Resort locations and duplicate areas

Lorenzo's original 300-row feature table is preserved. The new `resorts_snow_roster.csv` has **293 distinct ski-area source URLs**. Two same-country duplicate groups are combined for climate analysis; five cross-border systems are assigned to `cross_border`, so they are not silently counted as two independent resorts or attributed to one country. Original price-market rows remain available for Luca's work.

All **33 flagged identities, representing 40 original rows**, were checked against their Skiresort access pages. We retained 211 explicitly listed lift-access points, with source URLs, retrieval timestamps and SHA-256 hashes in `resort_location_evidence.csv`. Scope decisions are explicit in `data/config/resort_scope_decisions.csv`.

- **18 areas are outside the Alps**: three in the Apennines and fifteen in the French Pyrenees or Massif Central. They are excluded from the Alpine candidate set.
- **275 areas remain candidates**, including five cross-border systems. The other 260 identities have not been individually rechecked.
- Ten reviewed Alpine identities had original coordinates over 30 km from the selected source access point. Examples include Les 3 Vallées, 4 Vallées, Via Lattea, San Domenico, Les Houches and Puy Saint Vincent.

For reviewed identities, the roster uses the **first explicitly listed lift-access point**, keeping the original coordinates and the movement distance. This is a reproducible representative location, not proof of snow depth at the minimum ski elevation. All rows retain `base_elevation_at_point_verified=False` and `snow_method_validated=False`. A candidate roster is not a validated full snow dataset.

To rebuild the roster from saved evidence: `python src/resort_review.py`. The optional `--download` refreshes missing source-page caches. The original automatic audit still flags the original inputs; the separate roster records the follow-up decisions.

## Alternative snow-model screening

We compared **the same 20 stations in winters 1995 and 2021** for ERA5-Land and CERRA, using complete hourly responses, metres and 06:00 UTC counts. These years were selected because both public products cover them, not as replacement study periods.

| Model | Matched station winters | Mean overcount, days | Mean absolute error, days | RMSE, days |
| --- | ---: | ---: | ---: | ---: |
| ERA5-Land | 40 | 31.20 | 34.65 | 46.25 |
| CERRA | 40 | 14.05 | 27.80 | 39.13 |

CERRA improves these screening errors, but the remaining errors are substantial. Two winters do not validate its long-term changes or resort risk classes. CERRA also assimilates observations, so a station comparison is not necessarily fully independent. This screening does not replace the original 400-case ERA5-Land validation.

The public CERRA API returned **3,264 timestamps but zero non-missing depths** for Adelboden in winter 2025. A separate ERA5 request for winter 1995 also returned no usable depth values. Missing values are recorded as unavailable, never as zero-snow days. See `snow_model_availability.csv`; this is a documented availability probe, not a claim that every possible coordinate/date was tested.

Saved screening reproduction: `python src/snow_candidates.py`. Use `--download` only to fetch missing candidate caches.

## Direct Copernicus data: the prepared next step

The official CERRA single-level catalogue now covers the target recent years, beyond the public Open-Meteo CERRA coverage. Its current form offers physical `snow_depth`, surface analysis at 06:00 UTC, and GRIB or experimental NetCDF4. It does **not** offer area subsetting, so downloaded files contain the European grid and can be large.

`src/cerra_download_plan.py` prepares:

- Ten monthly requests for the two original pilot winters, 1995 and 2025.
- One hundred monthly requests for all 20 target winters, with correct leap days and April ending on the 15th.
- An optional single-month download with a retained request and response hash. Authenticated retrieval has not been tested because no CDS credentials are configured here.

The first step is **one recent file**, not the whole European download. After the account owner accepts the dataset's licence and configures the private API key following the official setup page, run in the Codespace:

```bash
python -m pip install -r requirements-cerra.txt
python src/cerra_download_plan.py --download-one 5
```

Index 5 selects December 2024, the start of winter 2025. Credentials belong in `~/.cdsapirc` or the private `CDSAPI_KEY` environment variable. They do not belong in notebook cells, chat messages or committed files. Without credentials, the command stops before starting a download and preserves the published results.

The downloaded file must then be inspected for actual units, variable identity, times, spatial coordinates and grid elevation, followed by matched station validation for the full periods. The request plan does not label an unvalidated file as an analysis result. The prepared direct download uses 06:00 UTC for validation; it does not yet provide the original resort pilot's hourly daily-maximum indicator.

## Still open for the four-country conclusions

A suitable full-period snow method, the remaining individual location checks and the elevation basis must be settled before bulk resort downloads, country/elevation inference, risk classes or snow-to-price/closure joins. The current Swiss measured findings remain usable with their stated sample and station-history limitations. The original four-country question is unchanged.

## Sources

- Resort evidence: the exact per-area Skiresort access URLs, timestamps and hashes in `data/processed/resort_location_evidence.csv`; scope follows those locations and region breadcrumbs, not the page-wide navigation.
- Public API: https://open-meteo.com/en/docs/historical-weather-api and the exact requests/hashes in the candidate and availability CSVs.
- CERRA dataset and current request form: https://cds.climate.copernicus.eu/datasets/reanalysis-cerra-single-levels?tab=download
- Current catalogue and linked form schema, checked 22 November 2026: https://cds.climate.copernicus.eu/api/catalogue/v1/collections/reanalysis-cerra-single-levels
- CERRA documentation: https://confluence.ecmwf.int/spaces/CKB/pages/272323672/Copernicus+European+Regional+ReAnalysis+CERRA+product+user+guide
- Official account, API-key and licence setup: https://cds.climate.copernicus.eu/how-to-api
