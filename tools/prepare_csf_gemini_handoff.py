"""Offline CLI entrypoint for the CSF Gemini handoff.

This is NOT a live Gemini invocation. Requires a pinned Git checkout, emits
only source hashes/paths, and refuses mismatched HEAD before preparing manifest.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus_sandbox.csf_gemini_handoff import HandoffError, build_handoff


def prepare(root, source_commit):
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise HandoffError("exact source SHA required")
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise HandoffError("checkout identity unavailable") from error
    if result.stdout.strip() != source_commit:
        raise HandoffError("checkout HEAD differs from requested source commit")
    return build_handoff(root, source_commit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    try:
        packet = prepare(ROOT, args.source_commit)
    except HandoffError as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}))
        return 2
    print(json.dumps(packet, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
