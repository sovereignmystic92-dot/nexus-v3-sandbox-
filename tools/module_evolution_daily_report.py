"""Deterministic, read-only report from a Nexus module-evolution checkpoint.

Reports describe recorded observations, never readiness or verified progress.
"""
import argparse
import json
from pathlib import Path
import tempfile
import importlib.util

ROOT = Path(__file__).resolve().parents[1]

def load(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

MODULES = load("daily_runner", "tools/module_evolution_runner.py").MODULES
import_snapshot = load("daily_snapshot", "tools/module_evolution_snapshot.py").import_snapshot


def summarize(snapshot):
    payload = snapshot["payload"]
    counts = {module: 0 for module in MODULES}
    receipts = payload["receipts"]
    for receipt in receipts:
        if receipt["status"] != "PENDING_VALIDATION":
            raise ValueError("unexpected receipt status")
        for module in json.loads(receipt["modules_json"]):
            if module not in counts:
                raise ValueError("unknown module")
            counts[module] += 1
    return {
        "schema": "nexus_module_daily_observations_v1",
        "checkpoint_sha256": snapshot["sha256"],
        "receipt_count": len(receipts),
        "module_pending_observations": counts,
        "verified_advancements": 0,
        "readiness_advanced": False,
        "evidence_class": "offline",
        "scope": "checkpoint observations only; no live event collection or provider persistence",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temp:
        import_snapshot(Path(temp) / "readback.sqlite", snapshot)
    print(json.dumps(summarize(snapshot), sort_keys=True))


if __name__ == "__main__":
    main()
