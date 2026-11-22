"""Compare alternative snow models on the same 40 station-winter cases.

This screening uses winters 1995 and 2021, when both public products
have data. It is not a substitute for validating the full target periods.
By default only saved tables are read. Download explicitly with --download.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from snow_validation import (RateLimiter, correlation, get_model_row,
                             load_observations, pair_sources, project_root)

SCREENING_WINTERS = (1995, 2021)
CANDIDATES = ("era5_land", "cerra")


def compare_candidates(root, candidate_models):
    root = Path(root)
    observations = load_observations(root)
    subset = observations.loc[observations.winter.isin(SCREENING_WINTERS)]
    if set(candidate_models.model) != set(CANDIDATES):
        raise ValueError("The screening must contain both candidate models.")
    cases, metrics = [], []
    for model in CANDIDATES:
        values = candidate_models.loc[candidate_models.model.eq(model)].copy()
        pairs = pair_sources(subset, values, model=model)
        errors = pairs.error_days.to_numpy()
        r, _ = correlation(pairs.observed_days_06utc, pairs.model_days_06utc)
        cases.append(pairs)
        metrics.append({"model": model, "n_station_winters": len(pairs),
                        "n_stations": pairs.station_id.nunique(),
                        "screening_winters": ";".join(map(str, SCREENING_WINTERS)),
                        "mean_observed_days": pairs.observed_days_06utc.mean(),
                        "mean_model_days": pairs.model_days_06utc.mean(),
                        "bias_days": errors.mean(), "mae_days": np.abs(errors).mean(),
                        "rmse_days": np.sqrt(np.mean(errors**2)), "pearson_r": r})
    return pd.concat(cases, ignore_index=True), pd.DataFrame(metrics)


def download_candidates(root):
    root = Path(root)
    observations = load_observations(root)
    stations = observations.drop_duplicates("station_id")
    baseline = pd.read_csv(root / "data/processed/station_model_winters.csv")
    baseline = baseline.loc[baseline.winter.isin(SCREENING_WINTERS)].copy()
    # Older published rows identify their settings in request_url rather than
    # separate columns. Validate those URLs before adding explicit labels.
    pair_sources(observations.loc[observations.winter.isin(SCREENING_WINTERS)], baseline)
    baseline["model"] = "era5_land"
    baseline["cell_selection"] = "land"
    rows, errors = baseline.to_dict("records"), []
    limiter = RateLimiter()
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(get_model_row, root, station, year, limiter,
                            model=model): (model, station.station_id, year)
                for model in CANDIDATES[1:]
                for station in stations.itertuples(index=False)
                for year in SCREENING_WINTERS}
        for future in as_completed(jobs):
            key = jobs[future]
            try:
                rows.append(future.result())
            except Exception as error:
                errors.append({"model": key[0], "station_id": key[1],
                               "winter": key[2], "error": str(error)})
            completed = len(rows) - len(baseline) + len(errors)
            if completed % 10 == 0:
                print(f"Model screening: {completed}/{len(jobs)} requests checked; {len(errors)} errors.", flush=True)
    if errors:
        error_file = root / "data/raw/snow_candidate_errors.csv"
        pd.DataFrame(errors).to_csv(error_file, index=False)
        raise RuntimeError("Incomplete candidate screening. Saved published tables were preserved; see data/raw/snow_candidate_errors.csv.")
    models = pd.DataFrame(rows).sort_values(["model", "station_id", "winter"]).reset_index(drop=True)
    compare_candidates(root, models)
    target = root / "data/processed/station_model_candidates.csv"
    temporary = target.with_suffix(".tmp")
    models.to_csv(temporary, index=False)
    temporary.replace(target)
    return models


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    models = (download_candidates(root) if args.download else
              pd.read_csv(root / "data/processed/station_model_candidates.csv"))
    cases, metrics = compare_candidates(root, models)
    cases.to_csv(root / "data/processed/snow_candidate_validation.csv", index=False)
    metrics.to_csv(root / "data/processed/snow_candidate_metrics.csv", index=False)
    print(metrics.to_string(index=False))
    print("Screening only: these two winters cannot establish the 20-winter climate result.")


if __name__ == "__main__":
    main()
