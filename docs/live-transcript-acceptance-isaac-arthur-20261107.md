# Live transcript acceptance fixture — Isaac Arthur (2026-11-07)

## Scope and authorization
Owner approved a bounded real-world integration test of **The First Interplanetary War: Tactics in the Solar System**. This document is an evidence index and acceptance contract, **not** an execution receipt or a claim of automated processing. Never copy transcript text or credentials into CI logs. Existing manual connector writes are not GitHub-runner writes.

## Verified manual connector artifacts
- Original episode: https://www.youtube.com/watch?v=oGLnL0Fqluk
- Notion intake: https://app.notion.com/p/4128c067daa48117a96dc2d7b14452bd
- Notion transcript copy: https://app.notion.com/p/4128c067daa48122932aeb1105061ba1 (readback observed; exact source comparison **pending**)
- Notion Nexus Output: https://app.notion.com/p/4128c067daa481f19ba6de8ec0cc0dc7 (readback observed; provisional)
- Cortex derived module: `module_01m6wdjh6a8bvvz5s8vcxkx969` (version 1; search readback observed)
- Tracker: https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/202

## Gate A: source integrity
- Acquire the **exact** user-authorized original transcript through an authenticated immutable intake; never use a paraphrase or reconstructed public subtitle track.
- Compute UTF-8 SHA-256 and byte count from the exact source bytes. Preserve punctuation, errors, repeated phrases, sponsorship and attribution. No trimming or newline normalization without separately recording transformation and keeping raw bytes.
- Independently fetch stored Notion content and compare canonical raw bytes. If Notion's Markdown renderer changes whitespace/formatting, store a byte-preserving attachment or segmented raw data with deterministic reassembly and recheck.
- If any mismatch, record first offset and source/stored hashes; **block** source-fidelity pass.

## Gate B: authorization and runtime execution
- Trigger a real GitHub Actions event/schedule with source ID, checksum and idempotency key; verify owner principal, effective grants, destination IDs, policy version and source ownership before writes.
- No provider credential values in artifacts, logs or issues; no privileged pull_request_target; fail closed if runtime credentials, identity or destination checks are absent.
- Log GitHub run ID/attempt, event ID, policy decision and relevant actor identities.

## Gate C: readback and reconciliation
- Before writing, resolve existing Notion and Cortex IDs above. Update/reconcile only if authorized; never create duplicates on replay.
- Independently read back source and derived output after write. Store redacted receipt: source SHA-256, event/run IDs, Notion/Cortex IDs, verification outcomes, retry state and timestamp.
- Replay the same event: assert identical IDs and **zero additional creations**. Inject a partial failure and verify recovery without duplicate output.

## Gate D: operational promotion
- Require five consecutive independently verified real scheduled/event-triggered runs, not manual ChatGPT connector invocations or synthetic fixtures.
- Update CP03/CP04/CP05 audit gates only with actual linked runner logs, redacted receipts and readback evidence.

## Current verdict
**Manual integrations demonstrated. Full-fidelity checksum, unattended event trigger, runner enforcement, receipt, idempotency and five-run sequence NOT demonstrated.** No audit checkpoint promotion authorized by this document.
