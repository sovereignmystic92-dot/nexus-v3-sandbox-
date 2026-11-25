# Supervised existing-output enrichment

Status: Python API implementation and offline synthetic tests. No live provider
update, dispatcher, CLI extension, deployment, independent review or gate closure
is established by this change. Existing create and legacy-reconciliation paths
retain their interface and journal bindings.

The ordinary `execute_supervised` entrypoint accepts optional `update_plan` and
`allow_update` arguments. When a plan is supplied, `analysis` means the exact
appendix, beginning with two newlines. `allow_create` must remain false. Omit
`allow_update` (default false) for read-only preflight/reconciliation.

The plan has exactly:

- `before`: the fresh complete seven-field snapshot: id, name, owner, integer
  version, content, dependencies (list) and parent (name or null).
- `enrichment_id`: the saved stable batch identity, 1–160 ASCII letters/digits,
  underscores, periods, colons or hyphens; first character alphanumeric. Keep it
  across rewording/retry. It is not a new ID for each attempt.
- `exclusive_writer_evidence`: bounded nonempty reference to the trusted host's
  independently established exclusive mutation custody for this operation.

The appendix contains exactly one line each for `NEXUS_SOURCE_PAGE=<pinned UUID>`,
`NEXUS_SOURCE_SHA256=<pinned source digest>` and
`NEXUS_ENRICHMENT_ID=<stable enrichment identity>`. Conflicting binding-marker
lines fail preflight. If the base already contains that enrichment identity or
exact appendix, reconcile the retained operation instead of making another one.
The code preserves all original content bytes, parent and dependency order.

Supply the standard complete `analysis_gate` sidecar, assessed against the **full
final output**, `before.content + analysis`. Its output ID is the existing
destination name. Source and output hashes, domain determinations and required
action evidence must be real and exact; test fixtures are not live assessments.
Validation happens before journal or provider access. The new source binding is
appended; legacy content is not silently prefixed or rewritten.

## Trusted dispatcher operations

`archive_read` and `cortex_get` follow the existing supervised-host contract.
The update reader returns exactly the seven fields above, extracted from a fresh
authenticated provider observation. Do not treat errors, denied access or a
partial search as a missing record.

The sole new callback is `cortex_update`. Its payload carries name, module_id,
expected_owner, expected_version, before_sha256, full desired content and the
exclusive_writer_evidence reference. It must update only the existing module's
body. Do not forward private content into public logs. The response is ignored:
fresh exact output and source reads are required to mark the journal VERIFIED.
The output must retain its identity/owner/relationships and have exactly the
baseline version plus one; unrelated subsequent edits require reconciliation.

These fields are **not** a Cortex API signature. A dispatcher must enforce
current account/destination grants and independently establish exclusive writer
custody before enabling this callback. It must not drop pins and call an
unconditional provider update without that custody. If exclusivity cannot be
established, stop; keep update disabled. This implementation supplies neither
provider credentials nor an authority-verification callback/service.

## Recovery and limits

Only one cooperating local worker sharing the journal/lock is supported.
Baseline reads and the local flock do not prevent an external writer racing the
mutation. No remote compare-and-set, lease, fencing, complete caller directory
attestation or CP09 acceptance is claimed. The evidence reference is bound
metadata, not verification that its contents are true.

The existing execution table retains a distinct append-operation binding,
including the original snapshot, source receipt, final output digest and gate
fingerprint. Other create/update/legacy journals cannot be repurposed. A durable
FULL-synchronous INTENT precedes one update request. An exception, lost response
or interruption leaves INTENT. Re-entry can verify an exact saved successor with
fresh source/output/source reads and zero writes; an unchanged baseline after
uncertainty never permits retry. A matching final object in a replacement journal
cannot adopt an effect without retained prior intent. Preserve the original
create journal separately; allocate a new approved enrichment transaction only
after reconciling all prior intents and establishing its authoritative mapping.

The caller must retain and independently read the returned execution receipt in
authorized durable custody before declaring delivery complete. A local VERIFIED
journal is not by itself a durable cross-store receipt or fresh-session test.

Use the Python API only. Existing private CLI and connected/custodied wrappers
are unchanged and do not expose update mode. A later integration must be reviewed
against their own operation allowlists and custody schemas. Rollback: revert this
API extension, helper, tests and instructions; retain journals/receipts and
reconcile effects, never reset intent to enable a replacement write.

Validation: `PYTHONPATH=src python3 -m unittest discover -s tests/unit -p
'test_transcript_supervised_update.py' -v` (one command). Tests use synthetic
provider ports, including stale/duplicate/uncertain outcomes. They do not establish
actual provider timeouts, account grants, writer exclusivity or Haiti delivery.
