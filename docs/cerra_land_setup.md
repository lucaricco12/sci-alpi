# CERRA-Land: what is ready and what Matthias must do

Updated **26 November 2026**. The existing checkpoint results still use the original measured/model inputs. **The user's single-field CERRA-Land probe passed file checks in Codespaces. A complete winter and model accuracy remain unverified.**

## Repair HTTP 401 after using the earlier setup

The earlier version of our setup script incorrectly surrounded the saved key with JSON quotation marks. The CDS client uses a simple `key: value` reader and retains those quote marks as part of the credential. This can reject a correct key with HTTP 401. The updated setup writes the unquoted value and checks compatibility with the real CDS parser and credential resolver.

To fix the older private file without copying or displaying your key again, run:

```bash
git pull --ff-only origin main
unset CDSAPI_KEY CDSAPI_RC
python src/setup_cds.py --repair
python src/cerra_land.py --probe
```

`--repair` removes the older script's JSON quotes, keeps other settings and uses an atomic owner-only replacement. Already-unquoted files stay unchanged; ambiguous, malformed or linked files are preserved and rejected. Clearing the two optional environment settings makes this shell use the private file just repaired. No token is displayed or submitted by the repair command. This fixes local storage format; the subsequent probe still needs a current key and accepted licence. If HTTP 401 persists after repair, use `--replace` below with the current key from your profile.

## What we already did

| Work | Status |
| --- | --- |
| Check ERA5-Land against 20 Swiss stations for all 20 study winters | Done: 400 matched station winters; about 54 extra snow days per winter in this selected sample |
| Screen ordinary CERRA through Open-Meteo | Done for two winters (1995, 2021); this is **not CERRA-Land** |
| Verify current CERRA-Land catalogue, form and date constraints | Done: all 100 monthly requests for our unchanged 20 study winters are permitted by the saved form/constraints |
| Prepare a small recent-file test, GRIB inspection and one-winter station comparison | Code tests pass; the user's real one-field probe passed; the full-winter run is currently rejected |
| Create the account, accept the licence, configure the private token | Setup worked for the user's successful one-field probe; retain it |
| Download real CERRA-Land, test its accuracy, rebuild resort risk classes | One field checked; a complete winter, accuracy validation and risk conclusions remain pending |

## Current coverage and two corrections to the shared instructions

The old guide introduction still mentions April 2021, but the current ECMWF dataset page lists coverage to **31 July 2025**. The CDS catalogue and form advertise dates in 2025, and their constraints allow every date we need for the original winters 1985/86–1994/95 and 2015/16–2024/25. The catalogue's nominal end is December 2025; that metadata is not evidence that every file or grid value exists. **Keep the original study periods while testing actual retrieval.** Do not change the recent decade simply because the older introduction ends in 2021.

The current form exposes **no area-subset field**. The test downloads one full European field and extracts the 20 station points locally, rather than assuming an Alps rectangle is accepted. This is still much smaller than requesting a full winter or hourly multi-year fields.

Snow depth is a **forecast** variable in CERRA-Land. `time` is the forecast start time. We request `09:00` plus `leadtime_hour=3` for a field **valid at noon**, and `03:00` plus 3 hours for **06:00 UTC** to match the measured stations. Requesting noon plus three hours would give 15:00. Physical snow depth is `sde`, parameter 3066, in metres; `sd` is snow water equivalent and cannot be compared directly with the 30 cm depth threshold.

## Your account steps

