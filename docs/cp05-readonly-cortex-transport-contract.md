# CP05 — Read-only Cortex runtime transport acceptance contract

Status: **PROPOSED / NOT DEPLOYED**. This document authorizes no credentials, provider writes, workflow changes, or gate closures.

## Objective
An approved Nexus execution host must read the existing Notion source and Cortex module under its **own effective principal**, verify identity and provenance, and produce an independently inspectable, zero-write reconciliation receipt. ChatGPT connector access is not transferable to GitHub Actions.

## Target (positive control)
- Notion source page ID: `40b8c067daa481a3bc7ee289c8f7f050`
- YouTube source video ID: `kokDVXUGdes`
- Existing Cortex module ID: `module_01m6b6fdsz1s0ma4rqhvbdpe10`, previously observed revision `1`
- Notion source fidelity: **structured source, not a verbatim transcript**. Do not assert full-transcript completion.
- Do not create or update this Cortex module.

## Required transport properties
1. **Host identity**: documented service principal and permission scope, obtained from the provider's supported authentication method; no credentials in code, logs, issues, fixtures, or PRs. Explicitly verify the runner's own grant. Connector access in a chat is not evidence of host access.
2. **Read-only operation**: allow only exact-target GET/read operations for the Notion page and Cortex module. Reject all create, update, delete, archive, and mutation operations. No implicit discovery writes.
3. **Deterministic binding**: match Notion page ID, YouTube video ID, exact canonical source URL in Cortex content, Cortex module ID and observed revision; report changed revisions as stale rather than silently accepting them.
4. **Digest integrity**: only calculate a SHA-256 over a documented canonical source representation returned by the actual provider. Never substitute a fixture digest. Structured text cannot be marked verbatim.
5. **Uniqueness**: require exactly one matching existing Cortex module. If provider search is incomplete, report `INDETERMINATE_INVENTORY` rather than `NO_MATCH`. Zero or multiple candidates fail closed.
6. **Authority separation**: read permission is not write permission. Do not pass `cortex_authority_verified=True` to `validate_output_route` on read-only evidence. A read-only reconciliation cannot mark processing or persistence complete.
7. **Bounded execution**: limit calls, timeout, retries, rate budget, and maximum response size; fail closed on auth denial, timeout, malformed response, stale revision, missing provenance, or service unavailability.
8. **Evidence receipt**: record host identity reference (not token), timestamp, source and module IDs/revisions, fidelity, provenance checks, read counts, write count (must equal zero), outcome, and hashes only when actually computed. Independently read back the resulting run/receipt.

## Required negative cases
- No/expired Cortex credentials; insufficient read grant; provider timeout/429/5xx.
- Notion source ID or YouTube ID mismatch; missing Cortex source URL.
- Cortex revision drift; zero/multiple matches; truncated inventory.
- Source digest missing or computed from different canonicalization.
- Any attempted write or accidental use of a synthetic-only adapter on a real module.

## Acceptance
**PASS_READ_ONLY_MATCH** requires actual host-authenticated provider reads, unique exact match, valid provenance, explicit non-verbatim status, zero writes, and independent receipt readback. It is **not** `ROUTE_VERIFIED`, does not prove write authority or autonomous delivery, and does not close CP05 or CP09.

Current blocker: No approved Cortex API transport or runtime principal has been established for the GitHub runner. Do not add a secret or enable a scheduled live probe without explicit supported provider documentation and review.

Tracking: GitHub Issue #91; prior offline regression PR #160.
