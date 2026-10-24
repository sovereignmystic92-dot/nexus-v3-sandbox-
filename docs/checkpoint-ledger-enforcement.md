# Checkpoint ledger enforcement

The host-side isolated runner now validates tools/recovery_ledger.json against the exact PR base or push first parent, fetched credential-free from this same repository. Candidate history must preserve every base record byte-for-byte under canonical JSON, append contiguous sequences/hash links, retain installation identity, match both provider packet hashes and point latest at the final manifest. Empty history is uninitialized, not acceptance.

The source event/base comes from the existing GitHub workflow environment. Existing candidate-parent provenance checks remain in force. This supplies a real Git-base comparison before the network-disabled container; unit tests separately cover coherent rollback and recomputed-history rejection.

Local suite: 191 tests passed (184 existing plus seven ledger cases). Hosted validation pending. A valid ledger does not perform or prove provider readback: live copy identities and payloads still require independent host retrieval. The actual protected current main must be fetched afresh for recovery.

Trust boundary: this relies on GitHub service/configuration and a trusted reviewed checker/runner. An administrator or a change that deliberately removes the checker is not excluded by content hashes. It is not an independent human review, restricted provider grant, cross-service atomic commit or physical-host-loss guarantee.

The initial ledger contains no records. No latest checkpoint or new audit pass is claimed. CP06 remains partial and the tracker remains 10/19 pending live paired persistence, current-reference recovery tests and full adjudication.
