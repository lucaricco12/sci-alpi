"""Prepare or test CERRA-Land, keeping it separate from published snow results.

Default: prepare the request plan offline. --probe downloads one recent noon
field. --download-winter 2025 first checks that probe, then requests five
months at 06 UTC for a matched 20-station screening. Account setup and licence
acceptance must be completed by the account owner; no token belongs in GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from snow_validation import WINTERS, load_observations, project_root, season_dates

DATASET = "reanalysis-cerra-land"
API = "https://cds.climate.copernicus.eu/api"
SNAPSHOT = "data/config/cerra_land_cds"


def request_for_dates(dates, valid_hour=6):
    dates = pd.DatetimeIndex(dates)
    if dates.empty or valid_hour not in (6, 12):
        raise ValueError("Use non-empty dates and valid hour 6 or 12 UTC.")
    if dates.to_period("M").nunique() != 1 or dates.normalize().duplicated().any():
        raise ValueError("Each request must contain unique dates within one calendar month.")
    return {"variable": ["snow_depth"], "level_type": ["surface"],
            "product_type": ["forecast"], "year": [str(dates[0].year)],
            "month": [f"{dates[0].month:02d}"], "day": [f"{d.day:02d}" for d in dates],
            "time": [f"{valid_hour - 3:02d}:00"], "leadtime_hour": ["3"],
            "data_format": "grib"}


def monthly_requests(winter):
    dates = season_dates(winter).tz_localize(None)
    return [{"winter": int(winter), "calendar_month": str(month),
             "request": request_for_dates(dates[dates.to_period("M") == month])}
            for month in dates.to_period("M").unique()]


def expected_times(request):
    return pd.DatetimeIndex(sorted(
        pd.Timestamp(f"{year}-{month}-{day}T{time}:00Z") + pd.Timedelta(hours=int(lead))
        for year, month, day, time, lead in itertools.product(
            request["year"], request["month"], request["day"], request["time"], request["leadtime_hour"])))


def validate_request(request, form, constraints):
    """Check every requested combination, including leap days, against CDS rules."""
    fields = {x["name"]: x for x in form}
    for key, value in request.items():
        values = value if isinstance(value, list) else [value]
        if key not in fields or not set(values).issubset(fields[key]["details"]["values"]):
            raise ValueError(f"Request field is absent or unsupported in the saved CDS form: {key}")
    keys = [key for key in request if key != "data_format"]
    for values in itertools.product(*(request[key] for key in keys)):
        if not any(all(value in row.get(key, []) for key, value in zip(keys, values)) for row in constraints):
            raise ValueError("Request contains a combination unavailable in the CDS constraints snapshot.")


def build_plan(root):
    folder = Path(root) / SNAPSHOT
    form = json.loads((folder / "form.json").read_text())
    constraints = json.loads((folder / "constraints.json").read_text())
    catalogue = json.loads((folder / "catalogue.json").read_text())
    probe = request_for_dates(["2025-04-15"], valid_hour=12)
    full = [item for winter in WINTERS for item in monthly_requests(winter)]
    for request in [probe, *(item["request"] for item in full)]:
        validate_request(request, form, constraints)
    return {"dataset": DATASET, "checked_on": "2026-11-25",
            "status": "metadata_checked; authenticated_CERRA_Land_download_and_validation_pending",
            "catalogue_temporal_interval": catalogue["extent"]["temporal"]["interval"],
            "coverage_note": "Catalogue/form availability is not proof of successful file retrieval or complete snow values.",
            "spatial_note": "The current form exposes no area subset. Each GRIB field is a full European grid; extract points locally.",
            "variable_note": "Physical snow depth sde / paramId 3066 in metres; not snow water equivalent sd.",
            "timing_note": "CERRA-Land snow is forecast output. 09 UTC + 3 h = noon; 03 UTC + 3 h = 06 UTC.",
            "precision_note": "Inspect recent-file bitsPerValue; reject non-constant fields below 24 bits in the documented 2021-05 to 2025-07 issue period.",
            "probe_request": probe, "pilot_requests": [item for item in full if item["winter"] in (1995, 2025)],
            "full_validation_requests": full}


def file_hash(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def download_request(root, request):
    """Retain request/hash, reuse verified files, and never change published tables."""
    identity = hashlib.sha256(json.dumps({"dataset": DATASET, "request": request}, sort_keys=True).encode()).hexdigest()[:20]
    folder = Path(root) / "data/raw/cerra_land"
    target = folder / f"{identity}.grib"
    receipt = target.with_suffix(".json")
    if target.exists() or receipt.exists():
        if not target.is_file() or not receipt.is_file():
            raise ValueError("Incomplete CERRA-Land cache pair; inspect it before retrying.")
        saved = json.loads(receipt.read_text())
        if saved.get("dataset") != DATASET or saved.get("request") != request or saved.get("response_sha256") != file_hash(target):
            raise ValueError("CERRA-Land cached request or response hash does not match.")
        return target
    if not (os.environ.get("CDSAPI_KEY") or (Path.home() / ".cdsapirc").is_file()):
        raise RuntimeError("No private CDS credentials configured. Follow docs/cerra_land_setup.md; never paste a token into chat or GitHub.")
    try:
        import cdsapi
    except ImportError as error:
        raise RuntimeError("Install requirements-cerra-land.txt first.") from error
    key = os.environ.get("CDSAPI_KEY")
    options = {"url": API, "quiet": True, "debug": False, "progress": False}
    if key:
        options["key"] = key
    folder.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    try:
        cdsapi.Client(**options).retrieve(DATASET, request, str(partial))
    except Exception:
        # Provider exceptions can include signed URLs; keep them out of public logs.
        raise RuntimeError("CDS retrieval did not finish. Check your account, the CERRA-Land licence and provider request status. Completed caches are retained.") from None
    if not partial.is_file() or partial.stat().st_size == 0:
        raise ValueError("CDS returned no non-empty file.")
    partial.replace(target)
    receipt.write_text(json.dumps({"dataset": DATASET, "request": request,
                                  "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                                  "response_sha256": file_hash(target),
                                  "validation_status": "pending_GRIB_inspection_and_station_validation"}, indent=2) + "\n")
    return target


def validate_header(header, allowed):
    if header["paramId"] != 3066 or header["units"] != "m" or header["typeOfLevel"] != "surface" or header["stepType"] != "instant":
        raise ValueError("Expected instantaneous physical snow depth (paramId 3066) in metres at the surface.")
    valid = pd.Timestamp(f"{header['validityDate']} {header['validityTime']:04d}", tz="UTC")
    initial = pd.Timestamp(f"{header['dataDate']} {header['dataTime']:04d}", tz="UTC")
    if valid not in allowed or header["endStep"] != 3 or initial + pd.Timedelta(hours=3) != valid:
        raise ValueError("GRIB validity time or forecast lead does not match the requested UTC time.")
    if (pd.Timestamp("2021-05-01", tz="UTC") <= valid < pd.Timestamp("2025-08-01", tz="UTC")
            and 0 < header["bitsPerValue"] < 24):
        raise ValueError("Recent GRIB has less than 24 bits per non-constant value: possible documented CERRA-Land precision issue. Do not use it for risk or trends.")
    return valid


def sphere_points(lat, lon):
    lat, lon = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def inspect_grib(path, request, stations, grid_cache=None):
    """Read one GRIB field at a time; select geometric nearest grid points."""
    try:
        import eccodes as ec
    except ImportError as error:
        raise RuntimeError("Install requirements-cerra-land.txt first (GRIB reader ecCodes).") from error
    grid_cache = {} if grid_cache is None else grid_cache
    expected = expected_times(request)
    seen, rows, audit = set(), [], []
    # ecCodes reads the underlying descriptor. Disable Python buffering so the
    # magic-byte check cannot leave that descriptor ahead of the logical cursor.
    with Path(path).open("rb", buffering=0) as source:
        if source.read(4) != b"GRIB":
            raise ValueError("The downloaded response is not a GRIB file. Retain it for inspection; no counts were published.")
        source.seek(0)
        while (gid := ec.codes_grib_new_from_file(source)) is not None:
            try:
                keys = ["paramId", "units", "typeOfLevel", "stepType", "validityDate", "validityTime",
                        "dataDate", "dataTime", "endStep", "bitsPerValue", "gridType", "md5GridSection"]
                header = {key: ec.codes_get(gid, key) for key in keys}
                valid = validate_header(header, expected)
                if valid in seen:
                    raise ValueError("Duplicate GRIB validity time; no snow counts were published.")
                seen.add(valid)
                grid_id = header["md5GridSection"]
                selection_key = (grid_id, tuple(zip(stations.station_id, stations.lat, stations.lon)))
                if selection_key not in grid_cache:
                    lat = np.asarray(ec.codes_get_array(gid, "latitudes"), dtype=float)
                    lon = np.asarray(ec.codes_get_array(gid, "longitudes"), dtype=float)
                    tree = cKDTree(sphere_points(lat, lon))
                    chord, indices = tree.query(sphere_points(stations.lat.to_numpy(), stations.lon.to_numpy()))
                    grid_cache[selection_key] = (indices, lat[indices], ((lon[indices] + 180) % 360) - 180,
                                                2 * 6371.0088 * np.arcsin(np.clip(chord / 2, 0, 1)))
                indices, lat, lon, distances = grid_cache[selection_key]
                values = np.asarray(ec.codes_get_elements(gid, "values", indices.tolist()), dtype=float)
                missing = ec.codes_get(gid, "missingValue")
                if not np.isfinite(values).all() or (values < 0).any() or (values == missing).any():
                    raise ValueError("Missing or invalid depth at a selected station point; missing values are not zero snow.")
                for i, station in enumerate(stations.itertuples(index=False)):
                    rows.append({"station_id": station.station_id, "valid_time_utc": valid.isoformat(),
                                 "snow_depth_m": values[i], "grid_lat": lat[i], "grid_lon": lon[i],
                                 "grid_distance_km": distances[i], "grid_id": grid_id,
                                 "grid_elevation_verified": False, "model": "cerra_land"})
                audit.append({**header, "valid_time_utc": valid.isoformat()})
            finally:
                ec.codes_release(gid)
    if seen != set(expected):
        raise ValueError("GRIB file is missing requested validity times; incomplete seasons are not counted.")
    inspection = {"dataset": DATASET, "response_sha256": file_hash(path), "request": request,
                  "fields_checked": len(audit), "n_station_points": len(stations), "fields": audit,
                  "precision_note": "Packing check alone cannot confirm that the provider regenerated a file from the original higher-precision data.",
                  "status": "file_structure_checked; model_accuracy_and_grid_elevation_not_validated"}
    Path(path).with_suffix(".inspection.json").write_text(json.dumps(inspection, indent=2) + "\n")
    return pd.DataFrame(rows)


def compare_winter(root, daily, winter):
    observed = load_observations(root)
    observed = observed.loc[observed.winter.eq(winter)].copy()
    if daily.empty or not daily.model.eq("cerra_land").all() or daily.duplicated(["station_id", "valid_time_utc"]).any():
        raise ValueError("Expected unique CERRA-Land station/date keys.")
    if set(daily.station_id) != set(observed.station_id):
        raise ValueError("The CERRA-Land station set differs from the measured station set.")
    expected = season_dates(winter) + pd.Timedelta(hours=6)
    counts = []
    for station, group in daily.groupby("station_id"):
        times = pd.DatetimeIndex(pd.to_datetime(group.valid_time_utc, utc=True)).sort_values()
        if not times.equals(expected) or group[["grid_lat", "grid_lon", "grid_id"]].nunique().gt(1).any():
            raise ValueError("A complete 06 UTC winter at one unchanged grid point is required per station.")
        values = group.snow_depth_m.to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Missing or negative snow depth cannot enter counts.")
        counts.append({"station_id": station, "cerra_land_days_06utc": int((values >= .30).sum()),
                       "grid_lat": group.grid_lat.iloc[0], "grid_lon": group.grid_lon.iloc[0],
                       "grid_distance_km": group.grid_distance_km.iloc[0], "grid_elevation_verified": False})
    result = observed.merge(pd.DataFrame(counts), on="station_id", validate="one_to_one")
    baseline = pd.read_csv(Path(root) / "data/processed/snow_station_validation.csv")
    baseline = baseline.loc[baseline.winter.eq(winter), ["station_id", "model_days_06utc"]].rename(columns={"model_days_06utc": "era5_land_days_06utc"})
    result = result.merge(baseline, on="station_id", how="left", validate="one_to_one")
    if result.era5_land_days_06utc.isna().any():
        raise ValueError("Missing matched ERA5-Land baseline for the same winter.")
    for model in ("cerra_land", "era5_land"):
        result[f"{model}_error_days"] = result[f"{model}_days_06utc"] - result.snow_days_30cm
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true", help="Check dependencies/config presence without reading or displaying a token.")
    group.add_argument("--probe", action="store_true", help="Download/check one full-grid field valid 15 April 2025 at noon UTC.")
    group.add_argument("--download-winter", type=int, choices=WINTERS, help="After the probe, download five months at 06 UTC and screen 20 stations.")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    plan = build_plan(root)
    if args.status:
        print("Private CDS configuration present:", bool(os.environ.get("CDSAPI_KEY") or (Path.home() / ".cdsapirc").is_file()))
        for module in ("cdsapi", "eccodes"):
            print(f"{module} installed:", importlib.util.find_spec(module) is not None)
        print("CERRA-Land catalogue/form supports every target request; actual retrieval and model validation remain pending.")
        return
    (root / "data/config/cerra_land_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print("Prepared CERRA-Land: 1 recent-day noon probe, 10 pilot-month and 100 full-validation month requests.")
    if not args.probe and args.download_winter is None:
        print("No download started. Next: read docs/cerra_land_setup.md, configure your account, then --probe.")
        return
    try:
        if importlib.util.find_spec("eccodes") is None:
            raise RuntimeError("Install requirements-cerra-land.txt before requesting files.")
        stations = load_observations(root).drop_duplicates("station_id").reset_index(drop=True)
        cache = {}
        print("Checking one recent field before any winter download. CDS requests may queue.", flush=True)
        path = download_request(root, plan["probe_request"])
        preview = inspect_grib(path, plan["probe_request"], stations, cache)
        print(preview[["station_id", "snow_depth_m", "grid_distance_km"]].to_string(index=False))
        if args.download_winter is not None:
            panels = []
            for item in monthly_requests(args.download_winter):
                print("Checking", item["calendar_month"], flush=True)
                path = download_request(root, item["request"])
                panels.append(inspect_grib(path, item["request"], stations, cache))
            daily = pd.concat(panels, ignore_index=True)
            comparison = compare_winter(root, daily, args.download_winter)
            folder = root / "data/raw/cerra_land"
            daily.to_csv(folder / f"winter_{args.download_winter}_station_depths.csv", index=False)
            comparison.to_csv(folder / f"winter_{args.download_winter}_station_comparison.csv", index=False)
            for model in ("cerra_land", "era5_land"):
                error = comparison[f"{model}_error_days"]
                print(f"{model}: {len(error)} stations, bias {error.mean():.2f}, MAE {error.abs().mean():.2f}, RMSE {np.sqrt(np.mean(error**2)):.2f} days")
            print("Screening saved in data/raw/cerra_land/. One winter cannot validate long-term changes or risk classes.")
        print("File checks passed. This does not establish model accuracy or snow depth at the exact station elevation.")
    except (RuntimeError, ValueError) as error:
        parser.exit(2, str(error) + "\n")


if __name__ == "__main__":
    main()
