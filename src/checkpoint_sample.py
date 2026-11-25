"""A transparent 24-resort, four-country model demonstration for the checkpoints.

Selection is fixed by named areas and elevation coverage before downloading
outcomes. These are model reference points, not validated base-elevation
measurements or a representative sample of all Alpine resorts.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from resort_review import fetch_evidence
from snow_validation import (WINTERS, RateLimiter, get_model_row, project_root,
                             request_spec, season_dates)

SAMPLE = {
    "CH": ["adelboden-lenk-chuenisbaergli-silleren-hahnenmoos-metsch", "arosa-lenzerheide",
           "diavolezza-lagalb", "flumserberg", "kleine-scheidegg-maennlichen-grindelwald-wengen", "saas-fee"],
    "IT": ["aprica", "bormio-cima-bianca", "livigno", "sulden-am-ortler-solda-allortles",
           "val-senales-glacier-schnalstaler-gletscher", "belpiano-schoeneben-malga-san-valentino-haideralm"],
    "AT": ["kitzski-kitzbuehel-kirchberg", "skiwelt-wilder-kaiser-brixental", "obertauern", "soelden",
           "hintertux-glacier-hintertuxer-gletscher", "gurgl-obergurgl-hochgurgl"],
    "FR": ["les-houches-saint-gervais-prarion-bellevue-chamonix", "les-2-alpes", "alpe-dhuez",
           "les-3-vallees-val-thorens-les-menuires-meribel-courchevel", "tignes-val-disere",
           "serre-chevalier-briancon-chantemerle-villeneuve-la-salle-le-monetier-les-bains"],
}


def prepare_sample(root):
    root = Path(root)
    roster = pd.read_csv(root / "data/processed/resorts_snow_roster.csv")
    rows = []
    limiter = RateLimiter(interval=2.5)
    for country, identifiers in SAMPLE.items():
        for identifier in identifiers:
            match = roster.loc[roster.resort_id.eq(identifier)]
            if len(match) != 1 or match.country_for_analysis.iloc[0] != country:
                raise ValueError(f"Sample identity is missing or ambiguous: {identifier}")
            row = match.iloc[0]
            points = fetch_evidence(root, row, limiter)
            first = min(points, key=lambda x: x["access_point_index"])
            if not (43 <= first["access_latitude"] <= 49 and 4 <= first["access_longitude"] <= 17):
                raise ValueError(f"Source access point is outside the Alpine screening box: {identifier}")
            rows.append({"resort_id": identifier, "name": row.resort_name, "country": country,
                         "elev_base_m": int(row.elevation_base_m), "elev_top_m": int(row.elevation_top_m),
                         "lat": first["access_latitude"], "lon": first["access_longitude"],
                         "source_url": row.url, "coordinate_source_url": first["source_url"],
                         "coordinate_source_sha256": first["response_sha256"],
                         "source_retrieved_utc": first["retrieved_utc"],
                         "access_point_name": first["access_point_name"],
                         "location_method": "source_first_listed_lift_access",
                         "base_elevation_at_point_verified": False,
                         "sample_design": "six named areas per country, chosen for elevation coverage before model outcomes",
                         "snow_method_validated": False})
            print(f"Sample source checked: {len(rows)}/24 — {identifier}", flush=True)
    sample = pd.DataFrame(rows)
    if sample.resort_id.duplicated().any() or not sample.country.value_counts().eq(6).all():
        raise ValueError("The checkpoint demonstration needs six unique areas in each country.")
    sample.to_csv(root / "data/processed/checkpoint_resorts_24.csv", index=False)
    return sample


def validate_panel(sample, panel):
    if panel.duplicated(["resort_id", "winter"]).any():
        raise ValueError("Duplicate resort-winter keys.")
    expected = {(r, w) for r in sample.resort_id for w in WINTERS}
    if set(zip(panel.resort_id, panel.winter)) != expected:
        raise ValueError("Every sampled area must have all 20 target winters.")
    metadata = sample.set_index("resort_id")
    for row in panel.itertuples(index=False):
        site = metadata.loc[row.resort_id]
        station = SimpleNamespace(lat=site.lat, lon=site.lon, elev_m=site.elev_base_m)
        url, _ = request_spec(station, row.winter)
        expected_params = parse_qs(urlparse(url).query)
        actual_params = parse_qs(urlparse(row.request_url).query)
        for key, value in expected_params.items():
            if key in {"latitude", "longitude"}:
                if key not in actual_params or not np.isclose(float(actual_params[key][0]), float(value[0]), rtol=0, atol=1e-8):
                    raise ValueError("Model coordinates differ from the reviewed sample point.")
            elif actual_params.get(key) != value:
                raise ValueError("Model dates or settings differ from the study definition.")
        days = len(season_dates(row.winter))
        if row.model_hours != 24 * days or row.model_observed_days != days:
            raise ValueError("Mismatched model request or incomplete season.")
        if row.country != site.country or row.query_elev_m != site.elev_base_m:
            raise ValueError("Model metadata differ from the selected source site.")
        for count in [row.model_days_06utc, row.model_days_daily_max]:
            if not np.isfinite(count) or int(count) != count or not 0 <= count <= days:
                raise ValueError("Invalid model snow-day count.")
        if row.model_days_daily_max < row.model_days_06utc:
            raise ValueError("Daily maximum cannot count fewer days than the morning reading.")


def download_panel(root, sample):
    root = Path(root)
    rows, errors = [], []
    limiter = RateLimiter(interval=0.8)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {}
        for row in sample.itertuples(index=False):
            station = SimpleNamespace(station_id=row.resort_id, lat=row.lat, lon=row.lon, elev_m=row.elev_base_m)
            for winter in WINTERS:
                jobs[pool.submit(get_model_row, root, station, winter, limiter)] = (row.resort_id, winter)
        for future in as_completed(jobs):
            identifier, winter = jobs[future]
            try:
                value = future.result()
                value["resort_id"] = value.pop("station_id")
                rows.append(value)
            except Exception as error:
                errors.append({"resort_id": identifier, "winter": winter, "error": str(error)})
            done = len(rows) + len(errors)
            if done % 20 == 0:
                print(f"Four-country model sample: {len(rows)}/{len(jobs)} complete; {len(errors)} errors.", flush=True)
    if errors:
        pd.DataFrame(errors).to_csv(root / "data/raw/checkpoint_model_errors.csv", index=False)
        raise RuntimeError("Incomplete sample download; successful raw caches retained and published panel preserved.")
    panel = pd.DataFrame(rows).merge(sample[["resort_id", "country"]], on="resort_id", validate="many_to_one")
    panel = panel.sort_values(["resort_id", "winter"]).reset_index(drop=True)
    validate_panel(sample, panel)
    target = root / "data/processed/model_resort_winters_checkpoint.csv"
    panel.to_csv(target.with_suffix(".tmp"), index=False)
    target.with_suffix(".tmp").replace(target)
    return panel


def summarize_panel(sample, panel):
    validate_panel(sample, panel)
    means = panel.groupby(["resort_id", "period"])[["model_days_daily_max", "model_days_06utc"]].mean().unstack()
    result = sample.copy().set_index("resort_id")
    for suffix, field in [("", "model_days_daily_max"), ("_06utc", "model_days_06utc")]:
        result["days_past" + suffix] = means[field]["past"]
        result["days_recent" + suffix] = means[field]["recent"]
        result["lost_snow_days" + suffix] = means[field]["past"] - means[field]["recent"]
    grids = panel.groupby("resort_id")[["grid_lat", "grid_lon"]].nunique()
    if grids.gt(1).any().any():
        raise ValueError("Returned model point changed between study winters; inspect before regression.")
    result = result.join(panel.drop_duplicates("resort_id").set_index("resort_id")[["grid_lat", "grid_lon", "grid_distance_km"]])
    result["source_type"] = "unvalidated_era5_land_model"
    result["risk_class_validated"] = False
    return result.reset_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    sample = prepare_sample(root) if args.prepare else pd.read_csv(root / "data/processed/checkpoint_resorts_24.csv")
    panel = download_panel(root, sample) if args.download else pd.read_csv(root / "data/processed/model_resort_winters_checkpoint.csv")
    summary = summarize_panel(sample, panel)
    summary.to_csv(root / "data/processed/model_resort_summary_checkpoint.csv", index=False)
    print(summary[["country", "name", "elev_base_m", "days_past", "days_recent", "lost_snow_days"]].round(2).to_string(index=False))
    print("MODEL DEMONSTRATION: not validated real-world resort risk or country climate effects.")


if __name__ == "__main__":
    main()
