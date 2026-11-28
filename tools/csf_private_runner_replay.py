"""Manual recovery of the frozen Haiti batch; metadata-only output."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

IMPLEMENTATION = "616eb0690673d9f0ebe4253a61f33e23aa574932"
DATABASE_SHA256 = "c0e039bc1e1021177eace8b3fdc3eac07accc27c48d8bc23a520f341a08eba27"
SOURCE_SHA256 = "2f8ba596e3d4672f412487981390de6f3357a5a7156aefbc73a98cc42abcd646"
REVISION = "2026-11-07T16:58:29.408Z"
PAGE_ID = "4088c067-daa4-813b-b1f0-e1f1993120fb"
SOURCE_URL = "https://app.notion.com/p/4088c067daa4813bb1f0e1f1993120fb?pvs=204"
BATCH_ID = "haiti-csf-three-domain-01"
EXPECTED_REFS = [
    {"finding_id": "f7afcb50-34d3-5bcf-be06-fda0d8edfb9f", "payload_sha256": "db6476f98d9d68e494bd04d26afaec4078bd928abf4ca1834fb02cafa0617898"},
    {"finding_id": "e1271b26-3b5f-54fa-9451-e1d204372b49", "payload_sha256": "5432b86031109d508bcf6fffbe06978c9ce155109db4cc85f240bc8da58dc136"},
    {"finding_id": "bfd45b7c-7e02-56e7-a7d5-5fc47ae03603", "payload_sha256": "c20ca18613b5ebd3fee7e76ebf7c4102de2f963d2eaf4e9adeb9b23e0d8d58bf"},
]


def decode_database(encoded):
    if not isinstance(encoded, str) or not encoded or len(encoded) > 24000:
        raise ValueError("missing or oversized batch")
    raw = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(raw).hexdigest() != DATABASE_SHA256:
        raise ValueError("batch digest mismatch")
    return raw


def validate_source(source):
    expected = {"source_url": SOURCE_URL, "source_revision": REVISION,
                "document_id": "notion:" + PAGE_ID, "expected_sha256": SOURCE_SHA256}
    if not isinstance(source, dict) or set(source) != set(expected) | {"transcript"}:
        raise ValueError("source envelope mismatch")
    if any(source[key] != value for key, value in expected.items()):
        raise ValueError("source identity mismatch")
    raw = source["transcript"]
    if not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError("source digest mismatch")


def fetch_source(root, token):
    spec = importlib.util.spec_from_file_location(
        "pinned_notion_probe", root / "tools/notion_csf_authenticated_source_probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    before = probe.read_json("pages/" + PAGE_ID, token)
    def require_page(page):
        if (page.get("id", "").replace("-", "") != PAGE_ID.replace("-", "")
                or page.get("last_edited_time") != REVISION
                or page.get("archived") or page.get("in_trash")):
            raise ValueError("source revision unavailable")
    require_page(before)
    raw = probe.extract_raw(probe.children(PAGE_ID, token))
    require_page(probe.read_json("pages/" + PAGE_ID, token))
    source = {"source_url": SOURCE_URL, "source_revision": REVISION,
              "document_id": "notion:" + PAGE_ID, "expected_sha256": SOURCE_SHA256,
              "transcript": raw}
    validate_source(source)
    return source


def validate_result(result):
    if not isinstance(result, dict) or result.get("status") != "BATCH_REPLAYED":
        raise ValueError("replay failed")
    if (result.get("finding_count") != 3 or result.get("provider_called") is not False
            or result.get("audit_gate_promoted") is not False):
        raise ValueError("unexpected replay result")
    refs = result.get("finding_refs")
    if not isinstance(refs, list) or len(refs) != 3 or any(not isinstance(x, dict) for x in refs):
        raise ValueError("invalid finding references")
    canonical = lambda x: json.dumps(x, sort_keys=True)
    if sorted(map(canonical, refs)) != sorted(map(canonical, EXPECTED_REFS)):
        raise ValueError("finding reference mismatch")
    # Emit only fixed, verified metadata; never forward arbitrary child output.
    return {"status": "HAITI_PRIVATE_BATCH_REPLAY_VERIFIED", "finding_count": 3,
            "finding_refs": EXPECTED_REFS, "implementation_commit": IMPLEMENTATION,
            "database_sha256": DATABASE_SHA256, "source_sha256": SOURCE_SHA256,
            "source_revision": REVISION, "external_writes": 0,
            "new_gemini_call": False, "audit_gate_promoted": False,
            "independent_analytical_review_performed": False}


def recover(encoded, source_loader, root):
    raw = decode_database(encoded)  # Reject bad batch before any authenticated read.
    source = source_loader()
    validate_source(source)
    with tempfile.TemporaryDirectory(prefix="csf-private-replay-") as directory:
        private = Path(directory)
        database = private / "batch.sqlite"
        envelope = private / "source.json"
        database.write_bytes(raw)
        envelope.write_text(json.dumps(source))
        for path in (database, envelope):
            path.chmod(0o600)
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("database integrity failure")
            rows = db.execute("SELECT batch_id FROM csf_review_batches").fetchall()
            if rows != [(BATCH_ID,)]:
                raise ValueError("unexpected batch inventory")
        clean_env = {key: value for key, value in os.environ.items()
                     if key not in ("NOTION_SANDBOX_TOKEN", "CSF_HAITI_BATCH_B64")}
        child = subprocess.run([
            sys.executable, "-I", str(root / "tools/csf_review_handoff.py"),
            "--source-envelope", str(envelope), "--database", str(database),
            "--batch-id", BATCH_ID,
        ], capture_output=True, text=True, timeout=60, env=clean_env)
        if child.returncode != 0 or len(child.stdout) > 8192:
            raise ValueError("replay child failed")
        return validate_result(json.loads(child.stdout))


def main():
    try:
        if (os.environ.get("GITHUB_REPOSITORY") != "sovereignmystic92-dot/nexus-v3-sandbox-"
                or os.environ.get("GITHUB_REF") != "refs/heads/main"
                or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"):
            raise ValueError("manual main-only execution required")
        root = Path(sys.argv[1]).resolve()
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                         text=True, timeout=10).strip()
        if commit != IMPLEMENTATION:
            raise ValueError("implementation checkout mismatch")
        token = os.environ.get("NOTION_SANDBOX_TOKEN")
        if not token:
            raise ValueError("Notion connection unavailable")
        result = recover(os.environ.get("CSF_HAITI_BATCH_B64"),
                         lambda: fetch_source(root, token), root)
        for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"):
            value = os.environ.get(name, "")
            if not value or not value.isalnum():
                raise ValueError("run provenance unavailable")
            result[name.lower()] = value
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        # Never expose provider bodies, raw source, exception strings, or batch data.
        print('{"status":"BLOCKED","reason":"private_replay_preflight_or_verification_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
