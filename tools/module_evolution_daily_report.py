"""Deterministic, read-only report from a Nexus module-evolution checkpoint.

Reports describe recorded observations, never readiness or verified progress.
"""
import argparse
import json
from pathlib import Path
from tools.module_evolution_runner import MODULES
from tools.module_evolution_snapshot import load_snapshot


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
    print(json.dumps(summarize(load_snapshot(Path(args.snapshot))), sort_keys=True))


if __name__ == "__main__":
    main()
