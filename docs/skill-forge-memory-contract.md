# Skill Forge memory contract v0.1

Proposed for [issue #295](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/295). The merged [SQLite transport](../src/nexus_sandbox/sqlite_memory_transport.py) and [Cortex adapter](../src/nexus_sandbox/cortex_adapter.py) implement the offline single-worker persistence baseline. This contract defines the metadata and verification semantics for future adapters.

## Context module revision

| Field | Required meaning | Existing offline mapping |
| --- | --- | --- |
| `schema_version` | Literal `skill-forge.memory.v0.1` for an exported revision envelope | Envelope pending |
| `store_scope` | Stable configured namespace for the destination store and tenant. Treat `(store_scope, module_id)` as the record identity. | Dedicated transport and journal paths; explicit scope pending |
| `module_id`, `name`, `version` | Stable opaque ID within the store scope, lookup name, positive integer revision. Creation starts at version 1 and updates preserve the ID and increment the version once. | `Module.id`, `name`, `version` |
| `content`, `content_sha256` | Exact UTF-8 content and lowercase SHA-256 of its bytes. Whitespace and line endings are significant. | `Module.content`; explicit digest pending |
| `dependencies` | Ordered directed edges from this module to dependency names in the same store scope. Self-edges and duplicate names are invalid. A name is a reference to a module and does not pin its revision. | `Module.dependencies` tuple |
| `source` | Object with `authority`, `store_scope`, `record_id`, `revision_id`, and `content_sha256` for the content used. Use `null` if the exact revision cannot be established. A verified envelope requires the object and fresh comparison with the source. | `Write.source` binds an exact module snapshot in the journal for synthetic evidence |
| `observed_at_utc` | UTC timestamp of the observation in RFC 3339 form ending in `Z`. It records observation time, while the source revision identifies the actual input. | Journal event timestamp, separate from the module |
| `verification` | Status `unverified`, `verified` or `held`, with evidence class, observation time, and a reference to the receipt or verification event. | Journal verdict, checkpoint, and event |

Use one journal per configured store scope with the current adapter. A future portable journal must persist the scope in the binding before it can share a journal across stores. Verification uses `offline_synthetic`, `authenticated_read_only`, or `live_write` as its evidence class. `verified` requires a receipt or event reference. Held and unverified observations cannot advance a mission checkpoint. Persist provider IDs and revision identifiers as opaque strings in source references. If the provider omits reliable revision metadata or the exact-content digest cannot be established, retain the observation as unverified and hold any operation that requires verified provenance. For an original transcript, use the Notion source reference. Derived Cortex outputs cite that reference. Local SQLite records carry synthetic evidence.

## Operations and resume

1. **Read.** Report exactly one of found, explicitly absent, or unknown. A timeout, authorization failure, malformed result, or ambiguous match is unknown. Return the full snapshot for found, including content and ordered dependencies.
2. **Write intent.** Before any effect, durably bind the idempotency key to the store scope, operation, exact source revision, destination, content, ordered dependencies, and expected target state. The expected state is absence for create or the exact prior snapshot for update. Reject a reused key with different bindings.
3. **Verify.** After the effect, freshly read source and target. Verify source, target identity, revision, content bytes and dependency order. Mark verified only when all required comparisons succeed. An operation outcome such as acknowledged or unknown is recorded separately from its verification verdict.
4. **Resume.** Reopen the retained journal on restart. After a durable send intent, reconcile by reading first. Reuse the verified result when exact readback succeeds. A mismatch, an unreadable result, or a missing target after an uncertain send enters held status. A held attempt requires reconciliation before any new write.
5. **Mission checkpoint.** Record the mission ID, monotonic sequence, observation time, current and previous checkpoint digests, and a reference to the exact verified operation evidence. Advance only after verification and preserve accepted history as an immutable prefix. [The existing ledger](../src/nexus_sandbox/checkpoint_ledger.py) defines the paired-provider recovery format and transition checks. Mapping a memory receipt into that format requires genuine copy and packet bindings where the paired format is used. A local journal event provides local evidence and does not establish paired recovery.

For the provider-neutral mission checkpoint, the first sequence is 1 and the first previous digest is `null`. The SHA-256 preimage is the checkpoint body with fields `mission_id`, `sequence`, `observed_at_utc`, `previous_checkpoint_sha256`, and `verified_receipt`, excluding its own `checkpoint_sha256`. The receipt reference contains `store_scope`, `receipt_id`, and `receipt_sha256` over the exact retained receipt bytes. Use the existing ledger's canonical UTF-8 JSON encoder for the checkpoint body. A resume validator checks the checkpoint digest, contiguous sequence, previous digest, and the referenced receipt before accepting it. Receipt verification still depends on the authority and scope of the underlying evidence.

Use an append-only receipt history for verification and reconciliation. The bounded write implementation runs one worker. Enabling concurrent writers requires destination-side conditional writes or an equivalent validated fencing mechanism.

## Evidence and read-only trial

The [SQLite integration tests](../tests/unit/test_sqlite_memory_transport.py) cover exact offline restart readback, recovery after an interrupted write, and versioned updates. [Post-merge evidence](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/43646603065) covers the existing baseline. Envelope serialization, explicit digest and provenance readback, and mission checkpoint mapping remain implementation work.

For a separately authorized Cortex read-only trial, use an explicitly allowed module with an expected identity. Verify the effective principal and module access, then record whether a fresh read returns the expected identity, revision, content and edges. Missing credentials, missing access, or ambiguous identity yield a hold. Record the evidence class as authenticated read-only, with call count and measured latency, and cost when available. The trial requires permission to read and does not grant write authority.
