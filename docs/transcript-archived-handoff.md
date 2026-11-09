# Verified archive to derived-output handoff

`transcript_archived_handoff.run_archived_handoff` connects the indexed archive
reader to the existing bounded Cortex handoff. The caller supplies the original
prepared receipt/chunks, independently pinned source SHA-256 and canonical Notion
page UUID. Pass `NotionArchivePort.read_archive` as `read_archive`; supply the
separately authenticated Cortex read/write ports and explicit write grant.

This is an opt-in executable composition, not an installed runner or automatic
chat trigger. Existing entry points are unchanged. No new API, token, provider
grant, workflow, schedule or credential route is introduced.

The composition requires a complete, ordered, destination-bound exact archive
before any Cortex lookup. It cannot write Notion or repair missing source
chunks. It rechecks the archive immediately before a permitted Cortex write,
then checks again after the derived output has been independently read back.
The existing handoff embeds the canonical source page and SHA-256 in the output,
reuses an exact existing output and refuses to overwrite a conflicting output.
An identical invocation with `allow_cortex_write=False` can verify an existing
output without writing either store.

Only `READBACK_MATCHED` is returned on successful source/output comparison. This
retains `RECORD_DURABLE_EXECUTION_RECEIPT` as the next action; it does not mark
the full transaction complete, authorize an event, record a durable receipt,
attest a runner identity or promote an audit gate. The host must establish
current effective destination grants; a Boolean flag does not prove them.

A failed source read before handoff raises without reaching Cortex. If the
pre-write source recheck fails, the existing handoff conservatively reports
`CORTEX_WRITE_OUTCOME_UNCERTAIN_RECONCILE` even if that check prevented the write.
A changed/unavailable source after a saved output returns BLOCKED with
`RECONCILE_ARCHIVE_AFTER_CORTEX_READBACK`. Preserve and reconcile the saved
output; do not erase it or blindly retry. Any uncertain Cortex write also stops.
There is no retry loop, settled-absence proof or durable Cortex intent journal.

Repeated source observations are not an atomic snapshot across providers.
Concurrent or uncooperative writers, visibility delays and mutation after final
readback still require ownership/fencing outside this function. Analysis is
host-supplied; semantic correctness, independent AI review and policy acceptance
are not certified by byte comparison. Runner Cortex identity/grants and live
transport verification remain required before enabling a GitHub write path.

Validation: eight new offline integration tests use the real NotionArchivePort
with a synthetic SDK-shaped reader and synthetic Cortex storage. They cover
Unicode/whitespace fidelity, read-only replay, missing/mutated/misbound source,
grant rejection, source mutation before and after output write, uncertain output
write and conflict refusal. All eight and the existing 48 transcript tests
passed locally. Hosted CI is required. No live provider calls were made.

```sh
PYTHONPATH=src python -m unittest discover -s tests/unit -p test_transcript_archived_handoff.py -v
PYTHONPATH=src python -m unittest discover -s tests -p test_transcript_fidelity.py -v
```

Rollback: remove the composition, its test file and this document. No existing
runtime call site or provider record requires migration.
