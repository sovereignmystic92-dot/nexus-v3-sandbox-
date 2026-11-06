"""Pure readback verification for Cortex derived-output transfers.

Caller must obtain the record independently after the connector write.
This module never performs a write or elevates an automated acceptance gate.
"""
from dataclasses import dataclass


class ReadbackFailure(ValueError):
    pass


@dataclass(frozen=True)
class ReadbackReceipt:
    status: str
    module_id: str
    version: int
    transaction_key: str


def verify_readback(*, module: dict, expected_id: str, expected_owner: str,
                    transaction_key: str, source_url: str, analysis_url: str,
                    expected_analysis: str) -> ReadbackReceipt:
    if not all(isinstance(x, str) and x.strip() for x in
               (expected_id, expected_owner, transaction_key, source_url,
                analysis_url, expected_analysis)):
        raise ReadbackFailure("incomplete readback binding")
    if not isinstance(module, dict):
        raise ReadbackFailure("missing independent readback")
    if module.get("id") != expected_id or module.get("owner") != expected_owner:
        raise ReadbackFailure("module identity or owner mismatch")
    version = module.get("version")
    if type(version) is not int or version < 1 or module.get("archived") is not False:
        raise ReadbackFailure("invalid version or inactive module")
    content = module.get("content")
    if not isinstance(content, str):
        raise ReadbackFailure("missing content")
    for marker in (transaction_key, source_url, analysis_url, expected_analysis):
        if marker not in content:
            raise ReadbackFailure("readback content mismatch")
    return ReadbackReceipt("VERIFIED_MANUAL_OR_CONNECTOR_READBACK_ONLY",
                           expected_id, version, transaction_key)
