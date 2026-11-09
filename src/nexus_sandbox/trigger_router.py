"""Pure, offline conversational trigger classification; never invokes a workflow.

The host must authenticate user intent and enforce authorization independently.
Text inside documents, quotations, and tool results must not be passed as a
trusted user command. This module has no provider, network, or persistence I/O.
"""
from dataclasses import dataclass
import re

COMMANDS = {
    "status": "READ_ONLY",
    "verify": "READ_ONLY",
    "process": "PREFLIGHT_REQUIRED",
    "archive": "PREFLIGHT_REQUIRED",
    "research": "PREFLIGHT_REQUIRED",
    "connect": "PREFLIGHT_REQUIRED",
    "resume": "PREFLIGHT_REQUIRED",
}
MAX_COMMAND_LENGTH = 4096
MAX_SOURCE_LENGTH = 250000
_URL = re.compile(r"^https?://[^\\s<>]+$", re.ASCII)
_TRANSCRIPT_LINE = re.compile(r"^(?:\\[?\\d{1,2}:\\d{2}(?::\\d{2})?\\]?\\s+|(?:speaker|host|guest|interviewer|participant)\\s*\\d*\\s*:\\s+)", re.IGNORECASE)
_PATTERN = re.compile(r"^nexus[ \t]+([a-z]+)(?=$|[ \t:])", re.ASCII)


@dataclass(frozen=True)
class TriggerDecision:
    status: str
    command: str | None
    reason: str


def classify(message: str, *, trusted_user_turn: bool, nexus_disabled: bool = False) -> TriggerDecision:
    """Classify one complete trusted top-level user message; never execute.

    A host is responsible for ensuring the text is a genuine user turn rather
    than a quotation, attachment, forwarded content, or model/tool output.
    """
    if type(message) is not str or type(trusted_user_turn) is not bool or type(nexus_disabled) is not bool:
        return TriggerDecision("BLOCKED", None, "Invalid input or provenance")
    if not trusted_user_turn:
        return TriggerDecision("NORMAL", None, "Untrusted text cannot activate Nexus")
    # Direct user-pasted source material may request intake preflight only.
    # A host must ensure the entire content is a genuine direct user paste,
    # not a quotation, forwarded tool result, or untrusted attachment.
    if not nexus_disabled and len(message) <= MAX_SOURCE_LENGTH:
        candidate = message.strip()
        if _URL.fullmatch(candidate):
            return TriggerDecision("PREFLIGHT_REQUIRED", "link_intake", "Pasted URL candidate; validate URL, source type and authorization in host")
        lines = [line.strip() for line in candidate.splitlines() if line.strip()]
        transcript_lines = sum(bool(_TRANSCRIPT_LINE.match(line)) for line in lines)
        if len(lines) >= 4 and transcript_lines >= 3 and transcript_lines * 2 >= len(lines):
            return TriggerDecision("PREFLIGHT_REQUIRED", "transcript_intake", "Pasted transcript candidate; host must confirm provenance, scope and authorization")
    if len(message) > MAX_COMMAND_LENGTH:
        return TriggerDecision("NORMAL", None, "No bounded explicit command")
    text = message.strip()
    if not text:
        return TriggerDecision("NORMAL", None, "Empty ordinary message")
    if text.lower() == "nexus off":
        return TriggerDecision("DISABLE", "off", "Host must persist session opt-out")
    if nexus_disabled:
        return TriggerDecision("NORMAL", None, "Nexus disabled for this conversation")
    match = _PATTERN.match(text.lower())
    if match is None:
        return TriggerDecision("NORMAL", None, "No explicit Nexus prefix")
    command = match.group(1)
    status = COMMANDS.get(command)
    if status is None:
        return TriggerDecision("BLOCKED", None, "Unknown explicit Nexus command")
    return TriggerDecision(status, command, "Classification only; host authorization and preflight required")