1. Open [Copernicus CDS](https://cds.climate.copernicus.eu/) and use **Login–Register** to create/sign into your ECMWF account.
2. Open [CERRA-Land → Download](https://cds.climate.copernicus.eu/datasets/reanalysis-cerra-land?tab=download). Accept that dataset's licence/terms at the bottom of the form. This acceptance is a manual account step.
3. Open your CDS profile/API setup and copy your **Personal Access Token** privately. Do not send it to the group or ChatGPT, or put it in a notebook.

In your Codespace terminal, from the `sci-alpi` project folder:

```bash
git pull --ff-only origin main
python -m pip install -r requirements.txt -r requirements-cerra-land.txt
python src/setup_cds.py
```

The last command prompts for the token with input hidden and saves it to `~/.cdsapirc`, outside the repository, with owner-only permissions. An existing configuration is preserved. No token is passed as a command argument or printed.

**If you changed your API key:** use `python src/setup_cds.py --replace`. This asks for the replacement privately and replaces the old configuration only after the new input is valid. It preserves the file if you submit an empty or invalid value. The setup now explains that its hidden prompt takes a key, while the normal shell prompt ending in `$` takes a command. Paste the key once at `(hidden):`, press Enter and wait for the saved confirmation.

**If a key appears in a screenshot or as a shell command:** generate a new one from the API-key section of your [CDS profile](https://cds.climate.copernicus.eu/profile), then use `--replace` above. Generating a new key invalidates the old one. Do not send the replacement key in chat or screenshots.

Then run:

```bash
python src/cerra_land.py --status
python src/cerra_land.py --probe
```

**What you should see:** a small table with the 20 station IDs, the depth in metres at noon on 15 April 2025, and the distance to each nearest grid point. A successful run ends with `File checks passed`. A failure does not mean zero snow; it means stop and inspect the account/licence, service status or file problem. Requests can queue; do not promise completion within one hour.

The command identifies HTTP authentication, licence, rate-limit and service failures using fixed messages. HTTP 401 means the service did not accept the credentials; HTTP 403 with a provider licence requirement directs you to accept the terms on the CERRA-Land Download page. A generic 403 does not establish that the licence is missing. HTTP 400/422 now includes a short **Provider reason (redacted)** excerpt so we can diagnose the rejected request or retrieval. Known credentials, private fields, URLs and long identifiers are removed. Unfiltered provider text is not echoed. A failed request does not prove that the selected date is unavailable.

### December 2024 request rejection, 26 November

The one-field probe passed in the user's Codespace, while the first winter month returned HTTP 400. The current public form/constraints permit the requested December dates and 03 UTC + 3-hour lead, and the public costing service returned HTTP 200 with cost **31 fields**, limit **90,000**, for the full month. One-day and noon alternatives were also under that size limit. These checks do not prove archive availability or successful authenticated retrieval; the costing response did not explicitly return a request-validity verdict. Public, credential-free results are retained in `data/config/cerra_land_cost_checks_20261126.json`.

The monthly request and study periods were therefore preserved. The subsequent error excerpt only said **The job has been rejected**. The official CDS client exposes a separate `traceback` field; our initial summary selected `detail` alone and lost that cause. The summary now retains traceback/reason/detail together, with the same redaction and length bound. Long traces preserve their end, where the actual exception is commonly reported.

Inspect the **existing** failure without resubmitting the winter download:

```bash
git pull --ff-only origin main
python src/cerra_land.py --last-error
```

This reads the ten latest failed/rejected jobs, filters for CERRA-Land, and reports the newest matching job's redacted server logs and error. It does not submit, download or delete anything. The diagnostic supports both HTTP errors and the official SDK's `ProcessingFailedError`. If there is no retained matching job, it says so. Report this output, or the failed job's Error details from Your Requests. No new API key or licence reset is indicated by HTTP 400 alone. The retained queue-limit cause is documented below.

### Queue-limit cause and a simple duplicate check

The user's retained traceback now identifies **Maximum number queued requests for this dataset has been reached**. Their dashboard also shows global dataset/archive congestion and multiple Accepted requests. Similar dataset titles alone do not establish that those requests are duplicates.

Use one read-only check instead of comparing several screenshots:

```bash
git pull --ff-only https://github.com/lucaricco12/sci-alpi.git main
python src/cerra_land.py --queue
```

It lists active CERRA-Land requests, shows selected date/time fields, and flags identical **full recorded selections**, ignoring only dictionary/list order. It also checks whether a queued selection matches the configured one-field probe and a local cache whose receipt, inspection and response hash all agree. Missing selections or an unverified cache do not establish a completed duplicate. The report checks up to 50 active account jobs, filters for CERRA-Land and warns when that view may be incomplete. No job is submitted, cancelled, deleted or downloaded. Review the report before clearing any redundant queued probes; preserve useful winter requests.

The installed GRIB reader is ECMWF's **ecCodes** Python package. Its Linux pip wheel installed successfully in our test environment, so this workflow does not require xarray/cfgrib. The default checkpoint notebook does not require these optional packages.

## After the small test works

For a complete winter at the same 06 UTC measurement time:

```bash
python src/cerra_land.py --download-winter 2025
```

This first checks/reuses the recent-day probe, then requests five monthly full-grid files: December 2024 to 15 April 2025. Requests run sequentially. Every file must have physical depth in metres, the exact requested validity times and usable values at all selected stations. The command saves requests, SHA-256 hashes, packing/time audits, daily point depths and the station comparison in **`data/raw/cerra_land/`**. It prints bias, MAE and RMSE for CERRA-Land and the same-winter ERA5-Land baseline. These outputs are ignored by Git and do not overwrite published snow tables or database tables.

`--download-winter 1995` gives a second pilot winter. Default `python src/cerra_land.py` only prepares the offline request plan, including all 100 monthly requests for the 20 original study winters; it does not download them. A full-period run is deliberately not launched automatically.

## Important data issue before interpreting the results

ECMWF documents accidental **12-bit instead of 24-bit packing** for data between 1 May 2021 and 31 July 2025, with snow depth among the most affected variables. The guide says corrected files would be available by July 2026. That promised date alone does not prove a particular downloaded file was corrected. The reader records `bitsPerValue` and rejects non-constant recent fields with fewer than 24 bits. A constant field can legitimately use zero bits. Even a 24-bit header cannot prove that a file was regenerated from the original high-precision data; retain the retrieval/hash and seek provider clarification if the correction status is uncertain.

Nearest-grid extraction does **not** correct snow depth to the station or resort elevation. Grid coordinates and distances are retained; grid elevation remains explicitly unverified. The public ECMWF evaluation supports testing CERRA-Land as a candidate, but it does not establish accuracy at our locations. One or two successful winters cannot validate the past-to-recent climate change signal. Full-period station checks, grid elevation and remaining resort-location checks come before final country conclusions or price/closure risk classes.

## What you can tell the group now

> We completed the original model–station comparison and found a large bias in our selected Swiss sample. We checked the current CERRA-Land download options and prepared a recent-file test plus the matched station-comparison code. Current metadata supports our original study periods. The authenticated download and CERRA-Land accuracy checks are still pending account setup; we have not yet replaced the model or recalculated validated risk classes.

## Sources and reproducibility

- [CERRA-Land catalogue](https://cds.climate.copernicus.eu/datasets/reanalysis-cerra-land) and [live catalogue API](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/reanalysis-cerra-land), accessed 25 November 2026. Exact public catalogue/form/constraints snapshots and their source URLs and SHA-256 hashes are in `data/config/cerra_land_cds/`.
- [ECMWF dataset coverage](https://www.ecmwf.int/en/forecasts/datasets/cerra-land-sub-daily-regional-reanalysis-data-europe-1984-present).
- [CERRA-Land user guide](https://confluence.ecmwf.int/spaces/CKB/pages/278548151/CERRA-Land+surface+reanalysis+Data+User+Guide), including the forecast convention, snow-depth parameter and known precision issue.
- [CERRA strengths and weaknesses](https://confluence.ecmwf.int/spaces/CKB/pages/488285319/CERRA+Strengths+and+weaknesses): the favourable snow evaluation is evidence for a candidate method, not our own station validation.
- [Official account/API/licence setup](https://cds.climate.copernicus.eu/how-to-api), currently recommending `cdsapi>=0.7.7`.
- [ECMWF ecCodes Python package](https://github.com/ecmwf/eccodes-python). Decoder tests generate explicitly synthetic GRIB data locally; those files are not climate evidence.
