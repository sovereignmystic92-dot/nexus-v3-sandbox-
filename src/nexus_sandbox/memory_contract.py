"""Provider-neutral Skill Forge revision and checkpoint validation."""

from datetime import datetime
from hashlib import sha256
import re

from nexus_sandbox.checkpoint_ledger import canonical, manifest_hash, require

SCHEMA = "skill-forge.memory.v0.1"
SOURCE_FIELDS = {"authority", "store_scope", "record_id", "revision_id", "content_sha256"}
REVISION_FIELDS = {
    "schema_version", "store_scope", "module_id", "name", "version", "content",
    "content_sha256", "dependencies", "source", "observed_at_utc", "verification",
}
CHECKPOINT_BODY = {
    "mission_id", "sequence", "observed_at_utc", "previous_checkpoint_sha256", "verified_receipt",
}
UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z")


def _fields(value, names):
    require(type(value) is dict and value.keys() == names, "Unexpected record fields")


def _identities(*values):
    require(all(isinstance(value, str) and value.strip() for value in values), "Missing identity")


def _digest(value):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value), "Invalid SHA-256")


def _utc(value):
    require(isinstance(value, str) and UTC_TIMESTAMP.fullmatch(value), "Invalid UTC timestamp")
    datetime.fromisoformat(value[:-1] + "+00:00")


def source_reference(authority, store_scope, record_id, revision_id, content):
    """Build a source reference from an exact snapshot read by the caller."""
    _identities(authority, store_scope, record_id, revision_id)
    require(isinstance(content, str), "Source content must be text")
    return {
        "authority": authority, "store_scope": store_scope, "record_id": record_id,
        "revision_id": revision_id, "content_sha256": sha256(content.encode("utf-8")).hexdigest(),
    }


def encode_revision(record, *, fresh_source=None):
    """Validate and serialize an envelope. Verified records require fresh trusted readback."""
    _fields(record, REVISION_FIELDS)
    require(record["schema_version"] == SCHEMA, "Unsupported revision schema")
    _identities(record["store_scope"], record["module_id"], record["name"])
    require(type(record["version"]) is int and record["version"] >= 1, "Invalid revision version")
    require(isinstance(record["content"], str), "Revision content must be text")
    require(sha256(record["content"].encode("utf-8")).hexdigest() == record["content_sha256"],
            "Revision content digest mismatch")
    dependencies = record["dependencies"]
    require(type(dependencies) is list, "Expected ordered dependency list")
    _identities(*dependencies)
    require(record["name"] not in dependencies and len(set(dependencies)) == len(dependencies),
            "Invalid dependency edges")
    _utc(record["observed_at_utc"])

    source = record["source"]
    if source is not None:
        _fields(source, SOURCE_FIELDS)
        _identities(source["authority"], source["store_scope"], source["record_id"], source["revision_id"])
        _digest(source["content_sha256"])
    verdict = record["verification"]
    _fields(verdict, {"status", "evidence_class", "observed_at_utc", "receipt_ref"})
    _utc(verdict["observed_at_utc"])
    require(verdict["status"] in ("unverified", "verified", "held"), "Invalid verification status")
    require(verdict["evidence_class"] in ("offline_synthetic", "authenticated_read_only", "live_write"),
            "Invalid evidence class")
    if verdict["receipt_ref"] is not None or verdict["status"] == "verified":
        _identities(verdict["receipt_ref"])
    if verdict["status"] == "verified":
        require(source is not None and source == fresh_source, "Verified revision requires exact fresh source")
    return canonical(record)


def validate_resume(trusted_prefix, candidate, *, mission_id, resolve_verified_receipt,
                    authorize_genesis=False):
    """Return the checkpoint head digest after validating an independently trusted prefix.

    The resolver accepts mission ID, store scope and receipt ID. It returns exact
    retained bytes only for a verified receipt in that mission or raises on failure.
    The caller supplies the trusted prefix independently of the candidate.
    """
    _identities(mission_id)
    require(type(trusted_prefix) is list, "Trusted checkpoint history unavailable")
    require(bool(trusted_prefix) or authorize_genesis is True, "Genesis requires authorization")
    require(type(candidate) is list and len(candidate) >= len(trusted_prefix), "Accepted history truncated")
    require(canonical(candidate[:len(trusted_prefix)]) == canonical(trusted_prefix),
            "Accepted checkpoint history rewritten")
    previous = None
    for sequence, checkpoint in enumerate(candidate, 1):
        _fields(checkpoint, CHECKPOINT_BODY | {"checkpoint_sha256"})
        require(checkpoint["mission_id"] == mission_id, "Checkpoint mission mismatch")
        require(type(checkpoint["sequence"]) is int and checkpoint["sequence"] == sequence,
                "Checkpoint sequence gap")
        require(checkpoint["previous_checkpoint_sha256"] == previous, "Broken checkpoint hash chain")
        _utc(checkpoint["observed_at_utc"])
        digest = manifest_hash({field: checkpoint[field] for field in CHECKPOINT_BODY})
        require(checkpoint["checkpoint_sha256"] == digest, "Checkpoint digest mismatch")
        ref = checkpoint["verified_receipt"]
        _fields(ref, {"store_scope", "receipt_id", "receipt_sha256"})
        _identities(ref["store_scope"], ref["receipt_id"])
        _digest(ref["receipt_sha256"])
        receipt = resolve_verified_receipt(mission_id, ref["store_scope"], ref["receipt_id"])
        require(type(receipt) is bytes and sha256(receipt).hexdigest() == ref["receipt_sha256"],
                "Verified receipt bytes unavailable or changed")
        previous = digest
    return previous
