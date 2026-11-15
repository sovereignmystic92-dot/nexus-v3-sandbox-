# Skill Forge memory contract v0.1

Proposed for [issue #295](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/295). The merged [SQLite transport](../src/nexus_sandbox/sqlite_memory_transport.py) and [Cortex adapter](../src/nexus_sandbox/cortex_adapter.py) implement the offline single-worker persistence baseline. This contract defines the metadata and verification semantics for future adapters.

## Context module revision

| Field | Required meaning | Existing offline mapping |
| --- | --- | --- |
| `schema_version` | Literal `skill-forge.memory.v0.1` for an exported revision envelope | Envelope pending |
| `module_id`, `name`, `version` | Stable opaque ID within the store scope, lookup name, positive integer revision. Creation starts at version 1 and updates preserve the ID and increment the version once. | `Module.id`, `name`, `version` |
| `content`, `content_sha256` | Exact UTF-8 content and lowercase SHA-256 of its bytes. Whitespace and line endings are significant. | `Module.content`; explicit digest pending |
| `dependencies` | Ordered directed edges from this module to dependency names in the same store scope. Self-edges and duplicate names are invalid. A name is a reference to a module and does not pin its revision. | `Module.dependencies` tuple |
| `source` | Exact revision reference containing source authority, record ID, revision ID and SHA-256 over the content used. The reference must resolve to the same revision during verification. | `Write.source` binds an exact module snapshot in the journal for synthetic evidence |
| `observed_at_utc` | UTC timestamp of the observation in RFC 3339 form ending in `Z`. It records observation time, while the source revision identifies the actual input. | Journal event timestamp, separate from the module |
| `verification` | Status `unverified`, `verified` or `held`, with evidence class, observation time, and a reference to the receipt or verification event. | Journal verdict, checkpoint, and event |

Namespace every record identity by the configured store scope. Persist provider IDs and revision identifiers as opaque strings in source references. If the provider omits reliable revision metadata or the exact-content digest cannot be established, retain the observation as unverified and hold any operation that requires verified provenance. For an original transcript, use the Notion source reference. Derived Cortex outputs cite that reference. Local SQLite records carry synthetic evidence.

## Operations and resume

1. **Read.** Report exactly one of found, explicitly absent, or unknown. A timeout, authorization failure, malformed result, or ambiguous match is unknown. Return the full snapshot for found, including content and ordered dependencies.
2. **Write intent.** Before any effect, durably bind the idempotency key to the store scope, operation, exact source revision, destination, content, ordered dependencies, and expected target state. The expected state is absence for create or the exact prior snapshot for update. Reject a reused key with different bindings.
3. **Verify.** After the effect, freshly read source and target. Verify source, target identity, revision, content bytes and dependency order. Mark verified only when all required comparisons succeed. An operation outcome such as acknowledged or unknown is recorded separately from its verification verdict.
4. **Resume.** Reopen the retained journal on restart. After a durable send intent, reconcile by reading first. Reuse the verified result when exact readback succeeds. A mismatch, an unreadable result, or a missing target after an uncertain send enters held status. A held attempt requires reconciliation before any new write.
5. **Mission checkpoint.** Record the mission ID, monotonic sequence, observation time, current and previous checkpoint digests, and a reference to the exact verified operation evidence. Advance only after verification and preserve accepted history as an immutable prefix. [The existing ledger](../src/nexus_sandbox/checkpoint_ledger.py) defines the paired-provider recovery format and transition checks. Mapping a memory receipt into that format requires genuine copy and packet bindings where the paired format is used. A local journal event provides local evidence and does not establish paired recovery.

Use an append-only receipt history for verification and reconciliation. The bounded write implementation runs one worker. Enabling concurrent writers requires destination-side conditional writes or an equivalent validated fencing mechanism.

## Evidence and read-only trial

The [SQLite integration tests](../tests/unit/test_sqlite_memory_transport.py) cover exact offline restart readback, recovery after an interrupted write, and versioned updates. [Post-merge evidence](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/43646603065) covers the existing baseline. Envelope serialization, explicit digest and provenance readback, and mission checkpoint mapping remain implementation work.

For a separately authorized Cortex read-only trial, use an explicitly allowed module with an expected identity. Verify the effective principal and module access, then record whether a fresh read returns the expected identity, revision, content and edges. Missing credentials, missing access, or ambiguous identity yield a hold. Record the evidence class as authenticated read-only, with call count and measured latency, and cost when available. The trial requires permission to read and does not grant write authority.
