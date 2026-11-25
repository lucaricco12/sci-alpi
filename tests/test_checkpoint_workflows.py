"""Numerical, identity and geographic guards for Matthias's checkpoint work."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from checkpoint_database import build_crosswalk
from checkpoint_sample import validate_panel
from closure_locations import valid_municipal_candidate
from snow_checkpoint_map import point_feature
from snow_checkpoint_models import SEED, design_matrix, fit_regression, nominal_anova, station_quality
from snow_validation import compute_results, load_observations, pair_sources


class GeographicTests(unittest.TestCase):
    def candidate(self):
        return {"lat": "46.1", "lon": "10.2", "category": "boundary", "type": "administrative",
                "addresstype": "village", "place_rank": 16,
                "address": {"country_code": "it", "state": "Lombardia"}}

    def test_jsonv2_category_is_read(self):
        self.assertTrue(valid_municipal_candidate(self.candidate(), "Lombardia"))

    def test_region_centroid_and_wrong_country_are_rejected(self):
        value = self.candidate(); value.update(addresstype="state", place_rank=8)
        self.assertFalse(valid_municipal_candidate(value, "Lombardia"))
        value = self.candidate(); value["address"]["country_code"] = "fr"
        self.assertFalse(valid_municipal_candidate(value, "Lombardia"))
        self.assertFalse(valid_municipal_candidate(self.candidate(), "Abruzzo"))

    def test_point_order_and_missing_coordinates(self):
        feature = point_feature(46.1, 10.2, {"Name": "Test"})
        self.assertEqual(feature["geometry"]["coordinates"], [10.2, 46.1])
        with self.assertRaises(ValueError):
            point_feature(float("nan"), 10.2, {})


class RegressionTests(unittest.TestCase):
    def measured_fixture(self):
        height = np.linspace(1100., 2500., 20)
        noise = np.random.default_rng(13).normal(0, 2, 20)
        loss = 10 - 1.8 * (height - 1500) / 100 + noise
        loss[-1] += 25  # Makes a full-data prediction differ from a held-out one.
        return pd.DataFrame({"station_id": [f"s{i}" for i in range(20)], "elev_m": height,
                             "loss": loss, "country": "CH"})

    def test_elevation_units_and_country_interaction(self):
        data = pd.DataFrame({"height": [1500, 1700, 1400], "country": ["CH", "IT", "AT"]})
        design = design_matrix(data, "height", True, True)
        self.assertEqual(design.elevation_per_100m.tolist(), [0., 2., -1.])
        self.assertEqual(design.elevation_x_IT.tolist(), [0., 2., 0.])
        self.assertEqual(design.elevation_x_AT.tolist(), [0., 0., -1.])

    def test_heldout_predictions_match_independent_least_squares(self):
        data = self.measured_fixture()
        _, _, metrics, predictions = fit_regression(data, "loss", "elev_m", "test", "station_id")
        x = np.column_stack([np.ones(20), (data.elev_m.to_numpy() - 1500) / 100])
        expected = np.empty(20)
        baseline = np.empty(20)
        for train, test in KFold(5, shuffle=True, random_state=SEED).split(x):
            beta = np.linalg.lstsq(x[train], data.loss.to_numpy()[train], rcond=None)[0]
            expected[test] = x[test] @ beta
            baseline[test] = data.loss.to_numpy()[train].mean()
        np.testing.assert_allclose(predictions.heldout_prediction_days, expected)
        np.testing.assert_allclose(predictions.heldout_mean_baseline_days, baseline)
        self.assertAlmostEqual(metrics["rmse_5fold_days"], np.sqrt(np.mean((data.loss - expected)**2)))

    def test_country_model_cannot_be_estimated_from_swiss_only_data(self):
        with self.assertRaisesRegex(ValueError, "Swiss-only"):
            fit_regression(self.measured_fixture(), "loss", "elev_m", "bad", "station_id", include_country=True)

    def test_single_station_anova_group_is_not_reported_as_valid(self):
        data = pd.DataFrame({"loss": [1, 2, 3, 5, 6], "group": ["a", "a", "b", "b", "c"]})
        result = nominal_anova(data, "loss", "group", "test")
        self.assertEqual(result["status"], "insufficient_group_sizes")
        self.assertNotIn("p_value_nominal", result)


class DataIdentityTests(unittest.TestCase):
    def test_full_panel_has_exact_keys_and_missing_season_is_rejected(self):
        sample = pd.read_csv(ROOT / "data/processed/checkpoint_resorts_24.csv")
        panel = pd.read_csv(ROOT / "data/processed/model_resort_winters_checkpoint.csv")
        validate_panel(sample, panel)
        self.assertEqual(len(panel), 480)
        with self.assertRaisesRegex(ValueError, "20 target winters"):
            validate_panel(sample, panel.iloc[:-1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_panel(sample, pd.concat([panel, panel.iloc[[0]]]))

    def test_model_reference_identity_is_not_silently_moved(self):
        sample = pd.read_csv(ROOT / "data/processed/checkpoint_resorts_24.csv")
        panel = pd.read_csv(ROOT / "data/processed/model_resort_winters_checkpoint.csv")
        sample.loc[0, "lat"] += .1
        with self.assertRaisesRegex(ValueError, "coordinates differ"):
            validate_panel(sample, panel)

    def test_all_pilot_ids_resolve_without_doubling_cross_border_area(self):
        crosswalk = build_crosswalk(ROOT)
        self.assertEqual(len(crosswalk), 10)
        self.assertEqual(crosswalk.canonical_resort_id.nunique(), 9)
        gateways = crosswalk.loc[crosswalk.gateway_of_cross_border_area]
        self.assertEqual(len(gateways), 2)
        self.assertEqual(gateways.canonical_resort_id.nunique(), 1)

    def test_station_tests_use_station_units_not_repeated_seasons(self):
        pairs = pair_sources(load_observations(ROOT), pd.read_csv(ROOT / "data/processed/station_model_winters.csv"))
        _, changes, _ = compute_results(pairs)
        tests, uncertainty = station_quality(pairs, changes)
        self.assertTrue(tests.n_station_units.eq(20).all())
        self.assertEqual(len(pairs), 400)
        self.assertTrue(uncertainty.bootstrap_draws.eq(5000).all())

    def test_no_model_risk_labels_are_promoted(self):
        summary = pd.read_csv(ROOT / "data/processed/model_resort_summary_checkpoint.csv")
        self.assertTrue(summary.source_type.eq("unvalidated_era5_land_model").all())
        self.assertFalse(summary.risk_class_validated.any())
        self.assertNotIn("risk_class", summary.columns)

    def test_default_map_does_not_load_remote_scripts_or_styles(self):
        text = (ROOT / "docs/ski_resorts_closures_map.html").read_text()
        from html.parser import HTMLParser
        dependencies = []
        class Dependencies(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "script" and attrs.get("src"):
                    dependencies.append(attrs["src"])
                if tag == "link" and attrs.get("rel") == "stylesheet" and attrs.get("href"):
                    dependencies.append(attrs["href"])
        Dependencies().feed(text)
        self.assertEqual(dependencies, [])
        self.assertIn("MODEL SAMPLE ONLY", text)
        self.assertIn("Municipality/locality only", text)


if __name__ == "__main__":
    unittest.main()
