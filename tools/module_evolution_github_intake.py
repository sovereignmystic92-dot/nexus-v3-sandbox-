"""Normalize GitHub webhook payloads into untrusted Nexus observation envelopes.

Pure data transformation: no GitHub API, credentials, provider writes, or
readiness decisions. The caller must supply an authenticated event delivery.
"""
import argparse
import json
from pathlib import Path

REPOSITORY = "sovereignmystic92-dot/nexus-v3-sandbox-"
SUPPORTED = frozenset(("push", "pull_request", "issues", "workflow_run"))


def normalize(event_name, delivery_id, payload):
    if event_name not in SUPPORTED:
        raise ValueError("unsupported event")
    if not isinstance(delivery_id, str) or not delivery_id.strip():
        raise ValueError("missing delivery identity")
    if not isinstance(payload, dict) or not isinstance(payload.get("repository"), dict):
        raise ValueError("invalid payload")
    if payload["repository"].get("full_name") != REPOSITORY:
        raise ValueError("unexpected repository")
    if event_name == "push":
        subject = payload.get("after")
        source_url = payload.get("compare")
    elif event_name == "pull_request":
        obj = payload.get("pull_request") or {}
        subject = str(obj.get("number", ""))
        source_url = obj.get("html_url")
    elif event_name == "issues":
        obj = payload.get("issue") or {}
        subject = str(obj.get("number", ""))
        source_url = obj.get("html_url")
    else:
        obj = payload.get("workflow_run") or {}
        subject = str(obj.get("id", ""))
        source_url = obj.get("html_url")
    if not isinstance(subject, str) or not subject.strip() or not isinstance(source_url, str) or not source_url.startswith("https://github.com/"):
        raise ValueError("missing trusted-shape provenance")
    return {
        "repository": REPOSITORY,
        "event": event_name,
        "event_id": delivery_id,
        "subject": subject,
        "source_url": source_url,
        "module_hints": [],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--delivery-id", required=True)
    parser.add_argument("--payload-file", required=True)
    args = parser.parse_args()
    print(json.dumps(normalize(args.event_name, args.delivery_id, json.loads(Path(args.payload_file).read_text())), sort_keys=True))


if __name__ == "__main__":
    main()
