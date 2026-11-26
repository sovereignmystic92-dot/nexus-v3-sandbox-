# Single-transcript private custody CLI

Candidate implementation for normal review; no live transaction or dispatcher
installation is claimed. This exposes the existing `execute_custodied_supervised`
API through the existing versioned private-storage protocol. A shared CSF/knowledge
connection plan is unnecessary for one ordinary transcript. The existing connected
CLI remains unchanged for multi-consumer work and its retained-receipt milestone.

Run `PYTHONPATH=src python -m nexus_sandbox.custodied_supervised_cli --config
/private/transcript.json --journal /private/transcript.sqlite` as one command.
The private config has exactly `supervised`, `custody_key` and
`custody_head_reference`. `supervised` has the original six host fields plus the
complete JSON `analysis_gate` from analysis-evidence-gate.md. The stable custody
key/head mapping must already be authoritative; changing a key does not release
an uncertain transaction. No endpoint, credential, plan, update or grant fields.

The trusted host services only archive_read, cortex_get, cortex_create,
store_create, store_read and store_replace, using the same strict JSON-lines
protocol, bounds and response deadline as the existing CLI. See
versioned-custody-dispatcher.md for exact storage responses and mandatory service
version-conditional replacement. Never send private IPC or journal snapshots to
public logs. Source reads must independently verify the pinned source revision,
complete original text and archive identity. Provider access, exact destination
and create grant remain host obligations, not facts inferred from flags.

Default execution is read-only with an existing journal/head. `--initialize`
explicitly selects new work and refuses existing custody. `--allow-create` is a
separate host-controlled flag. `--restore` restores a missing local journal and
reconciles read-only; it cannot enable create. Gates and exact source/output
bindings are checked before storage access. Existing native INTENT-before-create,
uncertain-effect hold, source/output readback and independently read retained
journal barriers are unchanged. No update/enrichment mode is exposed.

Exit 0 establishes only matched output and journal observations. Every result
explicitly says `transaction_complete=false`. Save the execution result to the
existing authorized durable checkpoint, independently read it back and reconcile
its native module/source/output identities before reporting transaction completion.
This CLI does not claim the connected consumer persistence milestone, factual
verification, independent review, remote fencing or unattended acceptance.

## Revision 23 bottleneck disposition

The runtime is present in the repository. A dedicated MCP tool is not required:
the authenticated Chat host can service private IPC with its available connectors.
However this invocation exposes no create_library_file, prepare_materialize or
replace_library_file ports (the documented private versioned storage mapping).
Scratch SQLite alone is not proof of journal custody across environment replacement.
No replacement store, new credentials or API runner is introduced. The remaining
live requirement is an existing authorized private versioned store with retained
objects, an authoritative key-to-head mapping and fresh versioned reads/conditional
writes, plus actual destination grants and source-bound gate evidence.

Tengri (`youtube:e-Hc1Bp-piE`, Notion original
4078c067daa48105b81dc86ebf8e9647) remains the first candidate. Reuse the existing
analysis and connection, reconcile all prior receipts before assigning new intent,
and do not count a synthetic CLI run as its processing. No Notion original changed.

No repository rule is relaxed by this candidate. In particular AGENTS rules 9–10,
analysis evidence, source fidelity, journal recovery and truthful completion remain.
Rollback removes this optional CLI, tests and document while preserving any real
journals, private storage objects and receipts.

## Pending ordinary-processing simplification

[Non-governing custody proposal](supervised-custody-simplification-proposal.md)
records the observed storage capability limits and a single-writer checkpoint
intent alternative for explicit review. It grants no exception to current rules
and does not enable a live source transaction.
