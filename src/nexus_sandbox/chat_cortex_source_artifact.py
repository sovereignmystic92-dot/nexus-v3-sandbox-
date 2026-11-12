"""Prepare a redacted SOURCE_READY receipt from a freshly fetched Notion export.

The operator/worker supplies a complete Notion Markdown export and a trusted
metadata JSON. This program does not fetch Notion or invoke Chat/Cortex.
"""
import argparse
import json
from pathlib import Path

from .chat_cortex_notion_readback import verify_notion_export
from .chat_cortex_source_ready import prepare_source_ready


def build_receipt(markdown, metadata, *, destination_module, authorization_reference,
                  github_run_id, github_run_attempt, github_sha):
    if not isinstance(metadata, dict):
        raise ValueError("source metadata must be an object")
    for key in ("source_id", "source_revision", "truncated", "unknown_block_count"):
        if key not in metadata:
            raise ValueError("missing source metadata: " + key)
    verified = verify_notion_export(
        markdown, source_id=metadata["source_id"],
        source_revision=metadata["source_revision"],
        truncated=metadata["truncated"],
        unknown_block_count=metadata["unknown_block_count"],
    )
    evidence = {key: verified[key] for key in (
        "notion_source_id", "readback_sha256", "pending_cortex_processing",
        "readback_verified", "source_revision",
    )}
    evidence["destination_module"] = destination_module
    evidence["authorization_reference"] = authorization_reference
    ready = prepare_source_ready(evidence)
    if not all(isinstance(v, str) and v.strip() for v in
               (github_run_id, github_run_attempt, github_sha)):
        raise ValueError("missing GitHub execution attribution")
    return {
        "schema": "nexus.chat-cortex.source-ready-receipt.v1",
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "github_sha": github_sha,
        "source_id": verified["notion_source_id"],
        "source_revision": verified["source_revision"],
        "source_sha256": verified["readback_sha256"],
        "source_bytes": verified["byte_count"],
        "source_chunks": verified["chunk_count"],
        "source_ready_emitted": True,
        "state": ready["state"],
        "packet": ready["packet"],
        "triage": ready["triage"],
        "chat_invoked": False,
        "cortex_called": False,
        "cortex_write_verified": False,
        "audit_gate_promoted": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--destination-module", required=True)
    parser.add_argument("--authorization-reference", required=True)
    parser.add_argument("--github-run-id", required=True)
    parser.add_argument("--github-run-attempt", required=True)
    parser.add_argument("--github-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    markdown = Path(args.markdown).read_text(encoding="utf-8")
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    receipt = build_receipt(markdown, metadata,
                            destination_module=args.destination_module,
                            authorization_reference=args.authorization_reference,
                            github_run_id=args.github_run_id,
                            github_run_attempt=args.github_run_attempt,
                            github_sha=args.github_sha)
    Path(args.output).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
