# CSF Chat ↔ Gemini collaboration protocol v0.1 (proposal)

Tracking: Issue #189; draft PR #190. This is a **message contract**, not a claim of live agent connectivity.

## Message envelope
Each exchange is an append-only GitHub issue comment or retained artifact containing:
- `protocol_version`: `csf-collab/0.1`
- `message_id`: unique, stable per message
- `thread_id`: `csf-189-pr-190`
- `actor`: `chat`, `gemini`, `codex`, or `owner`
- `role`: `proposal`, `critique`, `reconciliation`, `implementation`, `independent_review`
- `source_commit`: exact reviewed SHA, not a moving branch
- `contract_version`: `0.2.0`
- `in_reply_to`: message ID or null
- `evidence_refs`: resolvable repository paths, run URLs or source segments
- `claims`: explicit observations, inferences and unknowns
- `requested_action`: bounded next step
- `status`: `proposed`, `responded`, `blocked`, `verified`
- `execution_proof`: workflow run/job plus model-response artifact for any purported Gemini output

## Round-trip acceptance
1. Chat posts a versioned proposal tied to a specific commit.
2. A **real** authenticated Gemini execution consumes that exact proposal and records its response with job evidence. Merely scheduling an Action is insufficient.
3. Chat retrieves and acknowledges the response, identifies agreements/disagreements and writes a reconciled engineering decision.
4. Codex implements the approved bounded change; CI tests its effects.
5. Gate C independent analytical review requires a separately identifiable Gemini review of a frozen findings artifact. Collaborative design comments alone do not count.

## Security and cost boundaries
- Never place API keys or raw private transcripts in issue comments or logs.
- Existing Gemini live-review workflow is manual/read-only and requires explicit free-tier confirmation; no autonomous paid calls are authorized here.
- No automatic GitHub writes by Gemini until a separately approved, least-privilege write mechanism is tested.
- No Cortex/Notion writes, production promotion, merge, or approval inference from this protocol.
- Failed or absent Gemini calls remain `blocked`, never simulated as successful.

## Initial proposal packet
**Actor:** chat. **Role:** proposal. **Source:** PR #190 current frozen SHA at dispatch.
**Question for Gemini:** Review CSF v0.2 schema/validator parity, source-reference integrity, deterministic idempotency collisions and the isolated CI schema-path failure. Identify reproducible counterexamples, distinguish hard failures from hypotheses, and recommend the smallest safe fixes.
**Response format:** finding ID; severity; exact path/line or test evidence; reproduction; suggested correction; unresolved assumptions.
**Current state:** awaiting actual Gemini dispatch and authenticated response.
