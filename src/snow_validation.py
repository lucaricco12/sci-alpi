"""Matched ERA5-Land / MeteoSwiss snow-day validation for the SCI project.

Raw responses stay in data/raw/. Published tables are replaced only after all
20 stations have all 20 complete winters. Run from the repository root:
    python src/snow_validation.py --download
"""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

WINTERS = (*range(1986, 1996), *range(2016, 2026))
API = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-nime"


def project_root(start=None):
    start = Path(start or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "data/processed/meteoswiss_station_winters.csv").is_file():
            return candidate
    raise FileNotFoundError("Open this notebook inside the sci-alpi repository.")


def season_dates(winter):
    return pd.date_range(f"{winter - 1}-12-01", f"{winter}-04-15", tz="UTC")


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2-p1)/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(np.radians(lon2-lon1)/2)**2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def load_observations(root):
    data = pd.read_csv(Path(root) / "data/processed/meteoswiss_station_winters.csv")
    required = {"station_id", "winter", "period", "snow_days_30cm", "observed_days",
                "station_name", "lat", "lon", "elev_m", "source"}
    if not required.issubset(data):
        raise ValueError(f"Missing station columns: {required-set(data)}")
    if data.empty or data[list(required)].isna().any().any():
        raise ValueError("Station inputs are empty or incomplete.")
    if data.duplicated(["station_id", "winter"]).any():
        raise ValueError("Duplicate station-winter keys.")
    for _, group in data.groupby("station_id"):
        if len(group) != len(WINTERS) or set(group.winter) != set(WINTERS):
            raise ValueError("Each station must have the complete 20-winter panel.")
        if group[["lat", "lon", "elev_m", "station_name"]].nunique().gt(1).any():
            raise ValueError("Station metadata must be consistent across winters.")
    expected_period = np.where(data.winter.le(1995), "past", "recent")
    lengths = data.winter.map(lambda year: len(season_dates(year)))
    if not data.period.eq(expected_period).all() or not data.observed_days.eq(lengths).all():
        raise ValueError("Station periods or seasonal observation counts are inconsistent.")
    if not (data.snow_days_30cm.mod(1).eq(0) & data.snow_days_30cm.ge(0) & data.snow_days_30cm.le(lengths)).all():
        raise ValueError("Impossible observed snow-day counts.")
    if not data.source.eq("MeteoSwiss").all() or not data.elev_m.gt(1000).all():
        raise ValueError("Expected MeteoSwiss stations above 1,000 m.")
    return data.sort_values(["station_id", "winter"]).reset_index(drop=True)


def request_spec(station, winter, cell_selection="land", model="era5_land"):
    if cell_selection not in {"land", "nearest"}:
        raise ValueError("Use land or nearest for the snow-method comparison.")
    if model not in {"era5_land", "era5", "cerra"}:
        raise ValueError("Unknown snow-model candidate.")
    params = {
        "latitude": float(station.lat), "longitude": float(station.lon),
        "elevation": int(station.elev_m), "start_date": f"{winter-1}-12-01",
        "end_date": f"{winter}-04-15", "hourly": "snow_depth",
        "models": model, "timezone": "GMT", "cell_selection": cell_selection,
    }
    query = urlencode(params)
    return f"{API}?{query}", hashlib.sha256(query.encode()).hexdigest()[:16]


def summarize_hourly(payload, winter):
    if payload.get("error"):
        raise ValueError(payload.get("reason", "Weather API returned an error."))
    if payload.get("hourly_units", {}).get("snow_depth") != "m" or payload.get("utc_offset_seconds") != 0:
        raise ValueError("Expected snow depth in metres and UTC timestamps.")
    dates = season_dates(winter)
    expected = pd.date_range(dates[0], dates[-1] + pd.Timedelta(hours=23), freq="h")
    times = pd.to_datetime(payload["hourly"]["time"], utc=True)
    values = pd.Series(payload["hourly"]["snow_depth"], index=times, dtype="float64")
    if not values.index.equals(expected) or values.isna().any() or not np.isfinite(values).all() or values.lt(0).any():
        raise ValueError("Hourly snow season has missing, irregular or invalid observations.")
    morning = values.loc[values.index.hour == 6]
    daily_max = values.resample("D").max()
    if len(morning) != len(dates) or len(daily_max) != len(dates):
        raise ValueError("A morning observation is required for every seasonal date.")
    return {"model_days_06utc": int(morning.ge(0.30).sum()),
            "model_days_daily_max": int(daily_max.ge(0.30).sum()),
            "model_hours": len(values), "model_observed_days": len(morning),
            "grid_lat": float(payload["latitude"]), "grid_lon": float(payload["longitude"])}


