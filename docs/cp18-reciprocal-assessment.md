# CP18 reciprocal registration candidate

Definition proposal-1 unchanged. CP18 already declares a single-worker synthetic SQLite coordinator scope. No Cortex/Notion reciprocal writes or production acceptance are claimed.

## Implemented behavior

Registration stores one typed derived_from connection between the existing source archive and output, and two explicit endpoint references. A fresh committed-storage reader checks connection identity/binding, endpoint references, and endpoint identities/types/destinations. Missing or conflicting reciprocity holds completion. Receipts retain the observed connection/version and typed references.

Explicit repair_reciprocity requires an incomplete REGISTERED checkpoint, current transaction version, unchanged allowed authority, complete bound source, original connection binding and exact existing artifacts. Only missing references are inserted. The same connection advances its version; its transaction advances its version. The repair event and references commit atomically. Conflicting or absent connection records are not replaced.

A successful repair operation still has an incomplete protocol result until independent verification. Exact repair/repeat is a no-op. Verification never repairs.

## Local evidence

python tools/validate.py --output cp18-local-validation.json passed 174 distinct tests: existing 163 plus 11 reciprocal registration tests.

Cases: complete registration/repeat; either or both missing references; wrong endpoint type; missing/changed connection; stale version; changed source; journal-write failure rollback; and an actual fresh-process reader before and after repair. The child reader rejects missing reciprocity, then reads the same repaired connection at version 2 with both references; full database snapshots remain unchanged by readback. Repair preserves existing artifact identities. Failed event insertion rolls back references, both versions and event together.

Initial standard validation exposed a test-child import-path issue. The child now receives an explicit source path. Corrected standard validation passed; no runtime check was weakened.

Hosted candidate run [40138044308](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40138044308) passed 174 distinct tests and four separately counted bounded faults. Gemini offline check also passed. The merge candidate 2491064de27909c4aa68867aea23675037e918f1 has exactly the observed main and reviewed head parents. Full report: cp18-hosted-validation.json.

## Proposed adjudication

CP18 PASSED within its unchanged adopted local SQLite scope. All conjunctive requirements are covered: missing reciprocity prevents completion; explicit repair updates the existing connection and ensures both references; a fresh process rejects missing state and verifies repaired state; repeat and fault rollback preserve the full durable snapshot. This proposes 10/19 on PR #26; owner adoption/merge remains pending.

## Compatibility and applicability

New disposable schema only. Old databases without reciprocal tables are refused without migration; retain old journals/backups and assess them with their matching historical runtime. No existing external fixture is changed.

The 163 existing tests rerun successfully on this schema. CP07 coordinator applicability is covered by new fresh-process typed-reference checks and the full suite. Cortex adapter/bridge code and fixtures are unchanged. Cross-service consistency, concurrent writers, physical loss, independent human review and production activation remain unaccepted.

Accepted main score remains 9/19 pending complete evidence and adoption. Historical external-endpoint blocker wording is retained, while assessment follows CP18's previously adopted local SQLite scope.
