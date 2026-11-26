"""Check credential replacement and useful diagnostics without secret output."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cds_errors import provider_detail, retrieval_error
from cerra_land import download_request, request_for_dates
from setup_cds import save_token


def http_error(status, detail):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({"detail": detail}).encode()
    response.headers["Content-Type"] = "application/json"
    return requests.HTTPError("Provider URL and private value must not be echoed: test-only-private-value", response=response)


class SetupReplacementTests(unittest.TestCase):
    def test_explicit_replacement_is_private_and_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            save_token("old-test-only-value", path)
            save_token("new-test-only-value", path, replace=True)
            self.assertIn('key: new-test-only-value\n', path.read_text())
            self.assertNotIn("old-test-only-value", path.read_text())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_invalid_replacement_preserves_previous_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            save_token("old-test-only-value", path)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                save_token("invalid replacement with spaces", path, replace=True)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_replacement_does_not_follow_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original"
            original.write_text("test-only-original")
            path = Path(directory) / ".cdsapirc"
            path.symlink_to(original)
            with self.assertRaisesRegex(ValueError, "link or special file"):
                save_token("new-test-only-value", path, replace=True)
            self.assertEqual(original.read_text(), "test-only-original")
            self.assertTrue(path.is_symlink())


class DownloadErrorTests(unittest.TestCase):
    def test_actual_provider_reason_is_available_without_credentials_or_urls(self):
        error = http_error(400, {"message": "No data found for requested date; synthetic-private-credential", "token": "nested-private-value", "download_url": "https://example.invalid/signed?secret=hidden"})
        output = retrieval_error(error, secret_values=("synthetic-private-credential",))
        self.assertIn("No data found for requested date", output)
        self.assertNotIn("synthetic-private-credential", output)
        self.assertNotIn("nested-private-value", output)
        self.assertNotIn("https://", output)

    def test_plain_text_errors_and_unlabelled_identifiers_are_redacted(self):
        response = requests.Response()
        response.status_code = 400
        response._content = b'No data found. https://example.invalid/signed?key=hidden Bearer hidden-value 00000000-0000-4000-8000-000000000000'
        output = provider_detail(response)
        self.assertIn("No data found", output)
        for private in ("https://", "hidden-value", "00000000-0000-4000-8000-000000000000"):
            self.assertNotIn(private, output)

    def test_large_provider_response_is_bounded(self):
        output = provider_detail(http_error(400, "Repeated error text " * 200).response)
        self.assertLessEqual(len(output), 800)

    def test_authentication_and_licence_have_different_instructions(self):
        authentication = retrieval_error(http_error(401, "Rejected token: test-only-private-value"))
        licence = retrieval_error(http_error(403, "required licences not accepted; test-only-private-value"))
        self.assertIn("HTTP 401", authentication)
        self.assertIn("--replace", authentication)
        self.assertIn("HTTP 403", licence)
        self.assertIn("Terms of use", licence)
        for output in (authentication, licence):
            self.assertNotIn("test-only-private-value", output)
            self.assertNotIn("Provider URL", output)

    def test_unknown_forbidden_does_not_assert_a_missing_licence(self):
        for detail in ("Access denied", "Licences accepted; a required profile field is missing"):
            with self.subTest(detail=detail):
                output = retrieval_error(http_error(403, detail))
                self.assertIn("Access was forbidden", output)
                self.assertNotIn("provider reports a licence/terms requirement", output)

    def test_rejected_request_exposes_only_allowlisted_field_names(self):
        output = retrieval_error(http_error(422, {"leadtime_hour": "invalid selection", "token": "test-only-private-value", "download_url": "https://example.invalid/signed?secret=test-only-private-value"}))
        self.assertIn("HTTP 422", output)
        self.assertIn("leadtime_hour", output)
        self.assertNotIn("test-only-private-value", output)
        self.assertNotIn("https://", output)
        self.assertNotIn("download_url", output)

    def test_limits_server_errors_and_transport_failures_are_distinguished(self):
        for error, expected in [
                (http_error(429, "Rate limit"), "rate or queue limit"),
                (http_error(503, "Service unavailable"), "service error"),
                (requests.Timeout("test-only-private-value"), "timeout interrupted"),
                (requests.ConnectionError("test-only-private-value"), "connection or timeout"),
                (ValueError("test-only-private-value"), "client failed")]:
            with self.subTest(expected=expected):
                output = retrieval_error(error)
                self.assertIn(expected, output)
                self.assertNotIn("test-only-private-value", output)

    def test_chained_http_response_is_classified_without_echoing_outer_error(self):
        outer = RuntimeError("test-only-private-value")
        outer.__cause__ = http_error(401, "Invalid token")
        output = retrieval_error(outer)
        self.assertIn("HTTP 401", output)
        self.assertNotIn("test-only-private-value", output)

    def test_failed_retrieval_keeps_published_data_and_returns_safe_reason(self):
        class FakeClient:
            def __init__(self, **options):
                pass

            def retrieve(self, *args):
                raise http_error(403, "required licences not accepted; test-only-private-value")

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"CDSAPI_KEY": "test-only-private-value"}), patch.dict(sys.modules, {"cdsapi": SimpleNamespace(Client=FakeClient)}):
            root = Path(directory)
            published = root / "data/processed/retained.csv"
            published.parent.mkdir(parents=True)
            published.write_bytes(b"test-only-published-results")
            with self.assertRaises(RuntimeError) as caught:
                download_request(root, request_for_dates(["2025-04-15"], 12))
            self.assertIn("HTTP 403", str(caught.exception))
            self.assertIn("Terms of use", str(caught.exception))
            self.assertNotIn("test-only-private-value", str(caught.exception))
            self.assertEqual(published.read_bytes(), b"test-only-published-results")
            self.assertEqual(list((root / "data/raw/cerra_land").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
