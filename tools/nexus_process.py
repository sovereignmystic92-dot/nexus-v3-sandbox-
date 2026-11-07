"""CLI preflight for the shared Nexus transcript gateway.

This command is intentionally READ-ONLY: it validates a job manifest and emits
a normalized job descriptor. It never calls Gemini, Notion or Cortex and cannot
mark a provider operation verified. Runtime execution needs authenticated ports.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nexus_sandbox.nexus_processing_gateway import MODES

VIDEO = re.compile(r"^https://(?:www\.youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})$")


def preflight(payload):
    if type(payload) is not dict or set(payload) != {
            "mode", "source_url", "transcript", "notion_page_id",
            "cortex_module_name", "analysis", "grants"}:
        raise ValueError("Exact job manifest fields required")
    mode = payload["mode"]
    if type(mode) is not str or mode not in MODES:
        raise ValueError("Invalid trigger mode")
    url = payload["source_url"]
    if type(url) is not str or not VIDEO.fullmatch(url):
        raise ValueError("Canonical YouTube video URL required")
    for field in ("transcript", "notion_page_id", "cortex_module_name", "analysis"):
        value = payload[field]
        if type(value) is not str or not value.strip():
            raise ValueError("Missing " + field)
    grants = payload["grants"]
    if type(grants) is not dict or set(grants) != {
            "process", "notion_write", "cortex_write"} or any(
            type(v) is not bool for v in grants.values()):
        raise ValueError("Invalid grants")
    if not grants["process"]:
        raise ValueError("Processing not authorized")
    return {
        "status": "PREFLIGHT_ONLY", "mode": mode,
        "source_url": url, "source_sha256": hashlib.sha256(
            payload["transcript"].encode("utf-8")).hexdigest(),
        "notion_page_id": payload["notion_page_id"],
        "cortex_module_name": payload["cortex_module_name"],
        "provider_writes": 0, "readback_verified": False,
        "automatic_execution": False,
        "next_action": "INVOKE_AUTHENTICATED_PROVIDER_RUNTIME",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        path = Path(args.manifest)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1048576:
            raise ValueError("Invalid or oversized manifest")
        result = preflight(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, OSError, UnicodeError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
