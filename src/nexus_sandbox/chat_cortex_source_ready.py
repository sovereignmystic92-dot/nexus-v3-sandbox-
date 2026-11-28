"""Offline, source-bound handoff preparation. Never invokes Chat or Cortex."""
import json
from .chat_cortex_handoff import make_packet
from .chat_cortex_triage import triage_packet

SOURCE_ID = "4168c067-daa4-8111-bda6-ef07325583ed"
SOURCE_DIGEST = "a74abe591255afcd03af59eb34d525e997486a0118542679b77edd766380c867"
SOURCE_ISSUE = "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/202"

def prepare_source_ready(evidence):
    """Prepare a review-only packet from independently attested source evidence.

    Caller must independently establish exact Notion readback and pending state.
    The provided evidence is not itself a provider authentication or approval.
    """
    if not isinstance(evidence, dict) or set(evidence) != {
        "notion_source_id", "readback_sha256", "pending_cortex_processing",
        "readback_verified", "source_revision", "destination_module",
        "authorization_reference",
    }:
        raise ValueError("source evidence fields missing or unsupported")
    if (evidence["notion_source_id"] != SOURCE_ID
            or evidence["readback_sha256"] != SOURCE_DIGEST
            or evidence["pending_cortex_processing"] is not True
            or evidence["readback_verified"] is not True):
        raise ValueError("source not independently verified or not pending")
    if not isinstance(evidence["source_revision"], str) or not evidence["source_revision"].strip():
        raise ValueError("missing source revision")
    if not isinstance(evidence["destination_module"], str) or not evidence["destination_module"].strip():
        raise ValueError("destination unresolved")
    if not isinstance(evidence["authorization_reference"], str) or not evidence["authorization_reference"].strip():
        raise ValueError("missing authorization reference")
    fields = {
        "source_issue_url": SOURCE_ISSUE,
        "source_sha256": SOURCE_DIGEST,
        "source_revision": evidence["source_revision"],
        "destination_module": evidence["destination_module"],
        "intent": "Review verified Notion source for Cortex reconciliation",
        "evidence_class": "derived-knowledge",
        "actor": "chatgpt-connected-cortex",
        "scope": "read-only",
        "approval_reference": evidence["authorization_reference"],
    }
    packet = make_packet(fields)
    decision = triage_packet(packet)
    if decision["decision"] != "REVIEW_REQUIRED":
        raise ValueError("packet triage rejected")
    return {
        "event": "SOURCE_READY",
        "state": "CHAT_REVIEW_REQUIRED",
        "notion_source_id": SOURCE_ID,
        "packet": packet,
        "triage": decision,
        "cortex_called": False,
        "cortex_write_authorized": False,
    }

def main():
    """Accept a local JSON evidence file; stdout contains metadata only."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_json")
    args = parser.parse_args()
    with open(args.evidence_json, encoding="utf-8") as handle:
        evidence = json.load(handle)
    print(json.dumps(prepare_source_ready(evidence), sort_keys=True))

if __name__ == "__main__":
    main()
