"""Prepare a bounded, read-only CSF artifact from an authorized source export.

This CLI has no Notion/Gemini/Cortex credentials, calls or writes. A trusted
host must independently fetch the canonical source and supply an exact envelope.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus_sandbox.csf_notional_intake import prepare_source_receipt
from nexus_sandbox.csf_v02 import CSFValidationError

MAX_ENVELOPE_BYTES = 2_500_000


def prepare(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise CSFValidationError("source envelope must be regular file")
    if p.stat().st_size > MAX_ENVELOPE_BYTES:
        raise CSFValidationError("source envelope oversized")
    try:
        envelope = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise CSFValidationError("source envelope unreadable") from exc
    return prepare_source_receipt(envelope)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-envelope", required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.source_envelope)
    except CSFValidationError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
