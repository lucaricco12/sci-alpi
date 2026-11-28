import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import verify_resort_coordinates as vrc  # noqa: E402


def page(country, region, points):
    """Minimal 'arrival by car' page in the structure that parse_arrival_page expects."""
    destinations = "".join(
        f'<strong> Destination </strong><ul><li><a title="Lift {i}" href="/lift/{i}/">Lift</a></li>'
        f'<li><a href="https://www.google.com/maps?q={lat},{lon}">View on Google Maps</a></li></ul>'
        for i, (lat, lon) in enumerate(points, start=1))
    return (f'<ul class="breadcrumb breadcrumbDetailpage"><li><span itemprop="name">Worldwide</span></li>'
            f'<li><span itemprop="name">Europe</span></li><li><span itemprop="name">{country}</span></li>'
            f'<li><span itemprop="name">{region}</span></li></ul>{destinations}')


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class VerifyTests(unittest.TestCase):
    def test_country_and_classification(self):
        self.assertEqual(vrc.source_country("Worldwide > Europe > Switzerland > Valais"), "CH")
        self.assertIsNone(vrc.source_country("Worldwide > Europe"))
        self.assertIsNone(vrc.source_country("Worldwide > Europe > Atlantis > X"))
        self.assertEqual(vrc.classify(0.0), "confirmed")
        self.assertEqual(vrc.classify(5.0), "confirmed")
        self.assertEqual(vrc.classify(5.1), "review")
        self.assertEqual(vrc.classify(7.0), "review")
        self.assertEqual(vrc.classify(7.1), "mismatch")

    def test_verify_one_uses_the_nearest_access_point_not_the_first(self):
        row = pd.DataFrame([{"resort_id": "a", "country_memberships": "CH;IT", "latitude": 46.0, "longitude": 8.0}]).itertuples(index=False).__next__()
        evidence = [
            {"access_point_index": 1, "access_latitude": 47.0, "access_longitude": 8.0, "breadcrumb": "Worldwide > Europe > Italy > Aosta",
             "source_url": "u", "retrieved_utc": "t", "response_sha256": "h"},
            {"access_point_index": 2, "access_latitude": 46.01, "access_longitude": 8.0, "breadcrumb": "Worldwide > Europe > Italy > Aosta",
             "source_url": "u", "retrieved_utc": "t", "response_sha256": "h"},
        ]
        result = vrc.verify_one(row, evidence)
        self.assertEqual(result["status"], "confirmed")
        self.assertLess(result["nearest_access_km"], 2)
        self.assertGreater(result["first_access_km"], 100)
        self.assertTrue(result["country_match"])
        self.assertEqual(result["source_region"], "Aosta")
        with self.assertRaises(ValueError):
            vrc.verify_one(row, [])

    def test_run_end_to_end_with_one_bad_page(self):
        pages = {
            "ok": page("Switzerland", "Valais", [(46.0, 7.0)]),
            "far": page("Austria", "Tyrol", [(47.0, 11.0), (47.1, 11.1)]),
            "wrongcountry": page("France", "Savoie", [(45.5, 6.5)]),
            "broken": "<html>no breadcrumb, no destination</html>",
        }
        stored = {"ok": (46.01, 7.0, "CH"), "far": (48.5, 14.0, "AT"), "wrongcountry": (45.5, 6.5, "IT"), "broken": (46.0, 8.0, "CH")}

        def fake_urlopen(request, timeout=0):
            for key, html in pages.items():
                if f"/{key}/" in request.full_url:
                    return FakeResponse(html.encode())
            raise AssertionError(request.full_url)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/processed").mkdir(parents=True)
            pd.DataFrame([{"resort_id": rid, "url": f"https://www.skiresort.com/en/ski-resort/{rid}/",
                           "country_memberships": c, "latitude": la, "longitude": lo}
                          for rid, (la, lo, c) in stored.items()]).to_csv(root / "data/processed/resorts_features.csv", index=False)
            with patch("resort_review.urlopen", fake_urlopen):
                result, errors = vrc.run(root, workers=1, interval=0.0)
            written = pd.read_csv(root / vrc.OUTPUT).set_index("resort_id")
            self.assertEqual(sorted(written.index), ["far", "ok", "wrongcountry"])
            self.assertEqual(written.loc["ok", "status"], "confirmed")
            self.assertEqual(written.loc["far", "status"], "mismatch")
            self.assertFalse(written.loc["wrongcountry", "country_match"])
            self.assertEqual([e["resort_id"] for e in errors], ["broken"])
            self.assertTrue((root / vrc.ERRORS).is_file())
            counts, wrong = vrc.summary(result)
            self.assertEqual(counts, {"confirmed": 2, "mismatch": 1})
            self.assertEqual(wrong, ["wrongcountry"])
            # second run: pages come from the cache, nothing is downloaded again
            with patch("resort_review.urlopen", side_effect=AssertionError("must use the cache")):
                result_again, errors_again = vrc.run(root, workers=1, interval=0.0)
            self.assertEqual(len(result_again), 3)
            self.assertEqual([e["resort_id"] for e in errors_again], ["broken"])  # the broken page has no cache: tries again


if __name__ == "__main__":
    unittest.main()
