"""Offline CSF review artifact/receipt verifier CLI.

Input files are local and untrusted. No network or provider authentication.
Exit 0 proves content binding only; never Gate C approval.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus_sandbox.csf_gemini_artifact_verify import verify_review_artifact
from nexus_sandbox.csf_gemini_review_receipt import ReviewReceiptError


def check(receipt_path, artifact_path):
    receipt_path = Path(receipt_path)
    artifact_path = Path(artifact_path)
    if receipt_path.is_symlink() or artifact_path.is_symlink():
        raise ReviewReceiptError("symlinked evidence path rejected")
    if not receipt_path.is_file() or not artifact_path.is_file():
        raise ReviewReceiptError("evidence file missing")
    if receipt_path.stat().st_size > 100_000:
        raise ReviewReceiptError("receipt too large")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ReviewReceiptError("invalid receipt JSON") from error
    return verify_review_artifact(receipt, artifact_path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()
    try:
        check(args.receipt, args.artifact)
    except (ReviewReceiptError, OSError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}))
        return 2
    print(json.dumps({"status": "ARTIFACT_CONTENT_BOUND", "provider_identity_verified": False,
                      "gate_c_approved": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
