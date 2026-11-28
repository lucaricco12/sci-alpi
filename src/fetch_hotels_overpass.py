"""Count 4- and 5-star hotels within 10 km of each resort (OpenStreetMap, Overpass API).

Usage (run in the Codespace, from the repository root, after notebook 02.4):

    python src/fetch_hotels_overpass.py

Input : data/processed/resorts_features.csv  (columns resort_id, latitude, longitude)
Output: data/processed/hotels_overpass.csv   (one row per resort_id)

Why: the old column ``hotels_4_5_star_10km`` was NOT measured. It was a formula of slope length and
ticket price (all 300 values reproduce ``round(slope_km / 30 + price_day_eur / 25 - 2)``).
It was removed in notebook 02.4. This script produces the real counts.

Method: one Overpass request for the bounding box of all resorts: nodes AND ways with
tourism=hotel and a ``stars`` tag starting with 4 or 5 (ways use their centre point). The count per
resort is the number of such hotels within a great-circle distance of 10 km.
Hotels that carry no stars tag in OpenStreetMap are not counted, so the numbers are a lower bound.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw" / "overpass"
OUT = PROCESSED / "hotels_overpass.csv"

EARTH_RADIUS_KM = 6371.0088
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "ZHAW-AlpineSkiResearch-StudentProject/1.0 (course project)"


def to_unit_vectors(latlon_deg: np.ndarray) -> np.ndarray:
    lat = np.radians(latlon_deg[:, 0])
    lon = np.radians(latlon_deg[:, 1])
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def count_within_km(resorts_latlon: np.ndarray, hotels_latlon: np.ndarray, radius_km: float = 10.0) -> list[int]:
    """Number of hotels within ``radius_km`` (great-circle distance) of each resort."""
    if len(hotels_latlon) == 0:
        return [0] * len(resorts_latlon)
    chord = 2.0 * np.sin(radius_km / (2.0 * EARTH_RADIUS_KM))   # distance between unit vectors
    tree = cKDTree(to_unit_vectors(hotels_latlon))
    hits = tree.query_ball_point(to_unit_vectors(resorts_latlon), r=chord)
    return [len(h) for h in hits]


def build_query(south: float, west: float, north: float, east: float) -> str:
    box = f"({south:.3f},{west:.3f},{north:.3f},{east:.3f})"
    return (
        "[out:json][timeout:180];(\n"
        f'  node["tourism"="hotel"]["stars"~"^[45]"]{box};\n'
        f'  way["tourism"="hotel"]["stars"~"^[45]"]{box};\n'
        ");\nout center;"
    )


def elements_to_points(elements: list[dict]) -> np.ndarray:
    points = []
    for element in elements:
        if "lat" in element and "lon" in element:
            points.append((element["lat"], element["lon"]))
        elif "center" in element:
            points.append((element["center"]["lat"], element["center"]["lon"]))
    return np.array(points, dtype=float).reshape(-1, 2)


def request_hotels(query: str) -> dict:
    import requests

    last_error = None
    for endpoint in ENDPOINTS:
        try:
            response = requests.post(endpoint, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=200)
            if response.status_code == 200:
                return {"endpoint": endpoint, "payload": response.json()}
            last_error = f"{endpoint}: HTTP {response.status_code}"
        except Exception as error:  # network problems are reported, never hidden
            last_error = f"{endpoint}: {error}"
    raise RuntimeError(f"Overpass request failed ({last_error}). Try again later.")


def main() -> int:
    resorts = pd.read_csv(PROCESSED / "resorts_features.csv")
    resorts = resorts.dropna(subset=["latitude", "longitude"])
    margin = 0.2   # degrees, a bit more than 10 km
    query = build_query(resorts.latitude.min() - margin, resorts.longitude.min() - margin,
                        resorts.latitude.max() + margin, resorts.longitude.max() + margin)
    print(f"Requesting hotels for {len(resorts)} resorts ...")
    result = request_hotels(query)
    elements = result["payload"].get("elements", [])
    points = elements_to_points(elements)
    print(f"{len(points)} hotels with 4 or 5 stars received from {result['endpoint']}")
    if len(points) < 500:
        print("Warning: very few hotels returned; the server may have answered with a partial result. "
              "The file is NOT written.")
        return 1

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc)
    raw_text = json.dumps(result["payload"], ensure_ascii=False)
    (RAW_DIR / f"hotels_{stamp:%Y%m%d_%H%M%S}.json").write_text(raw_text, encoding="utf-8")

    counts = count_within_km(resorts[["latitude", "longitude"]].to_numpy(float), points, 10.0)
    table = pd.DataFrame({
        "resort_id": resorts["resort_id"].values,
        "hotels_4_5_star_10km": counts,
        "hotels_total_in_query": len(points),
        "query_utc": stamp.isoformat(timespec="seconds"),
        "response_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "source": "OpenStreetMap via Overpass API; tourism=hotel, stars 4-5; 10 km; lower bound",
    })
    table.to_csv(OUT, index=False)
    print(f"Written {OUT.relative_to(ROOT)}; median count = {np.median(counts):.0f}, max = {max(counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
