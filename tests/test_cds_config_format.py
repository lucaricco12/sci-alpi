"""Use the actual CDS parser/client to protect credential-file compatibility."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from setup_cds import API, repair_configuration, save_token


class ConfigurationRepairTests(unittest.TestCase):
    def test_repair_preserves_other_settings_is_private_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            token = "synthetic-current-token"
            path.write_text(f"url: {API}\nkey: {json.dumps(token)}\nverify: 1\n# retained comment\n")
            self.assertTrue(repair_configuration(path))
            self.assertEqual(path.read_text(), f"url: {API}\nkey: {token}\nverify: 1\n# retained comment\n")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            after = path.read_bytes()
            self.assertFalse(repair_configuration(path))
            self.assertEqual(path.read_bytes(), after)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_malformed_or_ambiguous_configuration_is_not_overwritten(self):
        cases = [f"url: {API}\n", 'key: "one"\nkey: "two"\n',
                 'key: "bad\\xescape"\n', 'key: "test\\nwith-newline"\n', 'key: ""\n']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            for value in cases:
                with self.subTest(case=cases.index(value)):
                    path.write_text(value)
                    before = path.read_bytes()
                    with self.assertRaises(ValueError):
                        repair_configuration(path)
                    self.assertEqual(path.read_bytes(), before)

    def test_repair_refuses_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "retained"
            target.write_text('key: "synthetic-only"\n')
            path = Path(directory) / ".cdsapirc"
            path.symlink_to(target)
            before = target.read_bytes()
            with self.assertRaises(ValueError):
                repair_configuration(path)
            self.assertEqual(target.read_bytes(), before)
            self.assertTrue(path.is_symlink())

    def test_new_input_cannot_save_literal_quote_marks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            for token in ('"synthetic-only"', "'synthetic-only'"):
                with self.assertRaisesRegex(ValueError, "surrounding quotes"):
                    save_token(token, path)
                self.assertFalse(path.exists())


@unittest.skipUnless(importlib.util.find_spec("cdsapi"), "Install optional CDS requirements to test the provider's parser/client")
class ProviderCredentialResolutionTests(unittest.TestCase):
    def assert_provider_reads_exact_token(self, path, expected):
        from cdsapi.api import get_url_key_verify, read_config
        self.assertEqual(read_config(path)["key"], expected)
        with patch.dict(os.environ, {"CDSAPI_RC": str(path)}, clear=True), patch(
                "requests.sessions.Session.request", side_effect=AssertionError("Unexpected HTTP in config-format test")) as network:
            # This is the same resolver called by CDS Client.__new__/__init__.
            # Avoid unrelated SDK startup/version checks, which can contact CDS.
            self.assertEqual(get_url_key_verify(API, None, None)[1], expected)
            network.assert_not_called()

    def test_fresh_setup_round_trips_through_real_provider_credential_resolver(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            save_token("synthetic-fresh-token", path)
            self.assert_provider_reads_exact_token(path, "synthetic-fresh-token")

    def test_replacement_round_trips_through_real_provider_credential_resolver(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            save_token("synthetic-older-token", path)
            save_token("synthetic-replacement-token", path, replace=True)
            self.assert_provider_reads_exact_token(path, "synthetic-replacement-token")

    def test_legacy_repair_round_trips_through_real_provider_credential_resolver(self):
        from cdsapi.api import read_config
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cdsapirc"
            token = "synthetic-legacy-token"
            path.write_text(f"url: {API}\nkey: {json.dumps(token)}\n")
            # Reproduce the original failure before proving the repair.
            self.assertNotEqual(read_config(path)["key"], token)
            repair_configuration(path)
            self.assert_provider_reads_exact_token(path, token)


if __name__ == "__main__":
    unittest.main()
