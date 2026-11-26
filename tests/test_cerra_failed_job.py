"""Existing-job diagnostics must preserve the real cause and never resubmit."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cds_errors import provider_detail
from cerra_land import DATASET, read_last_error


def rejection():
    response = requests.Response()
    response.status_code = 400
    response._content = json.dumps({"detail": "The job has been rejected", "traceback": "Example backend cause: missing archive field; synthetic-private-key", "token": "nested-private"}).encode()
    return requests.HTTPError("Generic private error", response=response)


class FailedJobTests(unittest.TestCase):
    def test_existing_server_logs_are_visible_but_private_values_are_not(self):
        remote = SimpleNamespace(json={"processID": DATASET, "status": "rejected", "metadata": {"log": [["2026-11-26", "Example detailed server reason synthetic-private-key"]]}}, get_results=Mock(side_effect=rejection()))
        api = SimpleNamespace(get_jobs=Mock(return_value=SimpleNamespace(json={"jobs": [{"jobID": "synthetic-job", "processID": DATASET}]})), get_remote=Mock(return_value=remote), submit=Mock())
        capture = io.StringIO()
        with redirect_stdout(capture):
            output = read_last_error(SimpleNamespace(client=api, key="synthetic-private-key"))
        self.assertIn("Example detailed server reason", capture.getvalue())
        self.assertNotIn("synthetic-private-key", output + capture.getvalue())
        api.submit.assert_not_called()

    @unittest.skipUnless(importlib.util.find_spec("cdsapi"), "Requires the optional official CDS SDK")
    def test_sdk_processing_failure_without_http_response_keeps_cause(self):
        from ecmwf.datastores.processing import ProcessingFailedError
        remote = SimpleNamespace(json={"processID": DATASET, "status": "failed"}, get_results=Mock(side_effect=ProcessingFailedError("Example processing cause: missing archive field; synthetic-private-key")))
        api = SimpleNamespace(get_jobs=Mock(return_value=SimpleNamespace(json={"jobs": [{"jobID": "synthetic-job", "processID": DATASET}]})), get_remote=Mock(return_value=remote), submit=Mock())
        with redirect_stdout(io.StringIO()):
            output = read_last_error(SimpleNamespace(client=api, key="synthetic-private-key"))
        self.assertIn("Example processing cause: missing archive field", output)
        self.assertNotIn("synthetic-private-key", output)
        api.submit.assert_not_called()

    def test_traceback_is_not_lost_when_generic_detail_exists(self):
        output = provider_detail(rejection().response, ("synthetic-private-key",))
        self.assertIn("Example backend cause: missing archive field", output)
        self.assertIn("The job has been rejected", output)
        self.assertNotIn("synthetic-private-key", output)
        self.assertNotIn("nested-private", output)

    def test_long_traceback_keeps_the_final_cause(self):
        response = requests.Response(); response.status_code = 400
        response._content = json.dumps({"detail": "The job has been rejected", "traceback": "Stack frame " * 200 + "Final example cause: unavailable archive date"}).encode()
        output = provider_detail(response)
        self.assertIn("Final example cause: unavailable archive date", output)
        self.assertLessEqual(len(output), 800)

    def test_existing_rejected_job_is_read_without_submission_or_download(self):
        remote = SimpleNamespace(json={"processID": DATASET, "status": "rejected", "created": "2026-11-26T12:00:00Z"}, get_results=Mock(side_effect=rejection()), download=Mock())
        api = SimpleNamespace(get_jobs=Mock(return_value=SimpleNamespace(json={"jobs": [{"jobID": "synthetic-job", "processID": DATASET}]})), get_remote=Mock(return_value=remote), submit=Mock(), retrieve=Mock())
        client = SimpleNamespace(key="synthetic-private-key", client=api)
        capture = io.StringIO()
        with redirect_stdout(capture):
            output = read_last_error(client)
        self.assertIn("missing archive field", output)
        self.assertNotIn("synthetic-private-key", output + capture.getvalue())
        api.submit.assert_not_called(); api.retrieve.assert_not_called(); remote.download.assert_not_called()
        api.get_jobs.assert_called_once_with(limit=10, sortby="-created", status=["failed", "rejected"])

    def test_other_dataset_and_active_jobs_are_not_treated_as_failure(self):
        api = SimpleNamespace(get_jobs=Mock(return_value=SimpleNamespace(json={"jobs": [{"jobID": "other", "processID": "other-dataset"}, {"jobID": "active", "processID": DATASET}]})), get_remote=Mock(return_value=SimpleNamespace(json={"processID": DATASET, "status": "running"})), submit=Mock())
        output = read_last_error(SimpleNamespace(client=api))
        self.assertIn("No failed/rejected", output)
        api.get_remote.assert_called_once_with("active")
        api.submit.assert_not_called()

    def test_no_history_stops_without_new_request(self):
        api = SimpleNamespace(get_jobs=Mock(return_value=SimpleNamespace(json={"jobs": []})), get_remote=Mock(), submit=Mock())
        self.assertIn("No new request", read_last_error(SimpleNamespace(client=api)))
        api.get_remote.assert_not_called(); api.submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
