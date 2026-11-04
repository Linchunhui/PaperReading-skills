"""Content-addressed stage reuse with retained invocation receipts and revalidation."""
import json
from pathlib import Path
import shutil
import tempfile
import uuid


def quarantine(runner, spec):
    local = runner.out / "cache" / (spec.stage_id + ".json")
    if not runner.shared_cache or not local.exists():
        return
    old = json.loads(local.read_text())
    entry = runner.shared_cache / runner.workflow_digest(old["key"])
    if entry.exists():
        destination = runner.shared_cache / "quarantined" / (entry.name + "-" + uuid.uuid4().hex)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            entry.rename(destination)
        except FileNotFoundError:
            pass


def import_cached(runner, spec, key, evidence, facts):
    if not runner.shared_cache:
        return None
    entry = runner.shared_cache / runner.workflow_digest(key)
    try:
        meta = json.loads((entry / "cache.json").read_text())
        if meta["key"] != key:
            return None
        audit = entry / "audit"
        for name, sha in meta["accepted_attempt"]["files_sha256"].items():
            if Path(name).name != name or runner.workflow_file_digest(audit / name) != sha:
                return None
        response = (audit / "final-response.txt").read_text()
        receipt = runner.invocation_receipt(audit, (audit / "stdout.jsonl").read_bytes(), response)
        saved_receipt = json.loads((audit / "receipt.json").read_text())
        if saved_receipt.get("returncode") != 0 or saved_receipt.get("call_id") != receipt["call_id"]:
            return None
        stage = runner.validate_stage(spec, json.loads(response), evidence, facts, call_ids=[receipt["call_id"]])
        target = runner.out / "calls" / spec.stage_id / ("reused-" + entry.name) / "attempt-1"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(audit, target, dirs_exist_ok=True)
        artifact = runner.out / "stages" / (spec.stage_id + ".json")
        runner.workflow_dump(artifact, stage)
        meta.update(artifact_sha256=runner.workflow_file_digest(artifact), cache_hit=True, reused_from=str(entry))
        meta["accepted_attempt"]["path"] = str(target.relative_to(runner.out))
        runner.workflow_dump(runner.out / "cache" / (spec.stage_id + ".json"), meta)
        return stage, meta
    except (ValueError, KeyError, TypeError, OSError, runner.workflow_error):
        return None


def export_cached(runner, spec, stage, metadata):
    if not runner.shared_cache or metadata.get("cache_hit"):
        return
    root = runner.shared_cache
    root.mkdir(parents=True, exist_ok=True)
    target = root / runner.workflow_digest(metadata["key"])
    temporary = Path(tempfile.mkdtemp(prefix=".stage-", dir=root))
    try:
        runner.workflow_dump(temporary / "cache.json", metadata)
        runner.workflow_dump(temporary / "stage.json", stage)
        shutil.copytree(runner.out / metadata["accepted_attempt"]["path"], temporary / "audit")
        # Separate task runs never mutate an existing shared entry.
        if not target.exists():
            try:
                temporary.rename(target)
            except FileExistsError:
                pass
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
