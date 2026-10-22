"""Resolve explicit synthetic authority metadata; never interpret source prose."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class AuthorityDecision:
    allowed: bool
    reason: str
    governing_revision: str
    provenance: tuple


def default_records():
    return json.loads(Path(__file__).with_name("authority.json").read_text())


def resolve(records):
    """Labels are operator-supplied assertions, not authenticated authority.

    Only current records govern. Different current rules, ambiguous identities,
    missing current authority and explicit denial all fail closed. Historical,
    source and hypothesis records remain in the returned provenance.
    """
    documents = json.loads(json.dumps(records))
    identities = set()
    for document in documents:
        if (set(document) != {"document_id", "revision", "role", "rule"}
                or not isinstance(document["document_id"], str)
                or not document["document_id"].startswith("synthetic:authority:")
                or not isinstance(document["revision"], str) or not document["revision"]
                or document["role"] not in ("current", "historical", "source", "hypothesis")
                or document["rule"] not in ("allow_synthetic_output", "deny_synthetic_output")):
            raise ValueError("Malformed synthetic authority metadata")
        identity = (document["document_id"], document["revision"])
        if identity in identities:
            raise ValueError("Duplicate or ambiguous authority identity")
        identities.add(identity)
    documents.sort(key=lambda d: (d["document_id"], d["revision"]))
    governing = [d for d in documents if d["role"] == "current"]
    revision = hashlib.sha256(json.dumps(governing, sort_keys=True).encode()).hexdigest()
    rules = {d["rule"] for d in governing}
    reason = ("missing current authority" if not rules else
              "conflicting current authority" if len(rules) > 1 else
              "current authority denies output" if "deny_synthetic_output" in rules else
              "current authority permits synthetic output")
    return AuthorityDecision(rules == {"allow_synthetic_output"}, reason, revision,
                             tuple(documents))
