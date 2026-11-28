#!/usr/bin/env python3
"""Independent position check of ALL resorts against the Skiresort source page.

Why this script exists
----------------------
The resort positions come from name-based geocoding (Nominatim). Two geocoders that
search the same *name* can make the same mistake, so their agreement is not proof
(see notebook 02.4). The Skiresort page "arrival by car" lists, for every resort,
the explicitly named lift-access points with coordinates. Those are independent of
the name search. This script downloads that page for every resort (cached, polite
rate limit, robots.txt allows it), parses it with the already tested
``resort_review.parse_arrival_page`` and compares the access points with the
position that is currently stored in ``data/processed/resorts_features.csv``.

Run it in the Codespace (the sandbox of the assistant has no access to the site)::

    python src/verify_resort_coordinates.py            # all resorts, about 6 minutes
    python src/verify_resort_coordinates.py --limit 5  # quick test

Output: ``data/processed/resort_coordinate_verification.csv`` (one row per resort).
Notebook 02.4 reads that file when it is complete and upgrades the coordinate check.
Nothing is overwritten silently: the notebook documents every change.

Status of a resort:
    confirmed  the nearest access point is at most 5 km from the stored position
    review     between 5 and 7 km (village against lift base; look at the map if in doubt)
    mismatch   more than 7 km: the stored position is probably wrong

Why 7 km: in the first run on all 293 resorts the median distance was 0.9 km and 75 % were within
2.1 km. Above 5 km the cases fell into two groups: 8 between 5.1 and 6.3 km (a village geocoded
instead of the lift base) and 3 at 8.5, 14.9 and 42.7 km, which are clearly wrong positions (Pizol,
Sonnenkopf geocoded in the Lech area, Hoch-Ybrig geocoded in Obwalden). 7 km lies in the gap.
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resort_review import fetch_evidence  # noqa: E402
from snow_validation import RateLimiter, distance_km  # noqa: E402

CONFIRMED_KM = 5.0
MISMATCH_KM = 7.0
COUNTRY_CODES = {"Switzerland": "CH", "Austria": "AT", "France": "FR", "Italy": "IT",
                 "Germany": "DE", "Slovenia": "SI", "Liechtenstein": "LI"}
OUTPUT = "data/processed/resort_coordinate_verification.csv"
ERRORS = "data/raw/resort_location_review/errors_verification.csv"


def breadcrumb_parts(breadcrumb):
    """'Worldwide > Europe > Switzerland > Valais' -> ['Worldwide', 'Europe', 'Switzerland', 'Valais']."""
    return [part.strip() for part in str(breadcrumb).split(">") if part.strip()]


def source_country(breadcrumb):
    """Country code from the breadcrumb (third element), or None if not recognised."""
    parts = breadcrumb_parts(breadcrumb)
    return COUNTRY_CODES.get(parts[2]) if len(parts) > 2 else None


def classify(nearest_km):
    if nearest_km <= CONFIRMED_KM:
        return "confirmed"
    if nearest_km <= MISMATCH_KM:
        return "review"
    return "mismatch"


def verify_one(row, evidence):
    """Compare one stored position with all access points listed on the source page.

    ``row`` needs resort_id, country_memberships, latitude, longitude.
    ``evidence`` is the list of dicts returned by ``resort_review.fetch_evidence``.
    """
    if not evidence:
        raise ValueError(f"No access point for {row.resort_id}")
    points = pd.DataFrame(evidence).sort_values("access_point_index")
    d = distance_km(float(row.latitude), float(row.longitude),
                    points["access_latitude"].to_numpy(float), points["access_longitude"].to_numpy(float))
    nearest = int(np.argmin(d))
    centroid_lat, centroid_lon = points["access_latitude"].mean(), points["access_longitude"].mean()
    breadcrumb = points["breadcrumb"].iloc[0]
    country = source_country(breadcrumb)
    memberships = str(row.country_memberships).split(";")
    parts = breadcrumb_parts(breadcrumb)
    return {
        "resort_id": row.resort_id,
        "n_access_points": len(points),
        "stored_latitude": float(row.latitude), "stored_longitude": float(row.longitude),
        "nearest_access_km": round(float(d[nearest]), 2),
        "first_access_km": round(float(d[0]), 2),
        "centroid_km": round(float(distance_km(float(row.latitude), float(row.longitude), centroid_lat, centroid_lon)), 2),
        "first_access_latitude": float(points["access_latitude"].iloc[0]),
        "first_access_longitude": float(points["access_longitude"].iloc[0]),
        "nearest_access_latitude": float(points["access_latitude"].iloc[nearest]),
        "nearest_access_longitude": float(points["access_longitude"].iloc[nearest]),
        "breadcrumb": breadcrumb,
        "source_country": country,
        "country_match": (country in memberships) if country else np.nan,
        "source_region": parts[3] if len(parts) > 3 else "",
        "status": classify(float(d[nearest])),
        "source_url": points["source_url"].iloc[0],
        "retrieved_utc": points["retrieved_utc"].iloc[0],
        "response_sha256": points["response_sha256"].iloc[0],
    }


def run(root, workers=2, limit=None, interval=1.1):
    root = Path(root)
    resorts = pd.read_csv(root / "data/processed/resorts_features.csv")
    needed = {"resort_id", "url", "country_memberships", "latitude", "longitude"}
    if not needed <= set(resorts.columns):
        raise ValueError(f"resorts_features.csv misses columns: {sorted(needed - set(resorts.columns))}")
    if resorts["resort_id"].duplicated().any():
        raise ValueError("resort_id must be unique")
    if limit:
        resorts = resorts.head(limit)

    limiter = RateLimiter(interval=interval)
    rows, errors = [], []

    def work(row):
        return verify_one(row, fetch_evidence(root, row, limiter))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(work, row): row.resort_id for row in resorts.itertuples(index=False)}
        for future in as_completed(jobs):
            try:
                rows.append(future.result())
            except Exception as error:  # one broken page must not stop the other 292
                errors.append({"resort_id": jobs[future], "error": f"{type(error).__name__}: {error}"})
            print(f"Verified {len(rows)} resorts; {len(errors)} page errors.", flush=True)

    result = pd.DataFrame(rows).sort_values("resort_id").reset_index(drop=True)
    target = root / OUTPUT
    result.to_csv(target.with_suffix(".tmp"), index=False)
    target.with_suffix(".tmp").replace(target)
    error_file = root / ERRORS
    if errors:
        error_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(errors).sort_values("resort_id").to_csv(error_file, index=False)
    elif error_file.exists():
        error_file.unlink()
    return result, errors


def summary(result):
    counts = result["status"].value_counts().to_dict()
    wrong_country = result.loc[result["country_match"] == False, "resort_id"].tolist()  # noqa: E712
    return counts, wrong_country


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="only the first N resorts (test run)")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result, errors = run(root, workers=args.workers, limit=args.limit)
    counts, wrong_country = summary(result)
    print("Status:", counts)
    print("Source country differs from stored country:", wrong_country or "none")
    for item in result.loc[result["status"] == "mismatch", ["resort_id", "nearest_access_km", "source_region"]].itertuples(index=False):
        print("  MISMATCH", item.resort_id, f"{item.nearest_access_km} km", item.source_region)
    if errors:
        print(f"{len(errors)} pages failed, see {ERRORS}. Run the script again: finished pages come from the cache.")
        sys.exit(1)


if __name__ == "__main__":
    main()
