# Nexus persistent authority transition — proposal

Status: PROPOSED / NOT ACTIVATED. Owner decision recorded 2026-10-28: Cortex becomes primary persistent knowledge; GitHub remains authority for code and execution evidence; Notion becomes legacy reference/migration source.

## Authority
- Cortex: canonical knowledge, mission context, decisions, checkpoint summaries, and pointers to evidence.
- GitHub: canonical source code, workflow definitions, commits, CI logs, immutable run IDs, and test artifacts.
- Notion: historical source only pending inventory, reconciliation and verified migration. Do not erase or rewrite historical records.
- Neither Cortex nor GitHub may assert the other's success without direct readback of the authoritative source.

## Initial transport
1. Observe a bounded GitHub event (run ID, commit SHA, workflow, conclusion, timestamps, artifact links).
2. Normalize a deterministic event key and content digest; avoid secrets and personal data.
3. Persist intent and binding in the durable single-worker journal before any Cortex write.
4. Read exact Cortex destination; create/update only within an explicit allowlist and verified ownership scope.
5. Read back and compare exact content, identity and version; mark VERIFIED only on match.
6. On timeout, drift, conflict or uncertain write, HOLD with the last confirmed checkpoint and an explicit resume action; never blindly retry.
7. Record the GitHub evidence pointer and Cortex receipt without duplicating an event.

## Safeguards
- Default read-only until fixture-specific live write tests pass; no production migration by implication.
- No automatic Notion deletion, backfill or canonical promotion without source-by-source reconciliation.
- No secrets in public GitHub; credentials remain in protected execution environment.
- Existing Cortex adapter lacks compare-and-swap; retain single-writer restriction. CP09 multiworker fencing remains separate and unverified.
- Independent Gemini review can inspect evidence but must not inherit a prior reviewer's verdict as proof.
- Do not change audit checkpoint acceptance from this policy document alone.

## Acceptance stages
A. Verify GitHub event read and exact stable identifiers.
B. Verify Cortex synthetic fixture create/update, independent readback and journal restart.
C. Verify idempotent reprocessing, uncertain-write HOLD, and recovery without duplication.
D. Verify a bounded real record with owner-approved scope and independent evidence.
E. Enable a trigger-driven sync only after A–D pass, with monitored failures and bounded retries.

Implementation status: design recorded only; no GitHub→Cortex runtime trigger, scheduled sync, or live record migration has been installed by this change.
