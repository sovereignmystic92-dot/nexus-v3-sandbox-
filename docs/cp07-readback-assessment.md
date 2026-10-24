# CP07 independent readback — proposed adjudication

Assessed source: `500d3ddf5330265dab4026df080cf6f7c9b9ad5d`.
Assessor: ChatGPT author assessment, not independent human review.
Definition: proposal-1, unchanged.

## Intended persistence inventory

| Surface | Required readback | Evidence |
| --- | --- | --- |
| SQLite coordinator artifacts, transaction state and receipts | Reopened committed storage, exact identities/destinations/payload hashes, mismatch holds | Existing main evidence and newly rerun 163-test suite |
| SQLite Cortex adapter journal and identity anchors | Reopen without losing first verified identity; inconsistent retained history holds | Current adapter tests, including retained/replaced identity regressions |
| Recovery backup/staging and restored SQLite state | Fresh process verifies restored installation identity; changed identity fails without repair | test_recovery_process_readback tests in the rerun suite |
| Host-mediated Cortex synthetic adapter | Source, archive, output and registry: exact ID, name/destination, content/hash, version and all three dependencies | Two fresh rounds of four live context_get calls against separately retrieved original C05/C11 immutable requests; cp07-fresh-readback.json |
| GitHub source and audit evidence | Ref-bound retrieval of current source and committed evidence | Connected GitHub reads at the frozen source SHA and review-branch exact readback |

Notion remains authoritative but its integration is paused and unaccepted; there is no Notion execution or claim here. Gemini is a separate opt-in API smoke test, not a Nexus persistence adapter. Its provider responses and GitHub logs do not establish Nexus state or qualify as external readback. GitHub CI source/log retention remains subject to CP08. No other active persistence adapter is installed by the inspected src/tools/workflows inventory. Future activation of another adapter reopens CP07 for that expanded scope.

## Live comparison

The source remains v2, archive v1, output v1 and registry v3, at the original exact IDs. All contents and three dependency edges matched original C05 stage bindings and the later C11 update request, retrieved independently from their scoped Cortex issues. Every field matched in both rounds. Registry Flash corroborated the four-module dependency closure. Public evidence uses identity fingerprints rather than account IDs. No fixture create, update, repair or delete was invoked.

The live reads are current observations, not replay of the old writer and not proof of indefinite durability. The reader is a connected host-mediated tool, separate from the original write response, not an independent human or physical trust domain.

## Mismatch safety

The new test `test_fresh_readback_rejects_each_exact_field_without_repair` changes identity, destination name, version, content and dependencies individually, plus a missing target. Each case uses a fresh adapter against retained durable identity, repeats the bad observation twice, rejects VERIFIED, proves zero added transport writes and unchanged remote-state snapshot. Restoring the original test data permits read-only verification again. These are offline response/state mutations; live Cortex fixtures were not corrupted.

Existing source-change, readback-outage, journal-integrity and fresh-process restored-identity tests also passed. The local suite passed 163 distinct tests. Hosted run 40137488255 passed 163 tests and four separate fault checks at head d56cc94df28309cf37317095af872bf8227fb866 (merge candidate fa9ccbc271e563136a5284cf6d7062bb28c88ae5). The separate Gemini offline check passed. This subsequent revision changes documentation/status only; runtime and tested matrix are unchanged.

## Proposed disposition

The evidence supports PASSED for CP07 across the declared current single-worker synthetic persistence inventory, with candidate CI passed and owner review pending. This proposes a ninth checkpoint; the accepted main score remains 8/19 until the evidence update is adopted. No denominator or pass requirement changed. CP02 effective grants, CP06 broader loss/rollback resistance, CP08 teardown/retention, CP09 fencing and CP10 independent human review remain open. No production readiness or activation is authorized.
