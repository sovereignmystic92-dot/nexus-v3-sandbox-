"""Offline bridge from a supplied GitHub event to a verified Nexus checkpoint.

Caller is responsible for authenticating event delivery. No network access,
GitHub API calls, credentials, module promotion, or provider writes.
"""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


intake = load("nexus_github_intake", "tools/module_evolution_github_intake.py")
runner = load("nexus_event_runner", "tools/module_evolution_runner.py")
snapshot = load("nexus_event_snapshot", "tools/module_evolution_snapshot.py")


def process(database, event_name, delivery_id, payload, checkpoint):
    envelope = intake.normalize(event_name, delivery_id, payload)
    receipt = runner.evaluate(database, envelope)
    digest = snapshot.save_snapshot(database, checkpoint)
    return {
        "receipt": receipt,
        "checkpoint_sha256": digest,
        "checkpoint_path": str(checkpoint),
        "readiness_advanced": False,
        "authenticated_delivery": "CALLER_RESPONSIBILITY",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--delivery-id", required=True)
    parser.add_argument("--payload-file", required=True)
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    print(json.dumps(process(args.database, args.event_name, args.delivery_id, payload, args.checkpoint), sort_keys=True))


if __name__ == "__main__":
    main()
