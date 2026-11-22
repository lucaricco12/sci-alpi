"""Prepare the direct Copernicus validation download without requiring a key.

Default: write requests only. --download-one 0 fetches one pilot month after
the account owner configures CDS credentials and accepts the dataset licence.
Downloaded files still require inspection and station validation; this module
does not promote them to resort snow-risk results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from snow_validation import WINTERS, project_root, season_dates

DATASET = "reanalysis-cerra-single-levels"
API = "https://cds.climate.copernicus.eu/api"
DATASET_URL = f"https://cds.climate.copernicus.eu/datasets/{DATASET}?tab=download"


def monthly_requests(winters):
    requests = []
    for winter in winters:
        dates = season_dates(winter)
        for month in dates.tz_localize(None).to_period("M").unique():
            days = dates[(dates.year == month.year) & (dates.month == month.month)]
            request = {"variable": ["snow_depth"], "level_type": "surface_or_atmosphere",
                       "data_type": ["reanalysis"], "product_type": "analysis",
                       "year": [str(month.year)], "month": [f"{month.month:02d}"],
                       "day": [f"{date.day:02d}" for date in days],
                       "time": ["06:00"], "data_format": "netcdf"}
            requests.append({"winter": int(winter), "calendar_month": str(month), "request": request})
    return requests


def build_plan():
    return {"dataset": DATASET, "dataset_url": DATASET_URL,
            "purpose": "06:00 UTC station validation; not an hourly/daily-maximum resort indicator",
            "spatial_download": "Full European CERRA grid; this form does not support area subsetting",
            "format_note": "NetCDF4 is labelled experimental in the provider form; inspect units and coordinates before counting",
            "current_status": "Prepared only; authenticated CDS retrieval has not been tested",
            "pilot_requests": monthly_requests((1995, 2025)),
            "full_validation_requests": monthly_requests(WINTERS)}


def download_one(root, item):
    if not (os.environ.get("CDSAPI_KEY") or (Path.home() / ".cdsapirc").is_file()):
        raise RuntimeError("Copernicus credentials are not configured. Follow docs/snow_expansion_status.md; do not put a key in GitHub files.")
    try:
        import cdsapi
    except ImportError as error:
        raise RuntimeError("Install the optional client: python -m pip install -r requirements-cerra.txt") from error
    request_id = hashlib.sha256(json.dumps(item["request"], sort_keys=True).encode()).hexdigest()[:16]
    folder = Path(root) / "data/raw/cerra_cds"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{item['calendar_month']}_{request_id}.nc"
    metadata = target.with_suffix(".json")
    if target.is_file() and metadata.is_file():
        saved = json.loads(metadata.read_text())
        if saved.get("dataset") == DATASET and saved.get("request") == item["request"]:
            with target.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            if saved.get("response_sha256") == digest:
                return target
        raise ValueError("Cached CDS file does not match its retained request/hash.")
    partial = target.with_suffix(".part")
    key = os.environ.get("CDSAPI_KEY")
    client = cdsapi.Client(url=API, key=key, quiet=True, debug=False) if key else cdsapi.Client(url=API, quiet=True, debug=False)
    client.retrieve(DATASET, item["request"], str(partial))
    if not partial.is_file() or partial.stat().st_size == 0:
        raise ValueError("CDS did not return a non-empty file.")
    with partial.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    partial.replace(target)
    metadata.write_text(json.dumps({"dataset": DATASET, **item,
                                   "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                                   "response_sha256": digest,
                                   "validation_status": "pending_file_inspection_and_station_validation"}, indent=2) + "\n")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-one", type=int, help="Fetch one of the ten pilot months, indexed 0–9.")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    plan = build_plan()
    path = root / "data/config/cerra_cds_download_plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"Prepared {len(plan['pilot_requests'])} pilot-month requests and {len(plan['full_validation_requests'])} full-validation requests.")
    print("The form requires full European grids. Start with one file; do not launch a bulk download before checking it.")
    if args.download_one is not None:
        if not 0 <= args.download_one < len(plan["pilot_requests"]):
            parser.error("--download-one must be between 0 and 9")
        try:
            print(download_one(root, plan["pilot_requests"][args.download_one]))
        except RuntimeError as error:
            parser.exit(2, str(error) + "\n")


if __name__ == "__main__":
    main()
