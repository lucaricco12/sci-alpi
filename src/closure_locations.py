"""Geocode the extracted closure records to their municipalities/localities.

These points locate named municipalities, not the individual closed lifts.
Every original record is retained, including unresolved or rejected matches.
Raw responses are cached; Nominatim requests are sequential and paced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from snow_validation import project_root

API = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SCI-Alpi-ZHAW-research/1.0 (https://github.com/lucaricco12/sci-alpi)"


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", value)


def valid_municipal_candidate(candidate, region):
    address = candidate.get("address", {})
    try:
        lat, lon = float(candidate["lat"]), float(candidate["lon"])
    except (KeyError, ValueError, TypeError):
        return False
    if address.get("country_code") != "it" or not (35 <= lat <= 48.5 and 6 <= lon <= 19):
        return False
    if candidate.get("category", candidate.get("class")) not in {"boundary", "place"}:
        return False
    if candidate.get("addresstype") in {"state", "country", "county", "region"} or candidate.get("place_rank", 0) < 14:
        return False
    returned = normalize(address.get("state", "") + " " + address.get("region", ""))
    expected = normalize(region)
    aliases = {"valledaosta": ["aosta", "aoste"],
               "trentinoaltoadige": ["trentino", "sudtirol", "bolzano", "trento"],
               "friuliveneziagiulia": ["friuliveneziagiulia"]}
    choices = aliases.get(expected, [expected])
    return bool(expected) and any(choice and choice in returned for choice in choices)


class Geocoder:
    def __init__(self, root):
        self.folder = Path(root) / "data/raw/closure_geocoding"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.last_start = 0.

    def query(self, params):
        params = {**params, "format": "jsonv2", "countrycodes": "it", "addressdetails": 1,
                  "limit": 3, "accept-language": "it"}
        url = API + "?" + urlencode(params)
        cache_id = hashlib.sha256(url.encode()).hexdigest()[:20]
        path = self.folder / f"{cache_id}.json"
        if path.is_file():
            saved = json.loads(path.read_text())
            if saved.get("request_url") != url:
                raise ValueError("Geocoder cache key does not match its request.")
            return saved
        time.sleep(max(0., 1.15 - (time.monotonic() - self.last_start)))
        self.last_start = time.monotonic()
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=35) as response:
                body = response.read()
        except HTTPError as error:
            if error.code in {403, 429}:
                raise RuntimeError("Nominatim stopped the batch. Existing raw caches are retained; do not bypass its limit.") from error
            raise
        data = json.loads(body)
        if not isinstance(data, list):
            raise ValueError("Expected a list of Nominatim matches.")
        saved = {"request_url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                 "response_sha256": hashlib.sha256(body).hexdigest(), "candidates": data}
        path.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
        return saved

    def municipality(self, name, region):
        name = re.sub(r"\s*\([A-Z]{2,3}\)\s*", " ", name).strip()
        attempts = [{"city": name, "state": region, "country": "Italia"},
                    {"q": f"{name}, {region}, Italia"}]
        for params in attempts:
            saved = self.query(params)
            candidates = [c for c in saved["candidates"] if valid_municipal_candidate(c, region)]
            if candidates:
                first = candidates[0]
                return {"latitude": float(first["lat"]), "longitude": float(first["lon"]),
                        "geocode_status": "matched_municipality_approximate",
                        "matched_place": first["display_name"],
                        "osm_url": f"https://www.openstreetmap.org/{first['osm_type']}/{first['osm_id']}",
                        "request_url": saved["request_url"], "retrieved_utc": saved["retrieved_utc"],
                        "response_sha256": saved["response_sha256"]}
        return {"latitude": np.nan, "longitude": np.nan, "geocode_status": "unresolved",
                "matched_place": "", "osm_url": "", "request_url": saved["request_url"],
                "retrieved_utc": saved["retrieved_utc"], "response_sha256": saved["response_sha256"]}


def geocode_closures(root):
    root = Path(root)
    source = root / "data/processed/legambiente_closures.csv"
    original_bytes = source.read_bytes()
    original = pd.read_csv(source).fillna("")
    lookup = original[["comune", "region"]].drop_duplicates()
    alias_file = root / "data/config/closure_query_aliases.csv"
    aliases = {}
    if alias_file.is_file():
        configured = pd.read_csv(alias_file).fillna("")
        if configured.duplicated(["original_comune", "region"]).any():
            raise ValueError("Closure search aliases must have unique municipality/region keys.")
        aliases = {(r.original_comune, r.region): (r.query_name, r.basis) for r in configured.itertuples(index=False)}
    geocoder = Geocoder(root)
    rows = []
    for number, row in enumerate(lookup.itertuples(index=False), start=1):
        query_name, alias_basis = aliases.get((row.comune, row.region), (row.comune, "source name as written"))
        value = geocoder.municipality(query_name, row.region)
        rows.append({"comune": row.comune, "region": row.region, "geocode_query_name": query_name,
                     "query_alias_basis": alias_basis, **value})
        if number % 10 == 0 or number == len(lookup):
            matched = sum(r["geocode_status"].startswith("matched") for r in rows)
            print(f"Closure locations: {number}/{len(lookup)} municipality queries reviewed; {matched} matched.", flush=True)
    locations = pd.DataFrame(rows)
    result = original.merge(locations, on=["comune", "region"], how="left", validate="many_to_one")
    result.insert(0, "closure_id", [f"leg-{i+1:03d}" for i in range(len(result))])
    result["source_csv_sha256"] = hashlib.sha256(original_bytes).hexdigest()
    result["location_precision"] = "municipality_or_named_locality; not individual lift"
    result["attribution"] = "© OpenStreetMap contributors; ODbL / Nominatim"
    if len(result) != len(original) or source.read_bytes() != original_bytes:
        raise ValueError("The source closure records must be preserved exactly.")
    output = root / "data/processed/legambiente_closure_locations.csv"
    result.to_csv(output.with_suffix(".tmp"), index=False)
    output.with_suffix(".tmp").replace(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    if args.download:
        print(geocode_closures(root).geocode_status.value_counts().to_string())
    else:
        print(pd.read_csv(root / "data/processed/legambiente_closure_locations.csv").geocode_status.value_counts().to_string())
