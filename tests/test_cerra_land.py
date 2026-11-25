"""Protect the CERRA-Land source, valid times and unvalidated-data boundary."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cerra_land import (DATASET, build_plan, compare_winter, download_request,
                        expected_times, inspect_grib, monthly_requests,
                        request_for_dates, validate_header, validate_request)
from setup_cds import save_token
from snow_validation import load_observations, season_dates


class LandPlanTests(unittest.TestCase):
    def test_correct_product_and_all_original_periods_pass_official_constraints(self):
        plan = build_plan(ROOT)
        self.assertEqual(plan["dataset"], "reanalysis-cerra-land")
        self.assertEqual(len(plan["pilot_requests"]), 10)
        self.assertEqual(len(plan["full_validation_requests"]), 100)
        self.assertEqual(set(x["winter"] for x in plan["full_validation_requests"]),
                         set(range(1986, 1996)) | set(range(2016, 2026)))
        self.assertIn("pending", plan["status"])
        for item in plan["full_validation_requests"]:
            self.assertEqual(item["request"]["product_type"], ["forecast"])
            self.assertEqual(item["request"]["time"], ["03:00"])
            self.assertEqual(item["request"]["leadtime_hour"], ["3"])
            self.assertNotIn("area", item["request"])

    def test_noon_probe_means_valid_noon_and_full_season_handles_leap_year(self):
        request = request_for_dates(["2025-04-15"], valid_hour=12)
        self.assertEqual(request["time"], ["09:00"])
        self.assertEqual(expected_times(request).tolist(), [pd.Timestamp("2025-04-15T12:00Z")])
        items = monthly_requests(1988)
        times = pd.DatetimeIndex([t for item in items for t in expected_times(item["request"])])
        self.assertTrue(times.equals(season_dates(1988) + pd.Timedelta(hours=6)))
        self.assertEqual(len(times), 137)
        self.assertEqual(items[-1]["request"]["day"][-1], "15")

    def test_snow_analysis_and_area_subset_are_not_silently_accepted(self):
        folder = ROOT / "data/config/cerra_land_cds"
        form = json.loads((folder / "form.json").read_text())
        constraints = json.loads((folder / "constraints.json").read_text())
        request = request_for_dates(["2025-04-15"])
        request["product_type"] = ["analysis"]
        with self.assertRaisesRegex(ValueError, "unavailable"):
            validate_request(request, form, constraints)
        request = request_for_dates(["2025-04-15"])
        request["area"] = [48, 5, 44, 17]
        with self.assertRaisesRegex(ValueError, "unsupported"):
            validate_request(request, form, constraints)

    def test_missing_account_stops_without_creating_raw_files(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch("pathlib.Path.home", return_value=Path(directory)):
            with self.assertRaisesRegex(RuntimeError, "No private CDS credentials"):
                download_request(Path(directory), request_for_dates(["2025-04-15"]))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_cached_download_cannot_silently_change_model_or_hash(self):
        import hashlib
        request = request_for_dates(["2025-04-15"])
        identity = hashlib.sha256(json.dumps({"dataset": DATASET, "request": request}, sort_keys=True).encode()).hexdigest()[:20]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "data/raw/cerra_land"; folder.mkdir(parents=True)
            target = folder / f"{identity}.grib"; target.write_bytes(b"GRIB-test-only")
            receipt = target.with_suffix(".json")
            receipt.write_text(json.dumps({"dataset": DATASET, "request": request,
                                           "response_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))
            self.assertEqual(download_request(root, request), target)
            target.write_bytes(b"changed-test-file")
            with self.assertRaisesRegex(ValueError, "hash does not match"):
                download_request(root, request)


class CredentialTests(unittest.TestCase):
    def test_private_permissions_and_existing_configuration_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            save_token("test-only-token", path)
            before = path.read_bytes()
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertIn('key: "test-only-token"', path.read_text())
            with self.assertRaises(FileExistsError):
                save_token("another-test-only-token", path)
            self.assertEqual(path.read_bytes(), before)

    def test_newlines_or_empty_tokens_do_not_create_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            for token in ("", "test\nkey", "<PERSONAL-ACCESS-TOKEN>"):
                with self.assertRaises(ValueError):
                    save_token(token, path)
            self.assertFalse(path.exists())


class HeaderTests(unittest.TestCase):
    def header(self):
        return {"paramId": 3066, "units": "m", "typeOfLevel": "surface", "stepType": "instant",
                "validityDate": 20250415, "validityTime": 1200, "dataDate": 20250415,
                "dataTime": 900, "endStep": 3, "bitsPerValue": 24}

    def test_physical_depth_and_valid_time(self):
        allowed = expected_times(request_for_dates(["2025-04-15"], 12))
        self.assertEqual(validate_header(self.header(), allowed), allowed[0])
        for key, value in [("paramId", 228141), ("units", "kg m**-2"), ("stepType", "accum")]:
            header = {**self.header(), key: value}
            with self.assertRaisesRegex(ValueError, "physical snow depth"):
                validate_header(header, allowed)

    def test_forecast_start_cannot_be_mistaken_for_valid_time(self):
        allowed = expected_times(request_for_dates(["2025-04-15"], 12))
        with self.assertRaisesRegex(ValueError, "validity time"):
            validate_header({**self.header(), "dataTime": 1200}, allowed)

    def test_known_recent_precision_issue_is_blocked_but_constant_field_is_allowed(self):
        allowed = expected_times(request_for_dates(["2025-04-15"], 12))
        with self.assertRaisesRegex(ValueError, "precision issue"):
            validate_header({**self.header(), "bitsPerValue": 12}, allowed)
        self.assertEqual(validate_header({**self.header(), "bitsPerValue": 0}, allowed), allowed[0])


@unittest.skipUnless(importlib.util.find_spec("eccodes"), "Install optional requirements-cerra-land.txt to test GRIB decoding")
class RealGribDecoderTests(unittest.TestCase):
    def write_grib(self, path, dates, bits=24, missing=False, lambert=False):
        import eccodes as ec
        with Path(path).open("wb") as output:
            for date in dates:
                gid = ec.codes_grib_new_from_samples("regular_ll_sfc_grib2")
                try:
                    if lambert:
                        for key, value in {"gridType": "lambert", "Nx": 4, "Ny": 4,
                                           "latitudeOfFirstGridPointInDegrees": 46.,
                                           "longitudeOfFirstGridPointInDegrees": 8.,
                                           "LoVInDegrees": 8., "LaDInDegrees": 45.,
                                           "Latin1InDegrees": 30., "Latin2InDegrees": 60.,
                                           "DxInMetres": 5500., "DyInMetres": 5500.}.items():
                            ec.codes_set(gid, key, value)
                    for key, value in {"paramId": 3066, "dataDate": date, "dataTime": 900,
                                       "stepUnits": 1, "stepType": "instant", "step": 3,
                                       "bitsPerValue": bits}.items():
                        ec.codes_set(gid, key, value)
                    size = 16 if lambert else ec.codes_get_size(gid, "values")
                    values = np.linspace(.1, 1.2, size)
                    if missing:
                        ec.codes_set(gid, "bitmapPresent", 1)
                        values[:] = ec.codes_get(gid, "missingValue")
                    ec.codes_set_values(gid, values)
                    ec.codes_write(gid, output)
                finally:
                    ec.codes_release(gid)

    def test_actual_grib_round_trip_reads_nearest_values_and_retains_audit(self):
        stations = pd.DataFrame({"station_id": ["synthetic-A", "synthetic-B"], "lat": [46., 48.], "lon": [8., 10.]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.grib"
            self.write_grib(path, [20250415])
            result = inspect_grib(path, request_for_dates(["2025-04-15"], 12), stations)
            self.assertEqual(len(result), 2)
            self.assertTrue(result.model.eq("cerra_land").all())
            self.assertFalse(result.grid_elevation_verified.any())
            self.assertTrue(result.valid_time_utc.eq("2025-04-15T12:00:00+00:00").all())
            audit = json.loads(path.with_suffix(".inspection.json").read_text())
            self.assertEqual(audit["fields"][0]["bitsPerValue"], 24)

    def test_decoder_rejects_missing_dates_duplicate_fields_and_missing_values(self):
        stations = pd.DataFrame({"station_id": ["synthetic-A"], "lat": [46.], "lon": [8.]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.grib"
            self.write_grib(path, [20250415])
            with self.assertRaisesRegex(ValueError, "missing requested"):
                inspect_grib(path, request_for_dates(["2025-04-14", "2025-04-15"], 12), stations)
            self.write_grib(path, [20250415, 20250415])
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                inspect_grib(path, request_for_dates(["2025-04-15"], 12), stations)
            self.write_grib(path, [20250415], missing=True)
            with self.assertRaisesRegex(ValueError, "Missing or invalid"):
                inspect_grib(path, request_for_dates(["2025-04-15"], 12), stations)

    def test_lambert_grid_and_cached_station_order(self):
        stations = pd.DataFrame({"station_id": ["synthetic-A", "synthetic-B"], "lat": [46., 46.05], "lon": [8., 8.05]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-lambert.grib"
            self.write_grib(path, [20250415], lambert=True)
            cache = {}
            request = request_for_dates(["2025-04-15"], 12)
            first = inspect_grib(path, request, stations, cache).set_index("station_id").sort_index()
            second = inspect_grib(path, request, stations.iloc[::-1], cache).set_index("station_id").sort_index()
            pd.testing.assert_frame_equal(first, second)
            self.assertTrue(first.grid_distance_km.lt(5).all())
            audit = json.loads(path.with_suffix(".inspection.json").read_text())
            self.assertEqual(audit["fields"][0]["gridType"], "lambert")

    def test_actual_low_precision_grib_is_not_counted(self):
        stations = pd.DataFrame({"station_id": ["synthetic-A"], "lat": [46.], "lon": [8.]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-low-precision.grib"
            self.write_grib(path, [20250415], bits=12)
            with self.assertRaisesRegex(ValueError, "precision issue"):
                inspect_grib(path, request_for_dates(["2025-04-15"], 12), stations)


class MatchedScreeningTests(unittest.TestCase):
    def panel(self):
        stations = load_observations(ROOT).drop_duplicates("station_id")
        return pd.DataFrame([{"station_id": row.station_id, "valid_time_utc": time.isoformat(),
                              "snow_depth_m": .4 if time.month == 12 else .2, "grid_lat": row.lat,
                              "grid_lon": row.lon, "grid_id": "synthetic-grid", "grid_distance_km": 0.,
                              "model": "cerra_land"}
                             for row in stations.itertuples(index=False)
                             for time in season_dates(2025) + pd.Timedelta(hours=6)])

    def test_complete_same_winter_panel_matches_all_twenty_stations(self):
        comparison = compare_winter(ROOT, self.panel(), 2025)
        self.assertEqual(len(comparison), 20)
        self.assertTrue(comparison.cerra_land_days_06utc.eq(31).all())
        self.assertTrue(comparison.cerra_land_error_days.eq(31 - comparison.snow_days_30cm).all())
        self.assertFalse(comparison.grid_elevation_verified.any())
        self.assertFalse(any("risk" in key for key in comparison))

    def test_missing_day_noon_or_mixed_model_cannot_enter_counts(self):
        panel = self.panel()
        with self.assertRaisesRegex(ValueError, "complete 06 UTC"):
            compare_winter(ROOT, panel.iloc[1:].copy(), 2025)
        panel.loc[0, "valid_time_utc"] = "2024-12-01T12:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "complete 06 UTC"):
            compare_winter(ROOT, panel, 2025)
        panel.loc[0, "model"] = "cerra"
        with self.assertRaisesRegex(ValueError, "CERRA-Land"):
            compare_winter(ROOT, panel, 2025)


if __name__ == "__main__":
    unittest.main()
