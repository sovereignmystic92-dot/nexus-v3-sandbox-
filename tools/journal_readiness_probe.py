"""Read-only host journal readiness probe. No journal creation, repair, or network.

Usage: python3 tools/journal_readiness_probe.py --journal /private/path/journal.sqlite --identity ID
Do not call this proof of cross-run persistence or remote worker fencing.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus_sandbox.journal_custody import inspect_journal


def evaluate(path, identity):
    observed = inspect_journal(path, identity)
    return {
        "schema": "nexus.journal.host-readiness.v1",
        "verdict": "LOCAL_JOURNAL_OBSERVED_NOT_ACTIVATED",
        "journal": observed,
        "passive_schedule": "DISABLED",
        "active_triggers": "DISABLED",
        "notion_writes": "DISABLED",
        "cortex_writes": "DISABLED",
        "not_proven": [
            "storage survives replacement of GitHub-hosted runner",
            "remote lease fencing or cross-host single-writer custody",
            "backup and recovery from complete journal loss",
            "live Notion or Cortex write/readback",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--identity", required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(args.journal, args.identity)
        code = 0
    except Exception:
        result = {
            "schema": "nexus.journal.host-readiness.v1",
            "verdict": "HOLD",
            "reason": "JOURNAL_CUSTODY_NOT_VERIFIED",
            "passive_schedule": "DISABLED",
            "active_triggers": "DISABLED",
        }
        code = 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
