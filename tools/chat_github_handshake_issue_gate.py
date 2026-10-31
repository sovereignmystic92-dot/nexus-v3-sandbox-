"""Evaluate a public synthetic ChatGPT/GitHub handshake issue, no effects."""
import json
import os
from pathlib import Path
from nexus_sandbox.chat_github_handshake import precheck, postcheck

PREFIX = "NEXUS_CHAT_GITHUB_SYNTHETIC_HANDSHAKE_V1\n"
TITLE = "[Nexus synthetic adapter handshake]"
REPO = "sovereignmystic92-dot/nexus-v3-sandbox-"
OWNER = "sovereignmystic92-dot"


def inspect_event(event):
    held = dict(status="HELD", next_action="REJECT_ISSUE_EVENT",
                provider_writes=0, automatic_execution=False, cp09="NOT_PROVEN")
    if type(event) is not dict or event.get("action") != "opened":
        return held
    repo, sender, issue = [event.get(k) for k in ("repository", "sender", "issue")]
    if any(type(v) is not dict for v in (repo, sender, issue)):
        return held
    if (repo.get("full_name") != REPO or sender.get("login") != OWNER
            or type(issue.get("user")) is not dict
            or issue["user"].get("login") != OWNER
            or issue.get("title") != TITLE):
        return held
    body = issue.get("body")
    if type(body) is not str or len(body) > 4096 or not body.startswith(PREFIX):
        return held
    try:
        def no_dupes(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError("duplicate JSON key")
                obj[key] = value
            return obj
        payload = json.loads(body[len(PREFIX):], object_pairs_hook=no_dupes)
    except (ValueError, TypeError):
        return held
    if type(payload) is not dict or set(payload) != {"phase", "intent", "receipt"}:
        return held
    if payload["phase"] == "PRECHECK" and payload["receipt"] is None:
        v = precheck(payload["intent"])
    elif payload["phase"] == "POSTCHECK":
        v = postcheck(payload["intent"], payload["receipt"])
    else:
        return held
    return dict(status=v.status, next_action=v.next_action,
                intent_sha256=v.intent_sha256, issue_number=issue.get("number"),
                provider_writes=0, automatic_execution=False, cp09="NOT_PROVEN")


def main():
    path = Path(os.environ["GITHUB_EVENT_PATH"])
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("oversized event")
    result = inspect_event(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("PRECHECK_VALIDATED",
                   "SYNTHETIC_RECEIPT_MATCHED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
