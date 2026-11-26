import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cerra_land import request_for_dates
from cerra_queue import DATASET, read_queue, verified_probe_cache


def cache(root, probe):
    identity = hashlib.sha256(json.dumps({"dataset": DATASET, "request": probe}, sort_keys=True).encode()).hexdigest()[:20]
    target = Path(root) / "data/raw/cerra_land" / f"{identity}.grib"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"synthetic-test-cache-only")
    item = {"dataset": DATASET, "request": probe, "response_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    target.with_suffix(".json").write_text(json.dumps(item))
    target.with_suffix(".inspection.json").write_text(json.dumps({**item, "fields_checked": 1, "status": "file_structure_checked; accuracy_not_validated"}))
    return target


def client_for(requests):
    jobs, remotes = [], {}
    for index, request in enumerate(requests, 1):
        job_id = f"synthetic-job-{index}"
        jobs.append({"jobID": job_id, "processID": DATASET})
        metadata = {"processID": DATASET, "status": "accepted", "created": f"2026-11-26T0{index}:00:00Z", "metadata": {"request": {"ids": request}}}
        remotes[job_id] = SimpleNamespace(json=metadata, delete=Mock(), download=Mock())
    api = SimpleNamespace(get_jobs=Mock(return_value=SimpleNamespace(json={"jobs": jobs})), get_remote=Mock(side_effect=lambda job_id: remotes[job_id]), submit=Mock(), retrieve=Mock())
    return SimpleNamespace(client=api, key="synthetic-private-key"), remotes


class QueueTests(unittest.TestCase):
    def test_identical_active_probes_are_flagged_without_mutations(self):
        probe = request_for_dates(["2025-04-15"], 12)
        with tempfile.TemporaryDirectory() as directory:
            cache(directory, probe)
            client, remotes = client_for([probe, dict(reversed(list(probe.items())))])
            output = read_queue(client, directory, probe)
            self.assertIn("SAME RECORDED SELECTION as #1", output)
            self.assertIn("Active copies of the completed probe: #1, #2", output)
            self.assertNotIn("synthetic-private-key", output)
            client.client.submit.assert_not_called(); client.client.retrieve.assert_not_called()
            for remote in remotes.values():
                remote.delete.assert_not_called(); remote.download.assert_not_called()

    def test_useful_month_is_not_labelled_as_completed_probe(self):
        probe = request_for_dates(["2025-04-15"], 12)
        month = request_for_dates(["2024-12-01", "2024-12-02"])
        with tempfile.TemporaryDirectory() as directory:
            cache(directory, probe)
            client, _ = client_for([probe, month])
            output = read_queue(client, directory, probe)
            self.assertNotIn("SAME RECORDED", output)
            self.assertIn("Active copies of the completed probe: #1.", output)
            self.assertNotIn("completed probe: #1, #2", output)

    def test_missing_selection_is_not_assumed_to_be_duplicate(self):
        probe = request_for_dates(["2025-04-15"], 12)
        with tempfile.TemporaryDirectory() as directory:
            client, remotes = client_for([None, None])
            remotes['synthetic-job-2'].json['metadata']['request'] = None
            output = read_queue(client, directory, probe)
            self.assertIn("selection unavailable", output)
            self.assertNotIn("SAME RECORDED", output)

    def test_changed_cache_cannot_establish_completed_probe(self):
        probe = request_for_dates(["2025-04-15"], 12)
        with tempfile.TemporaryDirectory() as directory:
            target = cache(directory, probe)
            target.write_bytes(b"changed-synthetic-cache")
            self.assertFalse(verified_probe_cache(directory, probe))
            client, _ = client_for([probe, probe])
            output = read_queue(client, directory, probe)
            self.assertIn("SAME RECORDED", output)
            self.assertNotIn("Active copies of the completed probe:", output)


if __name__ == "__main__":
    unittest.main()
