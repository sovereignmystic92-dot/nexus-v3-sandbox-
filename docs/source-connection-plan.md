# Shared source plan: transcript intake, knowledge development and CSF

Status: offline preparation only. Skill Forge is excluded by owner direction.
Mission: connect existing source references without adding an executor or store.
Base inspected: a87d6f0a2e3b9874d43309271eb19864a85bd08f.

## Coherence review: REFINE existing intake

The existing Notion-to-CSF host contract already describes two consumers after
one intake. `csf_notional_intake.prepare_source_receipt` validates source bytes;
`transcript_receipt_bridge` records independently authenticated archive evidence;
`execute_supervised` governs new qualifying transcript processing; knowledge
mastery has its own evidence and promotion gates. A second archive, global
completion state machine, or new processing worker would duplicate these roles.

`prepare_connection_plan` therefore reuses the existing intake validator and
exports metadata only. It does not export normalized segments or raw text.
The SHA-256 pin must describe the exact UTF-8 transcript. A matching digest
does not prove provider authentication, full pagination, source provenance,
video-audio accuracy, or independent factual corroboration.

| Shared field | Existing consumer contract | Meaning |
| --- | --- | --- |
| `source.document_id` | CSF `document_id`; remove `notion:` for supervised `source_page` and analysis gate `source_id` | Same canonical Notion page |
| `source.source_revision` | CSF `source_revision` | Exact source revision; host must freshly verify |
| `source.source_sha256` | CSF `content_digest`; analysis gate `source_sha256` | Exact original bytes |
| `source_key` | Shared plan reference | Revision-bound grouping, not a replacement for consumer idempotency keys |
| `consumers[].work_key` | Planned consumer work | Bound to source, mission, code and policy; not provider write authority |
| `consumers[].receipt_ref` | Future retained execution/evaluation receipt | Always null in preparation; no completion is inferred |

The knowledge development and CSF entries start separately at NOT_STARTED.
Knowledge mastery still requires actual evaluation IDs, rubrics, independent
evidence, contradiction handling and the existing Cortex promotion gate.
CSF keeps existing saved claim IDs, finding identities, review bindings and
destination checks. The shared plan does not generate any of these receipts.

## Host integration still required

1. Authenticate the canonical archive, full content, revision and destination
   grants; resolve existing transactions and receipts before new processing.
2. Prepare the source-bound plan under an explicit mission and pinned code and
   policy revisions. Retain it in authorized engineering evidence storage and
   independently read it back. Metadata can still be private: do not publicly
   publish real source IDs, mission context or transcripts without approval.
3. Submit new qualifying processing only through `execute_supervised` with the
   complete analysis gate or its authorized CLI. Preserve its durable journal.
4. Link genuine knowledge evaluations and CSF outcomes separately to the shared
   source key. Native receipts remain authoritative for their exact scope;
   completing one consumer does not complete the other.
5. Reconcile uncertain outcomes against retained intents and actual readbacks.
   Stable plan keys alone do not prevent duplicate provider effects. New code,
   mission or policy bindings change work keys and must not authorize retries.

No automatic dispatcher, schedule, event subscription, independent review,
mastery promotion, or audit-status change is installed. The two-AI production
approval policy remains binding where applicable. Preparing this draft requires
no Gemini call or account connection.

## Connected supervised persistence milestone

`execute_connected_supervised` makes receipt readback mandatory **within this
opt-in entrypoint**. It delegates all processing to the existing
`execute_supervised`, retaining its complete analysis gate, durable journal,
explicit create grant, output identity checks and uncertain-write hold. Existing
callers and the standard CLI are not silently redirected. Live invocation can
write Cortex only through the original explicitly authorized host path; this
draft has not invoked any real provider operation.

The wrapper validates the unchanged shared plan, binds the mission to the
analysis gate, and asks the trusted host to freshly verify the exact source
reference (including revision) before archive reads. Invalid gate evidence is
rejected by the original host before even this source-metadata read occurs.

Before the first archive request reaches the provider, the host checks for an
existing retained receipt by work key. An unreadable receipt blocks before any
output create. An existing receipt forbids replacement creates, even if an
execution journal is missing. The existing host may retain an INTENT hold when
that create is denied: preserve it for operator reconciliation, never reset it.
After output readback matches, the host freshly retrieves the receipt again;
an existing record changing or disappearing blocks reconciliation.
Confirmed absence returns `PENDING_RECEIPT` with a
`receipt_to_retain` envelope: `schema=nexus.connected-supervised-receipt.v1`,
an exact plan/source/consumer/work/output/owner binding, and the full native
execution receipt. The caller must save this through an authorized durable
checkpoint path. The wrapper has no receipt writer and performs no retries.
Denied access or a timeout must raise, never become confirmed absence.

Re-enter using the same plan and execution journal, preferably with
`allow_create=False`. The trusted `read_retained_receipt(work_key)` callback
must freshly fetch that exact durable record and return exactly `reference`
(its stable identity) and `content` (the exact UTF-8 JSON bytes). It must not
return a cached `receipt_to_retain` or echo caller memory as independent evidence.
The library validates the complete retained binding and native execution receipt.
Receipt reference identities must be nonempty strings of at most 512 characters
without surrounding whitespace. Invalid identities are rejected, not normalized.
Only the historical integer `create_requests` count (0 or 1) may differ on
read-only replay; other execution evidence must match. Duplicate JSON keys,
nonfinite values and receipts over 1 MiB are rejected.

After fetching the receipt, another guarded read-only execution must match the
actual source/output, followed by a fresh source revision check. Only then does
the wrapper return `CONSUMER_PERSISTENCE_READBACK_MATCHED` with the exact receipt
reference and SHA-256. It verifies **one consumer's persistence milestone**, not
overall project completion, independent factual review, CSF acceptance, mastery,
knowledge promotion or audit closure. The linked milestone itself still needs
authorized durable retention/readback before reporting transaction completion.

This is host-mediated evidence, not proof that Python callbacks authenticate
themselves. Hosts retain responsibility for provenance, fresh full pagination,
grants, exact receipt destination identity, authorizations and journal custody.
There is no distributed transaction or remote fence: concurrent mutation between
observations remains outside this single-worker baseline.

Host integration must allocate distinct `journal_path` and `output_name` values
for each `(plan_id, consumer)` and retain the mapping before execution. The
native journal does not include consumer identity: differing native bindings
fail closed, but identical native bindings could reuse one journal. Do not
assume the journal alone enforces cross-consumer allocation. The wrapper binds
the consumer in its separate receipt and does not install that host allocator.
The host must also verify that the pinned code and policy revisions correspond
to the actual execution environment; supplied revision strings are not proof.

## Validation and rollback

Run `PYTHONPATH=src python -m unittest discover -s tests/unit -p
'test_source_connection_plan.py' -v` as one shell command. Tests use synthetic
source identities and cover exact-byte changes, replay, revision/context changes,
identity mismatch, missing pins, unknown fields and no completion inflation.

The connected-host suite adds real local SQLite journal execution with synthetic
ports: pending receipts, read-only replay, cross-consumer mismatch, receipt
failure/disappearance, output/source mutation, malformed receipts, missing gate
preflight and uncertain-write holds. Run with `PYTHONPATH=src python -m unittest
discover -s tests/unit -p 'test_connected_supervised_host.py' -v` as one command.
These checks do not establish live account access or independently certify review.

Rollback removes this opt-in module, tests and document; retain any actual
operational journals and receipts. Existing consumers and workflows are unchanged.
