# Cortex fail-closed outbox policy (proposal)

## Purpose
Continue Nexus analysis and evidence generation while Cortex OAuth, effective grants and real remote fencing remain unverified. This is a **workaround for workflow continuity, not Cortex persistence**.

## Capability matrix
| Operation | Default | Condition |
|---|---|---|
| Read Notion approved synthetic fixture | ALLOW | Existing read-only authorization and exact page binding |
| Research, summarize, Gemini independent review | ALLOW | Approved source, content bounds and provenance |
| Prepare Cortex mutation proposal | ALLOW | Schema validated; no credentials or private transcript bodies in GitHub artifacts |
| Store content-free proposal manifest and hash | ALLOW | Minimal metadata, retention and access review |
| Store full original transcript in GitHub artifact | DENY | Notion remains canonical archive |
| Cortex API read | DENY by default | Require independently verified installation identity and scoped read grants |
| Cortex create/update/delete | DENY | Require verified grants, explicit approved scope, authoritative writer, atomic remote fencing or quiescent exclusive gateway, and independent readback |
| Automatic retry after timeout | DENY | Reconcile original request; no blind retries |
| Multiworker live mutation/takeover | DENY | CP09 remote boundary not proven |
| Agent bypass or credential exposure | DENY | No direct provider writes outside verified gateway |

## Manifest (no transcript content)
Fields: schema_version, source_system, source_id_hash, source_digest, operation, target_key_hash, request_id, status, evidence_refs, created_at. All hashes SHA-256 hex; status initially PREPARED. Do not interpret PREPARED or a CI PASS as remotely COMMITTED.

## Promotion gate
A human-approved scope and independently verified effective credentials are necessary but not sufficient. Commit requires remote conditional mutation or proven exclusive gateway and old-writer quiescence; subsequent authenticated readback and durable receipt. If any precondition fails, remain PREPARED/BLOCKED. No direct Cortex call in this proposal.

## Deferred verification
Cortex OAuth/installation identity, scoped grants, source-target mapping, write/readback, and real CP09 stale-worker rejection. A machine may help diagnostics but is not itself proof of capability.
