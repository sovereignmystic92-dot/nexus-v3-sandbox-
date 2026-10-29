"""Non-authoritative Notion checkpoint projection.

The execution journal is the sole source for write intent and ownership.
This module deliberately has no Notion API client, credentials, or retry loop.
"""
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class Checkpoint:
    event_key: str
    journal_identity: str
    state: str
    run_url: str
    commit_sha: str
    next_action: str

    def payload(self):
        if self.state not in ("PENDING", "HOLD", "VERIFIED"):
            raise ValueError("Unrecognized checkpoint state")
        if not all(type(v) is str and v for v in (
                self.event_key, self.journal_identity, self.run_url,
                self.commit_sha, self.next_action)):
            raise ValueError("Incomplete checkpoint")
        return {
            "schema": "nexus.notion.checkpoint.v1",
            "authority": "NON_CANONICAL",
            "event_key": self.event_key,
            "journal_identity": self.journal_identity,
            "state": self.state,
            "run_url": self.run_url,
            "commit_sha": self.commit_sha,
            "next_action": self.next_action,
        }


class NotionCheckpointProjection:
    """Host must provide an exact-key lookup and create; disabled by default.

    A lost create acknowledgement is resolved by a fresh exact-key lookup.
    If absence is uncertain, host lookup MUST raise, never return None.
    This projection is never used to decide whether an external effect may retry.
    """

    def __init__(self, *, find_exact, create, enabled=False):
        if not callable(find_exact) or not callable(create) or type(enabled) is not bool:
            raise TypeError("Explicit Notion host callbacks required")
        self.find_exact, self.create, self.enabled = find_exact, create, enabled

    def publish(self, checkpoint):
        if not self.enabled:
            return "DISABLED"
        payload = checkpoint.payload()
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        existing = self.find_exact(payload["event_key"])
        if existing is not None:
            if (type(existing) is not dict or existing.get("digest") != digest
                    or existing.get("body") != serialized):
                return "HOLD"
            return "VERIFIED"
        try:
            self.create(payload["event_key"], digest, serialized)
        except Exception:
            # A write may have succeeded despite a lost acknowledgement.
            return "HOLD"
        observed = self.find_exact(payload["event_key"])
        if (type(observed) is not dict or observed.get("digest") != digest
                or observed.get("body") != serialized):
            return "HOLD"
        return "VERIFIED"
