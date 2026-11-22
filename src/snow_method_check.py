"""Isolate the effect of Open-Meteo grid selection on the existing pilot winters.

This is a sensitivity test, not a replacement for the 20-winter climate study.
Both options use all 20 previously selected stations and winters 1995 and 2025.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from snow_validation import (RateLimiter, get_model_row, load_observations,
                             pair_sources, project_root)

PILOT_WINTERS = (1995, 2025)


def download_nearest_pilot(root):
    observations = load_observations(root)
    subset = observations.loc[observations.winter.isin(PILOT_WINTERS)].copy()
    stations = observations.drop_duplicates("station_id")
    limiter = RateLimiter()
    rows = []
    errors = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(get_model_row, root, station, year, limiter, "nearest"): (station.station_id, year)
                for station in stations.itertuples(index=False) for year in PILOT_WINTERS}
        for future in as_completed(jobs):
            key = jobs[future]
            try:
                rows.append(future.result())
            except Exception as error:
                errors.append((key, str(error)))
            done = len(rows) + len(errors)
            if done % 10 == 0:
                print(f"Closest-point test: {len(rows)}/{len(jobs)} complete; {len(errors)} errors.", flush=True)
    if errors:
        raise RuntimeError(f"Method-test downloads failed; cached successes are retained: {errors[:3]}")
    models = pd.DataFrame(rows).sort_values(["station_id", "winter"]).reset_index(drop=True)
    pair_sources(subset, models, cell_selection="nearest")
    models.to_csv(Path(root) / "data/processed/station_model_nearest_pilot.csv", index=False)
    return models


def compare_selections(root, nearest_models):
    root = Path(root)
    observations = load_observations(root)
    subset = observations.loc[observations.winter.isin(PILOT_WINTERS)]
    baseline = pd.read_csv(root / "data/processed/station_model_winters.csv")
    baseline = baseline.loc[baseline.winter.isin(PILOT_WINTERS)]
    land = pair_sources(subset, baseline)
    nearest = pair_sources(subset, nearest_models, cell_selection="nearest")
    keys = ["station_id", "winter", "period"]
    fields = ["model_days_06utc", "error_days", "grid_lat", "grid_lon", "grid_distance_km", "request_url", "response_sha256"]
    meta = ["station_name", "lat", "lon", "elev_m", "observed_days_06utc", "observed_days"]
    result = land[keys + meta + fields].merge(nearest[keys + fields], on=keys, validate="one_to_one", suffixes=("_land", "_nearest"))
    if len(result) != len(subset):
        raise ValueError("Both location-selection options must use identical station-winter cases.")
    result["same_grid_point"] = (np.isclose(result.grid_lat_land, result.grid_lat_nearest, atol=1e-6, rtol=0)
                                  & np.isclose(result.grid_lon_land, result.grid_lon_nearest, atol=1e-6, rtol=0))
    result["absolute_error_change_nearest_minus_land"] = result.error_days_nearest.abs() - result.error_days_land.abs()
    stats = []
    for selection in ["land", "nearest"]:
        errors = result[f"error_days_{selection}"]
        stats.append({"selection": selection, "n_station_winters": len(result), "n_stations": result.station_id.nunique(),
                      "pilot_winters": "1995;2025", "mean_observed_snow_days": result.observed_days_06utc.mean(),
                      "mean_model_snow_days": result[f"model_days_06utc_{selection}"].mean(),
                      "bias_days": errors.mean(), "mae_days": errors.abs().mean(),
                      "rmse_days": np.sqrt(np.mean(errors ** 2)),
                      "mean_grid_distance_km": result[f"grid_distance_km_{selection}"].mean(),
                      "same_grid_point_cases": int(result.same_grid_point.sum())})
    metrics = pd.DataFrame(stats)
    result.to_csv(root / "data/processed/snow_grid_selection_pilot.csv", index=False)
    metrics.to_csv(root / "data/processed/snow_grid_selection_metrics.csv", index=False)
    return result, metrics


if __name__ == "__main__":
    root = project_root(Path(__file__).resolve().parent)
    models = download_nearest_pilot(root)
    cases, metrics = compare_selections(root, models)
    print(metrics.to_string(index=False), flush=True)
