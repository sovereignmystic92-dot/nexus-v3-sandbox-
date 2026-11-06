"""Fail-closed host identity evidence gate for CP05.

This module does not authenticate a host. The attestation must be supplied by
an independently trusted host integration, not inferred from Cortex content.
"""
from collections.abc import Mapping


class HostEvidenceError(ValueError):
    pass


def validate_host_evidence(evidence):
    """Validate a host-provided evidence *shape*, not credential authenticity.

    A passing shape is NOT an authenticated Cortex read or CP05 gate pass.
    The trusted host must independently verify all claims and receipt readback.
    """
    if not isinstance(evidence, Mapping):
        raise HostEvidenceError("Missing host evidence")
    if evidence.get("origin") != "trusted-host":
        raise HostEvidenceError("Host provenance not established")
    principal = evidence.get("principal_ref")
    if type(principal) is not str or not principal.strip():
        raise HostEvidenceError("Host principal missing")
    if evidence.get("provider_auth_verified") is not True:
        raise HostEvidenceError("Provider authentication unverified")
    if evidence.get("effective_read_grant_verified") is not True:
        raise HostEvidenceError("Effective Cortex read grant unverified")
    if evidence.get("independent_receipt_readback") is not True:
        raise HostEvidenceError("Independent receipt readback missing")
    if type(evidence.get("reads")) is not int or evidence["reads"] < 1:
        raise HostEvidenceError("Read count missing")
    if type(evidence.get("writes")) is not int or evidence["writes"] != 0:
        raise HostEvidenceError("Writes not zero")
    if type(evidence.get("run_ref")) is not str or not evidence["run_ref"].strip():
        raise HostEvidenceError("Run reference missing")
    return {
        "principal_ref": principal,
        "run_ref": evidence["run_ref"],
        "reads": evidence["reads"],
        "writes": 0,
        "shape_valid_only": True,
    }