class RateLimiter:
    """Space out starts across all workers, below the public API minute limit."""
    def __init__(self, interval=0.6):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_start = 0.0
        self.stopped = threading.Event()

    def wait(self):
        with self.lock:
            if self.stopped.is_set():
                raise RuntimeError("Download stopped after an API rate-limit response.")
            now = time.monotonic()
            delay = max(0.0, self.next_start - now)
            self.next_start = max(self.next_start, now) + self.interval
        if delay:
            time.sleep(delay)
        if self.stopped.is_set():
            raise RuntimeError("Download stopped after an API rate-limit response.")


def get_model_row(root, station, winter, limiter, cell_selection="land", model="era5_land"):
    url, cache_id = request_spec(station, winter, cell_selection=cell_selection, model=model)
    cache = Path(root) / "data/raw/open_meteo_validation" / f"{cache_id}.json"
    if cache.is_file():
        body = cache.read_bytes()
        summary = summarize_hourly(json.loads(body), winter)
    else:
        for attempt in range(3):
            limiter.wait()
            try:
                request = Request(url, headers={"User-Agent": "ZHAW-sci-alpi-station-validation/1.0"})
                with urlopen(request, timeout=45) as response:
                    body = response.read()
                summary = summarize_hourly(json.loads(body), winter)
                break
            except HTTPError as error:
                if error.code == 429:
                    limiter.stopped.set()
                    raise RuntimeError("API rate limit reached. Existing caches are retained; rerun later.") from error
                if error.code not in (500, 502, 503, 504) or attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
            except (TimeoutError, URLError):
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix(".tmp")
        temporary.write_bytes(body)
        temporary.replace(cache)
    return {"station_id": station.station_id, "winter": winter, "cell_selection": cell_selection, "model": model,
            "period": "past" if winter <= 1995 else "recent", "query_elev_m": int(station.elev_m),
            **summary, "grid_distance_km": float(distance_km(station.lat, station.lon, summary["grid_lat"], summary["grid_lon"])),
            "request_url": url, "response_sha256": hashlib.sha256(body).hexdigest()}


def download_models(root, workers=3):
    observations = load_observations(root)
    stations = observations.drop_duplicates("station_id")
    limiter = RateLimiter()
    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(get_model_row, root, station, winter, limiter): (station.station_id, winter)
                for station in stations.itertuples(index=False) for winter in WINTERS}
        for future in as_completed(jobs):
            station_id, winter = jobs[future]
            try:
                rows.append(future.result())
            except Exception as error:
                errors.append({"station_id": station_id, "winter": winter, "error": str(error)})
            completed = len(rows) + len(errors)
            if completed % 20 == 0 or completed == len(jobs):
                print(f"Station validation: {len(rows)}/{len(jobs)} complete, {len(errors)} errors.", flush=True)
    raw = Path(root) / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    if errors:
        pd.DataFrame(errors).to_csv(raw / "station_validation_download_errors.csv", index=False)
        raise RuntimeError(f"{len(errors)} station seasons failed. Published data were not replaced. See data/raw/station_validation_download_errors.csv.")
    models = pd.DataFrame(rows).sort_values(["station_id", "winter"]).reset_index(drop=True)
    # Check the full join before promoting the downloaded table.
    pair_sources(observations, models)
    output = Path(root) / "data/processed/station_model_winters.csv"
    temporary = output.with_suffix(".tmp")
    models.to_csv(temporary, index=False)
    temporary.replace(output)
    return models


