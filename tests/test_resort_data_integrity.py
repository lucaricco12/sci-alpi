"""Integrity tests for the repaired resort tables (notebook 02.4).

Each test protects against an error that really happened in the first version of the data
(see docs/integration_log.md): invented rows, a fabricated hotel column, wrong or missing
coordinates, a name-based merge that lost the coordinates, and flags that do not match the data.
The tests accept the state before AND after the Codespace runs (re-parsed slopes, real hotel
counts, verified coordinates): they check that the flags tell the truth about the columns.
"""
import json
import sqlite3
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


class ResortDataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features = pd.read_csv(PROCESSED / "resorts_features.csv")
        cls.clean = pd.read_csv(PROCESSED / "resorts_clean.csv")
        cls.roster = pd.read_csv(PROCESSED / "resorts_snow_roster.csv")
        cls.status = json.loads((PROCESSED / "data_status.json").read_text())

    def test_one_row_per_resort_and_same_resorts_as_the_roster(self):
        f = self.features
        self.assertEqual(len(f), 293)
        self.assertTrue(f["resort_id"].is_unique)
        self.assertEqual(set(f["resort_id"]), set(self.roster["resort_id"]))
        self.assertEqual(set(f["resort_id"]), set(self.clean["resort_id"]))
        self.assertEqual(f["country"].value_counts().sum(), 293)
        self.assertTrue(f["country"].isin(["AT", "CH", "FR", "IT"]).all())

    def test_no_invisible_characters_and_no_dropped_snow_cannon_column(self):
        self.assertFalse(self.features["resort_name"].str.contains("​").any())
        self.assertNotIn("snow_cannons", self.features.columns)
        self.assertNotIn("snow_cannons", self.clean.columns)

    def test_coordinates_exist_for_every_resort_and_are_in_europe(self):
        f = self.features
        self.assertTrue(f[["latitude", "longitude"]].notna().all().all(), "merge by name lost coordinates once")
        self.assertTrue(f["latitude"].between(41, 49.5).all())
        self.assertTrue(f["longitude"].between(-2, 17).all())

    def test_distances_match_the_stored_coordinates(self):
        f = self.features
        d = haversine_km(f["latitude"], f["longitude"], 47.3769, 8.5417)
        self.assertLess(np.abs(d - f["dist_zurich_km"]).max(), 0.2)
        # Nara-Leontica was geocoded in Zurich; the Blenio valley is far away
        nara = f[f["resort_id"].str.startswith("nara-leontica")]
        self.assertEqual(len(nara), 1)
        self.assertGreater(nara["dist_zurich_km"].iloc[0], 50)

    def test_isolation_rule_every_analysis_area_has_a_neighbour_within_40_km(self):
        f = self.features
        lat, lon = f["latitude"].to_numpy(), f["longitude"].to_numpy()
        d = haversine_km(lat[:, None], lon[:, None], lat[None], lon[None])
        np.fill_diagonal(d, np.inf)
        nearest = d.min(axis=1)
        self.assertLess(np.abs(nearest - f["nearest_other_resort_km"]).max(), 0.1)
        self.assertLessEqual(nearest[f["in_alpine_analysis_set"].to_numpy(bool)].max(), 40)

    def test_analysis_set_is_the_candidate_set_without_review_flags(self):
        f = self.features
        flagged = f["alps_review_flag"].fillna("") != ""
        self.assertEqual(int(f["in_alpine_candidate_set"].sum()), int(self.roster["include_in_alpine_candidate_set"].sum()))
        self.assertTrue(((f["in_alpine_candidate_set"]) & ~flagged).equals(f["in_alpine_analysis_set"]))
        self.assertEqual(int(f["in_alpine_analysis_set"].sum()), 269)
        # areas outside the Alps by geography must not be in the analysis set
        for prefix in ["hochficht", "abetone", "lelex-crozet", "saint-lary-soulan", "font-romeu", "cimone-montecreto"]:
            rows = f[f["resort_id"].str.startswith(prefix)]
            self.assertEqual(len(rows), 1, prefix)
            self.assertFalse(bool(rows["in_alpine_analysis_set"].iloc[0]), prefix)

    def test_elevations_and_prices_are_plausible_and_complete(self):
        f = self.features
        self.assertTrue((f["elevation_base_m"] < f["elevation_top_m"]).all())
        self.assertTrue(f["elevation_base_m"].between(0, 3000).all() and f["elevation_top_m"].between(500, 4000).all())
        self.assertTrue(f["price_day_eur"].between(10, 300).all())
        self.assertTrue(f["price_source"].isin(["scraped", "manual_entry"]).all())
        self.assertLessEqual(int((f["price_source"] == "manual_entry").sum()), 2)

    def test_status_flags_tell_the_truth_about_the_columns(self):
        f = self.features
        self.assertEqual(sorted(f["slope_status"].unique()), self.status["slope_status"])
        self.assertEqual(sorted(f["hotels_status"].unique()), self.status["hotels_status"])
        # slope and lifts: unverified values must not be silently used as measured
        reparsed = f["slope_status"] == "reparsed"
        self.assertTrue(f.loc[reparsed, "slope_km"].notna().all())
        self.assertTrue(f.loc[~reparsed, "lifts_count"].isna().all(), "lifts_count was an artefact (12 for CH and IT)")
        self.assertTrue(f["slope_status"].isin(["reparsed", "unverified_old_parser"]).all())
        # hotels: not measured -> empty; measured -> non-negative integers
        measured = f["hotels_status"] == "openstreetmap_overpass"
        self.assertTrue(f.loc[~measured, "hotels_4_5_star_10km"].isna().all(), "hotel counts were once a formula of slope and price")
        self.assertTrue((f.loc[measured, "hotels_4_5_star_10km"].dropna() >= 0).all())
        self.assertTrue(f["hotels_status"].isin(["not_measured", "openstreetmap_overpass"]).all())

    def test_coordinate_check_uses_only_honest_labels(self):
        allowed = {"verified_access_point", "manual_correction", "geocoders_agree_not_independent",
                   "two_geocodes_differ_review", "single_geocode_only", "access_point_within_15km_review"}
        self.assertTrue(set(self.features["coordinate_check"].unique()) <= allowed)
        self.assertNotIn("two_geocodes_agree_5km", set(self.features["coordinate_check"]))

    def test_repair_audit_documents_the_changes(self):
        audit = pd.read_csv(PROCESSED / "resorts_repair_audit.csv")
        self.assertEqual(list(audit.columns), ["item", "action", "reason"])
        self.assertTrue(audit["reason"].notna().all() and (audit["reason"].str.len() > 10).all())
        for item in ["hotels_4_5_star_10km", "lifts_count", "snow_cannons", "slope_km"]:
            self.assertIn(item, set(audit["item"]))
        corrected = audit[audit["action"] == "corrected"]
        self.assertGreaterEqual(len(corrected), 20)

    def test_sqlite_table_matches_the_csv(self):
        db = ROOT / "db" / "sci_alpi.db"
        if not db.exists():
            self.skipTest("db/sci_alpi.db not built (run notebook 05)")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            table = pd.read_sql_query("SELECT resort_id, latitude, longitude, slope_status, hotels_status FROM resorts", con)
        finally:
            con.close()
        merged = table.merge(self.features[["resort_id", "latitude", "longitude", "slope_status", "hotels_status"]],
                             on="resort_id", suffixes=("_db", "_csv"), validate="1:1")
        self.assertEqual(len(merged), 293)
        self.assertLess(np.abs(merged["latitude_db"] - merged["latitude_csv"]).max(), 1e-9)
        self.assertTrue((merged["slope_status_db"] == merged["slope_status_csv"]).all())
        self.assertTrue((merged["hotels_status_db"] == merged["hotels_status_csv"]).all())


if __name__ == "__main__":
    unittest.main()
