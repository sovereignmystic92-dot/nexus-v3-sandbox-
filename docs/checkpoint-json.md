# Checkpoint text adapter — sandbox draft

The adapter connects the adopted pipeline's typed Receipt tuples to a strict,
versioned JSON representation. It requires an independently supplied immutable
job binding and pre-enrolled checkpoint; missing state never initializes work.
Duplicate JSON keys, Boolean schema versions, unknown fields, wrong revision,
misordered receipts and invalid pending intent hold before continuation.

Injected read_text/write_text callbacks are transport contracts, not Notion
implementations. write acknowledgment is not readback: the pipeline performs a
separate read and exact comparison before effects. The four local tests exercise
serialization, malformed state, and a recreated adapter reconciling an uncertain
action without replay. This test uses an in-memory string store; it does not prove
separate-process or remote durability. The existing pipeline's fresh-process test
is separate evidence and does not automatically validate a new transport.

No provider write, credential lookup, mandatory router, workflow or remote store
is installed. Before live audit use: implement an explicit page/checkpoint
selector, require complete fetches, reject duplicate job/report markers, verify
exact destination and payload hashes, establish current executor authorization,
and test real fresh-process JSON custody. Preserve the single-worker restriction.
JSON shape validation authenticates neither the storage provider nor evidence
references. Whole-store rollback and malicious callbacks remain out of scope.

This draft is additive to PR61. The maintenance report route remains a proposal
until its actual transport and checkpoint enrollment are independently verified.
