# Evidence contract

Each real run must record: schema_version, run_id, case_id, attempt_id, fixture_revision, code_revision, runtime_identity, started_at_utc, ended_at_utc, expected_result, observed_result, operation_outcome, protocol_verdict, last_confirmed_state, next_action, artifact_ids, expected_hashes, readback_hashes, reader_identity, evidence_refs, limitations.

Operation outcome: SUCCEEDED / FAILED / NOT_ATTEMPTED / UNKNOWN.

Protocol verdict: VERIFIED / PARTIALLY_VERIFIED / FAILED / NOT_TESTED / BLOCKED. A successful operation may still have an unverified protocol verdict.

Store events with a monotonically increasing sequence, transaction ID, prior/new state, UTC time and evidence reference. Commit events and checkpoint changes together. Never overwrite prior attempts to hide a failure. Local append-only policy is not cryptographic tamper resistance.

An independent persistence check uses a fresh reader/connection, not the write response or an in-memory copy. This is separate observation, not an independent human audit. Record exactly which aspect was checked and the observation time; immediate readback does not establish long-term durability.

No fabricated run records are included. Proposed scenarios remain NOT_TESTED until attributable execution evidence exists.
