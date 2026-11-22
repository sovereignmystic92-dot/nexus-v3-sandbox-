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
| `source.document_id` | CSF `document_id`; analysis gate `source_id` | Same canonical Notion page |
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

No automatic dispatcher, schedule, event subscription, Cortex write, independent
review, mastery promotion, or audit-status change is installed. The two-AI
production approval policy remains binding where applicable. Preparing this
draft requires no Gemini call or account connection.

## Validation and rollback

Run `PYTHONPATH=src python -m unittest discover -s tests/unit -p
'test_source_connection_plan.py' -v` as one shell command. Tests use synthetic
source identities and cover exact-byte changes, replay, revision/context changes,
identity mismatch, missing pins, unknown fields and no completion inflation.

Rollback removes this opt-in module, tests and document; retain any actual
operational journals and receipts. Existing consumers and workflows are unchanged.
