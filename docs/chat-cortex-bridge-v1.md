# Chat–Cortex bridge v1: bounded handoff

Owner direction: https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/263

GitHub Actions does **not** possess authenticated Socra runner identity. This contract does not claim unattended execution. ChatGPT, when explicitly invoked, is the Cortex actor.

1. GitHub prepares a metadata-only handoff packet with `make_packet(fields)`. Source content must remain in the canonical archive. Use the actual source digest/revision, never a placeholder.
2. A ChatGPT turn receives the packet and checks source provenance, owner scope, destination and existing Cortex records before writing. The packet's approval reference is evidence to review, not self-authorizing permission.
3. If authorized, ChatGPT performs at most one bounded Cortex write using its own connector, then separately retrieves the exact destination and compares content, identity and source link. A search hit alone is discovery, not proof of exact readback.
4. Record a receipt with packet_id, actor, status, readback_matched and audit_gate_promoted=false. Use `validate_receipt` before accepting it. The receipt validates declared structure, **not** provider attestation or authorization.
5. GitHub can store non-secret receipts in a reviewed issue/PR. Never include tokens, raw provider responses or private transcript excerpts. A future trusted runtime must implement authenticated transport and independently check the evidence before audit promotion.

States: PENDING_CHAT_REVIEW → READ_ONLY_COMPLETE / READBACK_VERIFIED / BLOCKED. No CP05 or CP09 promotion. Idempotency is packet_id based; verify an existing destination before creating a new one. Stop on conflicting revisions, permissions, ambiguous destinations or uncertain writes.

Current live pilot: Cortex module `Nexus CP05 — Chat–Cortex Bridge Pilot 2026-11-08`, linked to Issue #263; separately searchable after creation. It is not proof of GitHub runner access.
