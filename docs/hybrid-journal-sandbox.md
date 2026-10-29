# Hybrid journal sandbox boundary (PR #76)

Status: design and offline code only. No live Notion host callbacks, durable
external journal service, schedule, production access, or Cortex sync is activated.

## Roles and authority

- Execution: the existing private SQLite runner journal is authoritative for
  owner binding, inbox, intent, receipts, and uncertain-write reconciliation.
  It needs a persistent trusted host. **GitHub-hosted Actions runners are
  ephemeral** and cannot provide cross-run journal durability by themselves.
- Notion: an optional, non-authoritative checkpoint projection for inspection,
  audit evidence, and next-action context. It cannot claim atomic task ownership,
  globally fenced writes, or exactly-once remote execution.
- Cortex: intended knowledge layer for separately verified outcomes.
- GitHub Actions: trigger and CI evidence, not custody of the SQLite database.
  The new passive workflow is manual-only, emits an explicitly non-canonical
  artifact, and does not invoke this projection.

## Host callback contract

`NotionCheckpointProjection(find_exact=..., create=..., enabled=False)`
is disabled until a trusted host explicitly enables synthetic fixture writes.

- An authorized host must bind **one dedicated sandbox destination**, not an
  existing Foundation Audit page, and enforce credentials and destination scope.
- `find_exact(event_key)` must complete a fresh, complete, untruncated read of
  the destination; return `None` only if the key is provably absent; return
  `{"digest": sha256, "body": canonical_json}` only for exactly one matching
  record. Conflicting duplicates, pagination gaps, malformed data, unavailable
  reads, or unauthorized scope must **raise**, never look like absence.
- `create(event_key, digest, canonical_json)` makes at most one bounded
  append. Its host must not hide ambiguous writes with implicit retries.
- The projection verifies both digest and **full serialized body** after
  creation or replay. A lost create acknowledgment returns `HOLD` and the
  caller can later read/observe; it must not retry blindly.
- `PENDING`, `HOLD`, `VERIFIED` are journal snapshots. A changed snapshot
  at the same event key conflicts and holds: no replacement or mutation is
  implemented. For historical updates the host should choose versioned
  immutable keys based on the journal's sequence and immutable run identity.
- The host must independently authenticate origin, authorized writer,
  destination, and event-to-journal linkage. A content hash alone does not
  establish authenticity; Notion does not serve as an execution fence.
- A verified projection does not prove execution success or let the runner
  skip its own readback.

## Validation boundaries

Offline tests cover disabled calls, first create/readback, duplicate replay,
lost acknowledgment, conflicting records, incomplete readback, and restart
through a fresh projection object. These are **mock-host tests**, not a Notion
API integration test or proof of cross-run durable execution.

Before enabling an opt-in live sandbox projection, provision a dedicated
destination and narrowly scoped host credentials, review pagination and
duplicate detection, verify a read-only complete inventory, then authorize
one synthetic write and a separate fresh readback. Do not repurpose the
Foundation Audit write probe; it has different binding and event schema.

Before scheduling PASSIVE or enabling ACTIVE side effects, additionally prove
journal persistence/recovery across separate trigger runs, establish
single-worker custody or a transactional fencing mechanism, and validate
manual stop, retention, and no-blind-retry handling. Keep PR draft until the
remaining gates have evidence.
