"""CSF pilot: pure, offline contract validation. No connector or network access."""
import hashlib
import json

VERSION = "0.1.0"
DOMAINS = frozenset({"governance", "infrastructure"})
KINDS = frozenset({"observation", "inference", "scenario"})
STATES = ("INVENTORY_PENDING", "SOURCE_VERIFIED", "CONTRACT_READY",
          "IMPLEMENTED", "TESTED", "INDEPENDENT_REVIEWED",
          "OWNER_APPROVED", "PERSISTED")


class ContractError(ValueError):
    pass


def stable_key(source_id, revision, claim_id):
    if not all(isinstance(v, str) and v.strip() for v in (source_id, revision, claim_id)):
        raise ContractError("missing source identity or claim ID")
    payload = json.dumps([source_id, revision, VERSION, claim_id], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate(record):
    if not isinstance(record, dict) or record.get("contract_version") != VERSION:
        raise ContractError("unsupported contract version")
    source = record.get("source")
    if not isinstance(source, dict):
        raise ContractError("missing source")
    required = ("id", "revision", "digest", "notion_ref")
    if any(not isinstance(source.get(k), str) or not source[k].strip() for k in required):
        raise ContractError("incomplete source provenance")
    if len(source["digest"]) != 64 or any(c not in "0123456789abcdef" for c in source["digest"]):
        raise ContractError("invalid sha256 digest")
    if record.get("claim_type") not in KINDS:
        raise ContractError("unknown claim type")
    domains = record.get("domains")
    if not isinstance(domains, list) or not domains or len(domains) != len(set(domains)) or not set(domains) <= DOMAINS:
        raise ContractError("invalid pilot domains")
    if not isinstance(record.get("statement"), str) or not record["statement"].strip():
        raise ContractError("empty statement")
    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        raise ContractError("evidence must be a list")
    if record["claim_type"] == "observation" and not evidence:
        raise ContractError("observation requires evidence")
    if any(not isinstance(e, dict) or not isinstance(e.get("ref"), str) or not e["ref"].strip() for e in evidence):
        raise ContractError("invalid evidence reference")
    for field in ("relations", "uncertainty", "counterevidence", "review", "target"):
        if field not in record:
            raise ContractError("missing " + field)
    if not isinstance(record["relations"], list) or not isinstance(record["uncertainty"], dict):
        raise ContractError("invalid relationship or uncertainty")
    if not isinstance(record["review"], dict) or not isinstance(record["counterevidence"], (list, str)):
        raise ContractError("invalid review or counterevidence")
    key = stable_key(source["id"], source["revision"], record.get("claim_id"))
    if record.get("idempotency_key") != key:
        raise ContractError("incorrect idempotency key")
    return True


def authorize_transition(current, next_state, *, actor, evidence_ref, reviewer=None,
                         proposer=None, target=None, write_authorized=False):
    if current not in STATES or next_state not in STATES or STATES.index(next_state) != STATES.index(current) + 1:
        raise ContractError("invalid state transition")
    if not actor or not evidence_ref:
        raise ContractError("transition requires actor and evidence")
    if next_state == "INDEPENDENT_REVIEWED" and (not reviewer or not proposer or reviewer == proposer):
        raise ContractError("independent review required")
    if next_state == "PERSISTED" and (not isinstance(target, dict) or
            not target.get("module_id") or not target.get("revision") or not write_authorized):
        raise ContractError("verified target and explicit authorization required")
    return next_state
