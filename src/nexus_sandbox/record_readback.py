"""Read-only verification of host-observed records, never a write authorization.

No network, credentials or synthetic-fixture bypass. Callers supply independent
reads; their provenance and the completeness of provider exports remain external.
"""
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID


@dataclass(frozen=True)
class Binding:
    record_id: str
    parent_id: str
    payload_sha256: str


@dataclass(frozen=True)
class Observation:
    record_id: str
    parent_id: str
    payload: str
    complete: bool


@dataclass(frozen=True)
class Verdict:
    status: str
    reason: str
    observed_sha256: str | None = None


def digest(payload):
    return sha256(payload.encode('utf-8')).hexdigest()


def verify(binding, read):
    """Invoke a fresh read; compare identity, direct parent and exact bytes.

    Does not prove source truth, duplicate absence, external atomicity, future
    persistence, recovery, or that the callback actually contacted a provider.
    Exceptions deliberately exclude callback details from the returned verdict.
    """
    if type(binding) is not Binding:
        raise ValueError('Explicit Binding required')
    expected_id = UUID(binding.record_id)
    expected_parent = UUID(binding.parent_id)
    expected_hash = binding.payload_sha256
    if (not isinstance(expected_hash, str) or len(expected_hash) != 64
            or any(c not in '0123456789abcdef' for c in expected_hash)):
        raise ValueError('Lowercase SHA-256 required')
    try:
        observed = read(binding.record_id)
    except Exception:
        return Verdict('UNKNOWN', 'Read unavailable; no verification')
    if type(observed) is not Observation or observed.complete is not True:
        return Verdict('UNKNOWN', 'Incomplete or malformed observation')
    try:
        identity = UUID(observed.record_id)
        parent = UUID(observed.parent_id)
        if not isinstance(observed.payload, str):
            raise ValueError()
        actual_hash = digest(observed.payload)
    except (ValueError, TypeError, AttributeError, UnicodeError):
        return Verdict('UNKNOWN', 'Malformed record fields')
    if identity != expected_id or parent != expected_parent:
        return Verdict('MISMATCH', 'Identity or direct parent differs', actual_hash)
    if actual_hash != expected_hash:
        return Verdict('MISMATCH', 'Payload differs', actual_hash)
    return Verdict('VERIFIED_OBSERVATION', 'Exact bound record observed', actual_hash)
