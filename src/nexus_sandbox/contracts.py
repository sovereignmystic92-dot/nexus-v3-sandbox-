"""Review-only contracts. No storage, network, imports of fixtures, or entry point."""

from dataclasses import dataclass
from typing import Literal, Protocol

State = Literal["NEW", "VALIDATED", "ARCHIVED", "OUTPUT_CREATED", "REGISTERED", "VERIFIED"]


@dataclass(frozen=True)
class Request:
    idempotency_key: str
    source_id: str
    source_revision: str
    destination_id: str
    payload_sha256: str
    source_complete: bool


@dataclass(frozen=True)
class Checkpoint:
    transaction_id: str
    state: State
    version: int
    disposition: Literal["OPEN", "BLOCKED", "INCOMPLETE", "VERIFIED"]
    next_action: str


class Coordinator(Protocol):
    """Implementation must enforce architecture and evidence contracts."""

    def submit(self, request: Request) -> Checkpoint: ...

    def resume(self, transaction_id: str, expected_version: int) -> Checkpoint: ...
