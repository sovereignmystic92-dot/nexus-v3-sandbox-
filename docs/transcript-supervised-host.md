# Supervised Chat host for archived transcript handoffs

This composition provides the standard gated `execute_supervised` entrypoint around
PR #284's `run_archived_handoff`. It installs no service, schedule, GitHub
workflow, credentials or provider endpoint. Review PR #284 first. The host must
supply authenticated calls; this module cannot authenticate itself.

Provide a private, owned, durable journal path, the independently pinned source
receipt/chunks, exact Notion page, Cortex name, expected owner, analysis and an
explicit create grant, plus the complete `analysis_gate` sidecar described in
analysis-evidence-gate.md. Missing/malformed evidence is rejected before journal
or provider access, including read-only calls. The function invokes
`request(operation, payload)`:

| Operation | Host action / response |
| --- | --- |
| `archive_read` | Fresh full source read, returning the existing indexed archive observation schema. Validate source container identity and completeness before returning. |
| `cortex_get` | Fresh exact-name get in the confirmed account; return ID, name, owner, version and content, or confirmed absence. Never turn denied access or failed reads into absence. |
| `cortex_create` | One exact-name create of the provided content in the independently confirmed destination. No update, overwrite or automatic retry. Return value is ignored; a fresh get must verify the saved object. |

The request callable belongs to the trusted host. Operation payloads can include
private analysis: use private IPC, never public logs, committed examples or tool
transcripts containing secrets. It is not a credential/token transport.

The host must independently enforce current provider grants, account/parent
selection, operation allowlists and payload limits. Expected-owner checks are
readback checks, not proof of account identity or complete grants. Caller flags
do not provide authorization. The module has no source writer.

A SQLite FULL-synchronous intent precedes the create request. An unknown result
leaves INTENT. A later exact source/output read may reconcile that intent; an
absent output cannot release it. Existing exact output is reused; a different
module ID after verification or conflicting content stops the transaction.
The same journal binds source, analysis hash, name and owner. It must survive
host restarts and must not be deleted to bypass a hold. Losing it requires
operator reconciliation. Local flock covers cooperating workers sharing the
path only; distributed ownership and remote fencing remain unimplemented.

Every successful invocation checks fresh source, fresh output, and source again.
Before a create, an additional fresh source read is required. Save the returned
execution receipt in the authorized durable checkpoint and independently read
it back before reporting the supervised operation complete. Report actual
module version and ID separately from the name-based handoff result.

## Validation and limits

Run `PYTHONPATH=src python -m unittest discover -s tests/unit -p
test_transcript_supervised_host.py -v` (as one command). Tests cover one create,
fresh read-only replay, committed/absent uncertain outcomes, source mutation,
owner/identity drift, journal rebinding, read failure and denied create.
These are offline synthetic tests, not live authentication evidence.

A supervised connector pilot is separate from deployment. No standalone host
tool dispatcher or unattended runtime is installed by importing this function.
The caller must implement and review the request callable. Published-audio
accuracy, analysis quality, independent Gemini review, total host loss, remote
CAS, five real ingestion runs and audit closure are outside this entrypoint.

## Private command protocol

Run `PYTHONPATH=src python -m nexus_sandbox.transcript_supervised_cli --config
/private/mission.json --journal /private/execution.sqlite` as one command.
The standard config has exactly prepared, source_page, source_sha256, output_name,
analysis, expected_owner and analysis_gate. In JSON the gate has exactly binding,
required_domains (a list) and report. The CLI validates this envelope and converts
the domain list to the API's tuple; the same host guard validates its contents.
Default write mode is read-only, with structural analysis checks still mandatory.
Add `--allow-create`
only for a separately authorized exact-destination create. A config field
cannot turn writes on.

The command emits one JSON line per host request: type=request, monotonically
increasing integer id, operation and payload. The private trusted dispatcher
performs that connector call and replies with exactly id, ok=true and value.
An explicit ok=false response stops; never translate it to absence. A final
type=result contains the execution receipt; exit 0 requires READBACK_MATCHED.
Failures exit 2. No provider error bodies are printed. Keep stdin/stdout private:
requests can contain analysis. This is an IPC channel, not public job logging.

Config and individual messages are bounded to 1 MiB. Duplicate keys,
nonfinite JSON, wrong reply IDs, unexpected fields, EOF, unsolicited extra
messages and incomplete host response delivery after 45 seconds stop execution.
The deadline covers partial response delivery too. Retain the journal
after any interruption. No credential or endpoint settings are accepted.

Six subprocess protocol tests cover real process reopen/replay, committed
create with response EOF and reconciliation, mismatched response identity,
failed host response, unexpected config fields and read-only default. These
are local synthetic process tests, not live provider timeout evidence. A seventh
pipe test verifies that a partial response cannot defeat the total deadline.

Rollback: revert the default-gate change to restore the earlier host/CLI
interface. Preserve real execution journals/receipts for reconciliation; do not
replay uncertain creates under a new journal or edit their binding to downgrade
the recorded assessment.

## Existing ungated journals

For an explicitly authorized recovery of an older ungated transaction, use the
separate Python `reconcile_legacy_supervised` function with nonempty `reason`
and `evidence_ref`, or the CLI with both `--reconcile-legacy-reason` and
`--reconcile-legacy-evidence`. That exception config has only the original six
fields; it must not contain analysis_gate, and cannot use `--allow-create`.

The exception requires an existing transaction in an existing journal with the
exact original binding. It cannot initialize a journal, downgrade a gated one,
create a provider record, overwrite output, or retry an uncertain effect. An
existing exact output may reconcile INTENT to VERIFIED in the local journal.
Missing/conflicting source/output remains blocked. Losing the journal requires
operator reconciliation, never creating a substitute through this path.

Receipts record execution_mode=LEGACY_READONLY_RECONCILIATION, the reason and
evidence reference, and analysis_evidence_status=NOT_ASSESSED_LEGACY_RECONCILIATION.
A successful readback/exit code on this path establishes observation/recovery,
not completed analysis or structural-gate acceptance. Reasons record the trusted
host's authority basis; they do not grant provider permissions.

The ordinary API and CLI now fail closed without the gate, but arbitrary Chat
sessions and third-party callers are not automatically intercepted. Generic
pipeline/handoff primitives are lower-level components, not an approved bypass
for new qualifying transcript processing. The host still supplies authenticated
calls, honest domain assessment, fresh evidence and durable receipt readback.
