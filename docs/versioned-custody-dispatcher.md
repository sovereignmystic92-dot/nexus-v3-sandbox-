# Versioned private-store custody dispatcher

Status: offline implementation for independent review. No storage SDK, credentials,
network endpoint, account grant, background worker or live Cortex create is
installed. This supplies an executable private command path around the merged
custody API; it does not certify the external host that services its requests.

## Pinned head and retained objects

`VersionedCustodyDispatcher(key, head_reference, request)` implements the four
`JournalCustody` ports using three versioned file operations. The authoritative
key-to-head identity is explicitly pinned before execution. There is no search,
"latest file" selection, missing-head auto-create, or replacement of a lost
mapping. An authorized new head file must already contain exactly:

```json
{"schema":"nexus.versioned-custody-head.v1","key":"synthetic-work-key","head":null}
```

For the connected CLI, key is the selected consumer's exact work_key from the
validated connection plan. This consumer mapping does not authorize new work
when earlier intent is uncertain. Reconcile existing receipts/journals first.
The mapping must survive host loss outside scratch. Never infer confirmed
absence or an authorized new transaction from an inaccessible file.

| Private operation | Request | Exact success response |
| --- | --- | --- |
| store_create | content_b64 | reference |
| store_read | reference | reference, nonnegative integer version, content_b64 |
| store_replace | reference, expected_current_version, content_b64 | status=UPDATED, reference, integer version=expected+1 |

The only non-success value accepted from store_replace is exactly
`{"status":"CONFLICT"}`, mapped by the host solely from a genuine service
version conflict. Denied access, timeouts, missing records, uncertain replies and
other errors must fail the IPC request, never become null, absence or conflict.
There is no automatic retry. A pointer mismatch returns False without a write.

Retained objects have create/read paths only. Head replacement is restricted to
the pinned head reference, and a head file cannot masquerade as a retained
journal. Underlying write permissions/immutability remain host obligations;
the custody envelope hash detects content changes, but this adapter cannot
prevent a privileged user deleting or rolling back the external store.

CAS freshly reads and validates the pinned document and its current service
version, compares its complete head with the expected head, and requests a
version-conditional service replacement. A competing service update must reject
the stale version atomically. `JournalCustody` then separately fetches and
verifies the actual saved head and retained object. Python's read-before-write
comparison alone is not the CAS. The service's conditional write is mandatory.

## Host mapping to available private file tools

The trusted Chat host can map create to create_library_file; fetch exact bytes
and a current version using prepare_materialize; and map replacement to
replace_library_file with the exact pinned library_file_id and
expected_current_version. Apply returned file identity metadata using the
current file-transfer contract. Do not omit the version check, derive a version
from a filename or use a stale local copy as readback. Native file version and
custody generation are different fields and must not be substituted.

For reads, the host must verify the returned stable file identity, complete exact
bytes and authoritative current_version_number in one fresh file observation.
Read failures or ambiguous versions block. Snapshot objects must remain private,
because native journal bindings can include full source chunks. Never publish
snapshots or IPC payloads to this public repo or CI logs. Only synthetic
fixtures are included here; no private tool-file identities are embedded.

An earlier authenticated synthetic file probe established a valid versioned
update, sequential stale-version rejection and independent unchanged readback.
It did not establish concurrent contention, immutable object retention, this
dispatcher's authenticated end-to-end operation or full host-loss durability.
Those claims remain separate acceptance work. The provider's protected version
service and key-to-head mapping are trusted prerequisites, not implemented here.

## Private connected CLI

Run `PYTHONPATH=src python -m nexus_sandbox.custodied_connected_cli --config
/private/connected.json --journal /private/consumer.sqlite` as one command.
Config has exactly plan, consumer, supervised, custody_head_reference.
supervised has the original six supervised fields plus complete analysis_gate;
the JSON domain list is converted to the native tuple. Credentials/endpoints
and create grants are not config fields. The plan, source/output gate and
mission binding are checked before storage requests.

Default is existing-journal, read-only reconciliation. `--initialize` explicitly
requests a new transaction and refuses an existing local/remote transaction.
`--allow-create` is a separate host-side grant flag, not authorization supplied
by this module. `--restore` restores from the pinned head to a missing path,
then reconciles read-only; it cannot be combined with --initialize or
--allow-create. No legacy ungated route is added.

The same private request/response envelope, monotonically increasing IDs,
1 MiB message/config bound and 45-second complete-response deadline as the
existing supervised CLI are used. Operation names additionally include
source_reference and retained_receipt, plus the three storage operations.
retained_receipt replies are null for confirmed exact absence or exactly
reference/content_b64, freshly fetched by work_key. The standard connected
wrapper still verifies that separate retained execution receipt and native
provider output; a custody head is not its replacement.

Storage content and retained receipts are limited to 512 KiB in this adapter,
below the native journal limit, so base64 IPC fits within 1 MiB. Oversize input
fails before its create/replace request. Result exit 0 requires the actual
connected persistence milestone. PENDING_RECEIPT or BLOCKED exits 2 with a
non-success result or a sanitized blocked record. Preserve all intents and
reconcile after any interruption; never blind-retry uncertain storage or
provider effects.

## Validation and remaining gates

Run `PYTHONPATH=src python -m unittest discover -s tests/unit -p
'test_versioned_custody_dispatcher.py' -v` as one command. Synthetic storage and
real subprocess tests cover version conflicts, uncertain replacement, identity
drift, strict parsing, missing gate, response ID mismatch, private retained
receipt re-entry and explicit restore with one provider create total. The lost
replacement-reply case records a synthetic storage effect but cannot reach
the provider create.

No real source journal or Cortex destination has been used with this code.
Independent review of this exact implementation, authenticated immutable
retain/read acceptance, protected mapping custody, actual Cortex execution
principal/account/parent/grants, refreshed source evidence and complete
operation-specific approval remain required. The source-attributed analytical
review and a version-guard probe do not waive these requirements. Single
cooperating worker only; pointer CAS still does not fence a stale worker at a
provider's mutation boundary. No CP09 closure, live activation or deployment.

Rollback removes the two opt-in modules, tests and this contract. Preserve
actual private objects, head mappings, journals, receipts and uncertain intents.
Existing host entrypoints, schemas and workflows are unchanged.
