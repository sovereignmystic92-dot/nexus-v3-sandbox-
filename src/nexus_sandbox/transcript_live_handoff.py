"""Bounded live transcript handoff using host-provided authenticated provider ports.

This module performs real provider calls when the host supplies ports. It does
not create credentials, schedule itself, or attest the host's identity.
Uncertain writes STOP for reconciliation; never retry blindly.
"""
from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class Observed:
    object_id: str
    content: str


@dataclass(frozen=True)
class Handoff:
    status: str
    next_action: str
    source_sha256: str
    notion_id: str = ""
    cortex_id: str = ""


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_handoff(*, transcript, notion_page_id, cortex_module_name,
                analysis, notion_read, notion_write, cortex_read, cortex_write,
                allow_notion_write=False, allow_cortex_write=False):
    """Port signatures: read(identifier)->Observed|None; write(identifier,text)->None.

    Destination identities are explicit. A missing object can only be created
    by a host write port with its own policy/grant checks. Every write is
    followed by a fresh independent read. Existing exact content is reused.
    """
    if any(type(v) is not str or not v.strip() for v in
           (transcript, notion_page_id, cortex_module_name, analysis)):
        raise ValueError("Nonempty transcript, destinations and analysis required")
    if type(allow_notion_write) is not bool or type(allow_cortex_write) is not bool:
        raise ValueError("Explicit boolean authorization required")
    sha = _sha(transcript)

    def observe(read, key):
        value = read(key)  # errors propagate; no assumption of absence
        if value is not None and (type(value) is not Observed or value.object_id != key):
            raise ValueError("Provider identity mismatch")
        return value

    n = observe(notion_read, notion_page_id)
    if n is None or n.content != transcript:
        if not allow_notion_write:
            return Handoff("BLOCKED", "NOTION_FULL_FIDELITY_READBACK_REQUIRED", sha)
        if n is not None:
            return Handoff("BLOCKED", "NOTION_CONFLICT_RECONCILE_NO_OVERWRITE", sha)
        try:
            notion_write(notion_page_id, transcript)
        except Exception:
            return Handoff("BLOCKED", "NOTION_WRITE_OUTCOME_UNCERTAIN_RECONCILE", sha)
        n = observe(notion_read, notion_page_id)
        if n is None or n.content != transcript:
            return Handoff("BLOCKED", "NOTION_POSTWRITE_READBACK_MISMATCH", sha)
    # Bind analytical output to exact canonical source and content hash.
    marker = "NEXUS_SOURCE_PAGE=" + notion_page_id + "\nNEXUS_SOURCE_SHA256=" + sha + "\n"
    desired = marker + analysis
    c = observe(cortex_read, cortex_module_name)
    if c is None or c.content != desired:
        if not allow_cortex_write:
            return Handoff("BLOCKED", "CORTEX_READBACK_REQUIRED", sha, notion_page_id)
        if c is not None:
            return Handoff("BLOCKED", "CORTEX_CONFLICT_RECONCILE_NO_OVERWRITE", sha, notion_page_id)
        try:
            cortex_write(cortex_module_name, desired)
        except Exception:
            return Handoff("BLOCKED", "CORTEX_WRITE_OUTCOME_UNCERTAIN_RECONCILE", sha, notion_page_id)
        c = observe(cortex_read, cortex_module_name)
        if c is None or c.content != desired:
            return Handoff("BLOCKED", "CORTEX_POSTWRITE_READBACK_MISMATCH", sha, notion_page_id)
    return Handoff("READBACK_MATCHED", "RECORD_DURABLE_EXECUTION_RECEIPT", sha,
                   notion_page_id, cortex_module_name)
