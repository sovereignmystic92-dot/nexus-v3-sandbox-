"""Classify actual read-only Cortex connector observations without trusting them as grants.

This is a capability/evidence assessment only. No provider calls or writes,
identity assumptions, role impersonation or gate promotion happen here.
"""


def inspect_read_capabilities(*, modules, access, detail, authenticated_principal=None):
    """Return bounded CP02/CP05 evidence blockers from untrusted connector outputs.

    modules is a fully paginated module-list response; access is context_access;
    detail is context_get; principal must be separately server-attested, not a
    caller-selected value. Strings supplied in authenticated_principal are
    intentionally NEVER treated as an attestation.
    """
    gaps = []
    if (type(modules) is not dict or type(modules.get("data")) is not list
            or modules.get("has_more") is not False):
        gaps.append("COMPLETE_MODULE_INVENTORY_NOT_VERIFIED")
    else:
        candidates = [x for x in modules["data"]
                      if type(x) is dict and
                      x.get("name") == "V2 Nexus CP02 Permission Test"]
        if (len(candidates) != 1 or
                type(candidates[0].get("id")) is not str or
                not candidates[0]["id"] or
                type(candidates[0].get("version")) is not int or
                candidates[0]["version"] < 1):
            gaps.append("SYNTHETIC_MODULE_ID_AND_REVISION_NOT_VERIFIED")
    if (type(access) is not dict or
            type(access.get("permissions")) is not list or
            any(type(p) is not str for p in access["permissions"]) or
            type(access.get("is_owner")) is not bool):
        gaps.append("EFFECTIVE_MODULE_ACCESS_REPORT_MISSING")
    # The connector's owner access is evidence of this session only, never
    # evidence of the restricted second identity.
    if type(access) is dict and access.get("is_owner") is True:
        gaps.append("RESTRICTED_VIEWER_SESSION_NOT_OBSERVED")
    if (type(detail) is not dict or
            type(detail.get("version")) is not int or
            type(detail.get("name")) is not str or
            type(detail.get("complete")) is not bool or
            type(detail.get("truncated")) is not bool or
            detail["complete"] is not True or detail["truncated"] is not False):
        gaps.append("EXACT_COMPLETE_PROVIDER_READBACK_NOT_VERIFIED")
    # No supported provider identity attestation is exposed by these inputs.
    gaps.append("PROVIDER_ATTESTED_EXECUTING_IDENTITY_MISSING")
    return {
        "status": "HELD",
        "next_action": "BIND_PROVIDER_SESSION_IDENTITY_AND_COMPLETE_READBACK",
        "missing": tuple(sorted(set(gaps))),
        "provider_writes": 0,
        "execution_authorized": False,
        "cp02": "OPEN",
        "cp05": "OPEN",
    }