def pair_sources(observations, models, cell_selection="land", model="era5_land"):
    if cell_selection not in {"land", "nearest"}:
        raise ValueError("Unknown snow validation cell selection.")
    if "cell_selection" in models and not models.cell_selection.eq(cell_selection).all():
        raise ValueError("Do not mix different weather-grid selections in one validation table.")
    if model not in {"era5_land", "era5", "cerra"}:
        raise ValueError("Unknown snow-model candidate.")
    if "model" in models and not models.model.eq(model).all():
        raise ValueError("Do not mix different snow models in one validation table.")
    keys = ["station_id", "winter", "period"]
    if models.duplicated(["station_id", "winter"]).any():
        raise ValueError("Duplicate model station-winter keys.")
    joined = observations.merge(models, on=keys, how="outer", validate="one_to_one", indicator=True)
    if not joined._merge.eq("both").all() or len(joined) != len(observations):
        raise ValueError("Observed and model panels must have exactly the same station-winter keys.")
    joined = joined.drop(columns="_merge").rename(columns={"snow_days_30cm": "observed_days_06utc"})
    if "request_url" in joined:
        for row in joined.itertuples(index=False):
            request = parse_qs(urlparse(row.request_url).query)
            expected = {"models": model, "hourly": "snow_depth", "timezone": "GMT",
                        "cell_selection": cell_selection, "start_date": f"{row.winter-1}-12-01", "end_date": f"{row.winter}-04-15"}
            if any(request.get(key) != [value] for key, value in expected.items()):
                raise ValueError("Model request settings or dates do not match the validation definition.")
            if (not np.isclose(float(request["latitude"][0]), row.lat, rtol=0, atol=1e-8)
                    or not np.isclose(float(request["longitude"][0]), row.lon, rtol=0, atol=1e-8)
                    or float(request["elevation"][0]) != row.elev_m):
                raise ValueError("Requested model coordinates/elevation differ from the measured station.")
    if not joined.observed_days.eq(joined.model_observed_days).all():
        raise ValueError("Model and observed seasons must contain the same number of days.")
    for column in ["model_days_06utc", "model_days_daily_max"]:
        if not (joined[column].notna() & joined[column].mod(1).eq(0) & joined[column].ge(0) & joined[column].le(joined.observed_days)).all():
            raise ValueError("Impossible model snow-day counts.")
    if not joined.model_hours.eq(joined.observed_days * 24).all() or not joined.query_elev_m.eq(joined.elev_m).all():
        raise ValueError("Incomplete model seasons or mismatched requested elevations.")
    joined["error_days"] = joined.model_days_06utc - joined.observed_days_06utc
    joined["daily_max_extra_days"] = joined.model_days_daily_max - joined.model_days_06utc
    if joined.daily_max_extra_days.lt(0).any():
        raise ValueError("A daily maximum cannot produce fewer snow days than the same day's morning reading.")
    return joined.sort_values(["station_id", "winter"]).reset_index(drop=True)


def correlation(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return np.nan, np.nan
    result = pearsonr(x, y)
    return float(result.statistic), float(result.pvalue)


def compute_results(pairs):
    metrics = []
    for period in ["all", "past", "recent"]:
        group = pairs if period == "all" else pairs.loc[pairs.period.eq(period)]
        error = group.error_days.to_numpy()
        r, _ = correlation(group.observed_days_06utc, group.model_days_06utc)
        metrics.append({"period": period, "n_station_winters": len(group), "n_stations": group.station_id.nunique(),
                        "bias_days": float(error.mean()), "mae_days": float(np.abs(error).mean()),
                        "rmse_days": float(np.sqrt(np.mean(error**2))), "pearson_r": r,
                        "mean_daily_max_extra_days": float(group.daily_max_extra_days.mean()),
                        "model_full_season_fraction": float(group.model_days_06utc.eq(group.observed_days).mean()),
                        "observed_full_season_fraction": float(group.observed_days_06utc.eq(group.observed_days).mean())})
    means = pairs.groupby(["station_id", "period"])[["observed_days_06utc", "model_days_06utc"]].mean().unstack()
    info = pairs.drop_duplicates("station_id")[["station_id", "station_name", "lat", "lon", "elev_m"]].set_index("station_id")
    changes = info.copy()
    for kind, column in [("observed", "observed_days_06utc"), ("model", "model_days_06utc")]:
        changes[f"{kind}_days_past"] = means[column]["past"]
        changes[f"{kind}_days_recent"] = means[column]["recent"]
        changes[f"{kind}_lost_days"] = means[column]["past"] - means[column]["recent"]
    changes["loss_error_days"] = changes.model_lost_days - changes.observed_lost_days
    changes["same_direction"] = np.sign(changes.model_lost_days) == np.sign(changes.observed_lost_days)
    r, p = correlation(changes.observed_lost_days, changes.model_lost_days)
    trend = pd.DataFrame([{"n_stations": len(changes), "mean_observed_lost_days": changes.observed_lost_days.mean(),
                           "mean_model_lost_days": changes.model_lost_days.mean(),
                           "mean_loss_error_days": changes.loss_error_days.mean(),
                           "loss_rmse_days": np.sqrt(np.mean(changes.loss_error_days**2)),
                           "loss_pearson_r": r, "loss_pearson_p_nominal": p,
                           "same_direction_stations": int(changes.same_direction.sum())}])
    return pd.DataFrame(metrics), changes.reset_index(), trend


def export_results(root, pairs):
    metrics, changes, trend = compute_results(pairs)
    output = Path(root) / "data/processed"
    pairs.to_csv(output / "snow_station_validation.csv", index=False)
    metrics.to_csv(output / "snow_validation_metrics.csv", index=False)
    changes.to_csv(output / "snow_station_changes.csv", index=False)
    trend.to_csv(output / "snow_validation_trend_metrics.csv", index=False)
    return metrics, changes, trend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Fetch missing station-model seasons, using cached responses when available.")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    observations = load_observations(root)
    models = download_models(root) if args.download else pd.read_csv(root / "data/processed/station_model_winters.csv")
    pairs = pair_sources(observations, models)
    metrics, changes, trend = export_results(root, pairs)
    print(metrics.to_string(index=False), flush=True)
    print(trend.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
