"""Protect source identity, model isolation and reviewed location evidence."""
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from resort_review import build_roster, parse_arrival_page
from snow_validation import pair_sources, request_spec
from cerra_download_plan import build_plan, download_one, monthly_requests


class CandidateTests(unittest.TestCase):
    def test_model_choices_have_separate_cache_keys(self):
        station = SimpleNamespace(lat=46., lon=8., elev_m=1321)
        baseline, old_key = request_spec(station, 1995)
        candidate, new_key = request_spec(station, 1995, model="cerra")
        self.assertNotEqual(old_key, new_key)
        self.assertEqual(parse_qs(urlparse(baseline).query)["models"], ["era5_land"])
        self.assertEqual(parse_qs(urlparse(candidate).query)["models"], ["cerra"])

    def test_candidate_cannot_enter_original_model_validation(self):
        models = pd.DataFrame({"model": ["cerra"]})
        with self.assertRaisesRegex(ValueError, "mix different snow models"):
            pair_sources(pd.DataFrame(), models)


class CopernicusPlanTests(unittest.TestCase):
    def test_full_plan_uses_correct_seasons_and_real_calendar_dates(self):
        plan = build_plan()
        self.assertEqual(len(plan["pilot_requests"]), 10)
        self.assertEqual(len(plan["full_validation_requests"]), 100)
        leap = monthly_requests([1988])
        self.assertEqual(sum(len(item["request"]["day"]) for item in leap), 137)
        self.assertEqual(leap[0]["calendar_month"], "1987-12")
        self.assertEqual(leap[-1]["request"]["day"][-1], "15")
        self.assertEqual(leap[2]["request"]["day"][-1], "29")
        for item in plan["full_validation_requests"]:
            self.assertEqual(item["request"]["time"], ["06:00"])
            self.assertEqual(item["request"]["variable"], ["snow_depth"])
            self.assertNotIn("area", item["request"])

    def test_missing_credentials_stop_before_download_or_published_changes(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {}, clear=True), patch("pathlib.Path.home", return_value=Path(directory)):
            with self.assertRaisesRegex(RuntimeError, "credentials are not configured"):
                download_one(Path(directory), build_plan()["pilot_requests"][0])
            self.assertEqual(list(Path(directory).iterdir()), [])


class ResortReviewTests(unittest.TestCase):
    def test_only_explicit_destination_points_and_own_breadcrumb_are_read(self):
        html = '''<nav><span itemprop="name">Alps</span>
          <a href="https://www.google.com/maps?q=1,2">Unrelated map</a></nav>
          <ul class="breadcrumb breadcrumbDetailpage"><li><span itemprop="name">France</span></li>
          <li><ul><li><span itemprop="name">Savoie</span></li></ul></li></ul>
          <strong> Destination </strong><ul><li><a title="Test lift" href="/lift/1/">Lift</a></li>
          <li>Test village, France</li><li><a href="https://www.google.com/maps?q=45.2,6.5">View on Google Maps</a></li></ul>'''
        names, points = parse_arrival_page(html)
        self.assertEqual(names, ["France", "Savoie"])
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["access_latitude"], 45.2)
        self.assertEqual(points[0]["access_longitude"], 6.5)
        self.assertEqual(points[0]["access_point_name"], "Test lift")

    def test_unknown_page_structure_does_not_invent_a_coordinate(self):
        with self.assertRaisesRegex(ValueError, "explicitly listed"):
            parse_arrival_page('<ul class="breadcrumbDetailpage"><span itemprop="name">France</span></ul>')

    def test_deduplication_and_cross_border_rule_preserve_original_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/processed").mkdir(parents=True)
            (root / "data/config").mkdir()
            rows = []
            for index, country in enumerate(["CH", "IT"], start=2):
                rows.append({"source_csv_row": index, "resort_id": "test-area", "resort_name": "Test area",
                             "url": "https://www.skiresort.com/en/ski-resort/test-area/", "country": country,
                             "elevation_base_m": 1500, "elevation_top_m": 3000, "latitude": 40., "longitude": 15.,
                             "cross_border_url": True, "requires_location_or_identity_review": True})
            source = root / "data/processed/snow_resort_input_review.csv"
            pd.DataFrame(rows).to_csv(source, index=False)
            before = source.read_bytes()
            evidence = {"resort_id": "test-area", "url": rows[0]["url"], "access_point_index": 1,
                        "access_point_name": "Valley lift", "destination_description": "Village",
                        "access_latitude": 46., "access_longitude": 8., "source_url": rows[0]["url"] + "arrival-car/",
                        "retrieved_utc": "2026-11-22T00:00:00+00:00", "response_sha256": "a" * 64, "breadcrumb": "Switzerland"}
            pd.DataFrame([evidence]).to_csv(root / "data/processed/resort_location_evidence.csv", index=False)
            pd.DataFrame([{"resort_id": "test-area", "scope_decision": "in_alps", "scope_reason": "Reviewed"}]).to_csv(
                root / "data/config/resort_scope_decisions.csv", index=False)
            roster = build_roster(root)
            self.assertEqual(len(roster), 1)
            self.assertEqual(roster.country_for_analysis.iloc[0], "cross_border")
            self.assertEqual(roster.country_memberships.iloc[0], "CH;IT")
            self.assertEqual(roster.source_row_count.iloc[0], 2)
            self.assertEqual(roster.latitude.iloc[0], 46.)
            self.assertFalse(roster.base_elevation_at_point_verified.iloc[0])
            self.assertFalse(roster.snow_method_validated.iloc[0])
            self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
