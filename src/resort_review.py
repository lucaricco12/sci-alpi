"""Resolve flagged resort identities without changing Lorenzo's source table.

Climate sites are unique source URLs; original price-market rows stay intact.
Reviewed coordinates identify a listed lift-access point, not a certified
measurement at the resort's minimum ski elevation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from snow_validation import RateLimiter, distance_km, project_root


class BreadcrumbParser(HTMLParser):
    """Read only the resort breadcrumb, excluding the page-wide navigation."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.named = False
        self.buffer = []
        self.names = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "ul":
            if self.depth:
                self.depth += 1
            elif "breadcrumbDetailpage" in attrs.get("class", "").split():
                self.depth = 1
        if self.depth and tag == "span" and attrs.get("itemprop") == "name":
            self.named = True
            self.buffer = []

    def handle_data(self, data):
        if self.named:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "span" and self.named:
            self.names.append(" ".join("".join(self.buffer).split()))
            self.named = False
        if tag == "ul" and self.depth:
            self.depth -= 1


def plain_text(value):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def parse_arrival_page(html):
    breadcrumb = BreadcrumbParser()
    breadcrumb.feed(html)
    points = []
    for block in re.findall(r"<strong>\s*Destination\s*</strong>\s*<ul>(.*?)</ul>", html, flags=re.S | re.I):
        links = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>', block, flags=re.I)
        coordinates = []
        for link in links:
            parsed = urlparse(unescape(link))
            if parsed.hostname not in {"www.google.com", "google.com"} or parsed.path != "/maps":
                continue
            q = parse_qs(parsed.query).get("q", [""])[0]
            if re.fullmatch(r"-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?", q):
                coordinates.append(tuple(map(float, q.split(","))))
        if len(coordinates) != 1:
            continue
        lat, lon = coordinates[0]
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Invalid source access-point coordinates.")
        lift_names = re.findall(r'<a\b[^>]*title="([^"]+)"', block, flags=re.I)
        points.append({"access_point_index": len(points) + 1,
                       "access_point_name": " | ".join(map(unescape, lift_names)),
                       "destination_description": plain_text(block).replace("View on Google Maps", "").strip(),
                       "access_latitude": lat, "access_longitude": lon})
    if not breadcrumb.names or not points:
        raise ValueError("Expected a resort breadcrumb and at least one explicitly listed lift-access point.")
    return breadcrumb.names, points


def fetch_evidence(root, row, limiter):
    root = Path(root)
    url = row.url.rstrip("/") + "/arrival-car/"
    raw = root / "data/raw/resort_location_review"
    raw.mkdir(parents=True, exist_ok=True)
    cache = raw / f"{row.resort_id}.html"
    metadata_file = cache.with_suffix(".json")
    if cache.is_file() and metadata_file.is_file():
        body = cache.read_bytes()
        meta = json.loads(metadata_file.read_text())
        if meta["url"] != url or meta["response_sha256"] != hashlib.sha256(body).hexdigest():
            raise ValueError("Source-page cache metadata does not match the retained HTML.")
    else:
        limiter.wait()
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (ZHAW student research; resort coordinate review)"})
        with urlopen(request, timeout=45) as response:
            body = response.read()
        meta = {"url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "response_sha256": hashlib.sha256(body).hexdigest()}
        cache.write_bytes(body)
        metadata_file.write_text(json.dumps(meta, indent=2) + "\n")
    crumbs, points = parse_arrival_page(body.decode("utf-8"))
    return [{"resort_id": row.resort_id, "url": row.url,
             "source_url": url, "retrieved_utc": meta["retrieved_utc"],
             "response_sha256": meta["response_sha256"],
             "breadcrumb": " > ".join(crumbs), **point} for point in points]


def download_flagged_evidence(root):
    root = Path(root)
    audit = pd.read_csv(root / "data/processed/snow_resort_input_review.csv")
    flagged = audit.loc[audit.requires_location_or_identity_review].drop_duplicates("url")
    limiter = RateLimiter(interval=1.1)
    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(fetch_evidence, root, row, limiter): row.resort_id
                for row in flagged.itertuples(index=False)}
        for future in as_completed(jobs):
            try:
                rows.extend(future.result())
            except Exception as error:
                errors.append({"resort_id": jobs[future], "error": str(error)})
            print(f"Resort source review: {len(rows)} access points; {len(errors)} page errors.", flush=True)
    if errors:
        pd.DataFrame(errors).to_csv(root / "data/raw/resort_location_review/errors.csv", index=False)
        raise RuntimeError("Some source pages need review. Published evidence was preserved; see data/raw/resort_location_review/errors.csv.")
    evidence = pd.DataFrame(rows).sort_values(["resort_id", "access_point_index"]).reset_index(drop=True)
    if set(evidence.resort_id) != set(flagged.resort_id):
        raise ValueError("Every flagged identity must have source evidence before publishing.")
    target = root / "data/processed/resort_location_evidence.csv"
    evidence.to_csv(target.with_suffix(".tmp"), index=False)
    target.with_suffix(".tmp").replace(target)
    return evidence


