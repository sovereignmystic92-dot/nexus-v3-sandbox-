"""Fail-closed CP05 runtime capability preflight; never read or print secret values.

This checks only whether configured environment variables are nonempty and
whether the host declares supported capabilities. Presence is not proof of
valid credentials, effective grants, provider identity, or authenticated I/O.
"""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class CapabilityVerdict:
    status: str
    missing: tuple[str, ...]
    next_action: str


_REQUIRED_ENV = ("NEXUS_NOTION_TOKEN", "NEXUS_CORTEX_TOKEN")
_REQUIRED_CAPABILITIES = (
    "notion_authenticated_full_page_read",
    "notion_complete_pagination",
    "cortex_authenticated_module_read",
    "cortex_complete_output_read",
    "independent_provider_readback",
)


def check_runtime_capabilities(*, environ=None, capabilities=None):
    """Inspect declarations without exposing values or invoking providers.

    A positive result permits attempting a separately authorized read-only
    authentication probe. It NEVER permits recording a COMPLETE checkpoint.
    """
    env = os.environ if environ is None else environ
    if not hasattr(env, "get"):
        return CapabilityVerdict("BLOCKED", ("invalid_environment",), "CONFIGURE_RUNTIME")
    if not isinstance(capabilities, dict):
        return CapabilityVerdict("BLOCKED", ("capability_manifest",), "DECLARE_HOST_CAPABILITIES")
    missing = []
    for key in _REQUIRED_ENV:
        value = env.get(key)
        if not isinstance(value, str) or not value.strip():
            missing.append(key)
    for key in _REQUIRED_CAPABILITIES:
        if capabilities.get(key) is not True:
            missing.append(key)
    if missing:
        return CapabilityVerdict("BLOCKED", tuple(missing), "CONFIGURE_AND_ATTEST_HOST")
    return CapabilityVerdict("READY_FOR_AUTHENTICATED_READ_PROBE", (), "VERIFY_EFFECTIVE_GRANTS_AND_PROVIDER_READBACK")
