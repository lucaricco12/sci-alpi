"""Read-only queue comparison; never submit, download, dismiss or delete jobs."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from cds_errors import provider_detail

DATASET = "reanalysis-cerra-land"


def canonical(value):
    """Compare full recorded selections, ignoring dict/list ordering only."""
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((canonical(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def verified_probe_cache(root, probe):
    identity = hashlib.sha256(json.dumps({"dataset": DATASET, "request": probe}, sort_keys=True).encode()).hexdigest()[:20]
    target = Path(root) / "data/raw/cerra_land" / f"{identity}.grib"
    try:
        receipt = json.loads(target.with_suffix(".json").read_text())
        inspection = json.loads(target.with_suffix(".inspection.json").read_text())
        if not isinstance(receipt, dict) or not isinstance(inspection, dict):
            return False
        with target.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        return (target.stat().st_size > 0 and all(
            item.get("dataset") == DATASET and item.get("request") == probe
            and item.get("response_sha256") == digest for item in (receipt, inspection))
            and inspection.get("fields_checked") == 1
            and inspection.get("status", "").startswith("file_structure_checked"))
    except (OSError, ValueError, TypeError):
        return False


def read_queue(client, root, probe):
    api = getattr(client, "client", None)
    if api is None or not hasattr(api, "get_jobs"):
        raise RuntimeError("Install the current optional CDS client from requirements-cerra-land.txt.")
    jobs = api.get_jobs(limit=50, sortby="created", status=["accepted", "running"])
    rows = jobs.json.get("jobs", [])
    cached = verified_probe_cache(root, probe)
    output = ["READ-ONLY CERRA-Land queue check. No jobs will be cancelled or submitted.",
              "Configured one-field probe has a matching inspected cache: " + ("YES" if cached else "NO")]
    groups, completed_probe_copies, count = {}, [], 0
    fields = ("variable", "level_type", "product_type", "year", "month", "day", "time", "leadtime_hour", "data_format", "area", "grid")
    for job in rows:
        if job.get("processID") and job["processID"] != DATASET:
            continue
        if not job.get("jobID"):
            continue
        metadata = api.get_remote(job["jobID"]).json
        if metadata.get("processID") != DATASET or metadata.get("status") not in ("accepted", "running"):
            continue
        count += 1
        output.append(f"#{count}: {metadata['status']}; submitted {metadata.get('created', 'unknown')}")
        request_wrapper = (metadata.get("metadata") or {}).get("request")
        request = request_wrapper.get("ids") if isinstance(request_wrapper, dict) else None
        if not isinstance(request, dict) or not request:
            output.append("  Recorded selection unavailable; no duplicate conclusion for this job.")
            continue
        safe = {key: request[key] for key in fields if key in request}
        text = provider_detail(SimpleNamespace(json=lambda: {"context": safe}), (getattr(client, "key", None),))
        output.append("  Selection: " + text)
        fingerprint = json.dumps(canonical(request), sort_keys=True)
        if fingerprint in groups:
            output.append(f"  SAME RECORDED SELECTION as #{groups[fingerprint]}.")
        else:
            groups[fingerprint] = count
        if cached and canonical(request) == canonical(probe):
            completed_probe_copies.append(count)
            output.append("  MATCHES THE ALREADY CACHED, INSPECTED ONE-FIELD PROBE.")
    output.append(f"Active CERRA-Land jobs inspected: {count}.")
    if completed_probe_copies:
        output.append("Active copies of the completed probe: " + ", ".join(f"#{i}" for i in completed_probe_copies) + ".")
    if len(rows) >= 50:
        output.append("Only the first 50 active jobs across datasets were checked; this may be a partial view.")
    output.append("Nothing was cancelled or downloaded. Compare these results before changing the queue.")
    return "\n".join(output)