def build_roster(root):
    root = Path(root)
    audit = pd.read_csv(root / "data/processed/snow_resort_input_review.csv")
    evidence = pd.read_csv(root / "data/processed/resort_location_evidence.csv")
    decisions = pd.read_csv(root / "data/config/resort_scope_decisions.csv")
    if evidence.duplicated(["resort_id", "access_point_index"]).any() or decisions.resort_id.duplicated().any():
        raise ValueError("Source access points and scope decisions need unique keys.")
    flagged = set(audit.loc[audit.requires_location_or_identity_review, "resort_id"])
    if flagged != set(evidence.resort_id) or flagged != set(decisions.resort_id):
        raise ValueError("Every flagged resort needs evidence and an explicit scope decision.")
    if not decisions.scope_decision.isin(["in_alps", "outside_alps"]).all():
        raise ValueError("Unknown reviewed scope decision.")
    first = evidence.sort_values("access_point_index").drop_duplicates("resort_id")
    roster = audit.sort_values("source_csv_row").drop_duplicates("url").copy()
    memberships = audit.groupby("url").country.agg(lambda x: ";".join(sorted(set(x))))
    roster["country_memberships"] = roster.url.map(memberships)
    roster["country_for_analysis"] = np.where(roster.cross_border_url, "cross_border", roster.country)
    counts = audit.groupby("url").size()
    roster["source_row_count"] = roster.url.map(counts)
    roster = roster.merge(first.drop(columns="url"), on="resort_id", how="left", validate="one_to_one")
    roster = roster.merge(decisions, on="resort_id", how="left", validate="one_to_one")
    roster["scope_decision"] = roster.scope_decision.fillna("not_individually_reviewed")
    reviewed = roster.access_latitude.notna() & roster.access_longitude.notna()
    roster["original_latitude"] = roster.latitude
    roster["original_longitude"] = roster.longitude
    roster["latitude"] = roster.access_latitude.where(reviewed, roster.original_latitude)
    roster["longitude"] = roster.access_longitude.where(reviewed, roster.original_longitude)
    roster["coordinate_method"] = np.where(reviewed, "source_first_listed_lift_access", "original_geocode_not_rechecked")
    roster["coordinate_change_km"] = distance_km(roster.original_latitude, roster.original_longitude,
                                                roster.latitude, roster.longitude)
    roster["base_elevation_at_point_verified"] = False
    roster["include_in_alpine_candidate_set"] = roster.scope_decision.ne("outside_alps")
    roster["snow_method_validated"] = False
    columns = ["resort_id", "resort_name", "url", "country_memberships", "country_for_analysis", "source_row_count",
               "elevation_base_m", "elevation_top_m", "original_latitude", "original_longitude", "latitude", "longitude",
               "coordinate_method", "coordinate_change_km", "access_point_name", "destination_description",
               "source_url", "retrieved_utc", "response_sha256", "breadcrumb", "scope_decision", "scope_reason",
               "include_in_alpine_candidate_set", "base_elevation_at_point_verified", "snow_method_validated"]
    roster = roster[columns].sort_values("resort_id").reset_index(drop=True)
    if roster.resort_id.duplicated().any() or roster.url.duplicated().any():
        raise ValueError("Climate roster must contain one row per distinct resort source URL.")
    roster.to_csv(root / "data/processed/resorts_snow_roster.csv", index=False)
    return roster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Refresh source evidence for the flagged resorts.")
    args = parser.parse_args()
    root = project_root(Path(__file__).resolve().parent)
    if args.download:
        evidence = download_flagged_evidence(root)
        print(evidence.groupby("resort_id").first()[["breadcrumb"]].to_string())
    if (root / "data/config/resort_scope_decisions.csv").is_file():
        roster = build_roster(root)
        print(roster.groupby(["country_for_analysis", "scope_decision"]).size().to_string())
        print("Original source rows preserved. Candidate coordinates are not certified minimum-elevation snow sites.")


if __name__ == "__main__":
    main()
