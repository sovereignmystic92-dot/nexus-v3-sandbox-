# Archive resume planner

`plan_archive_resume` in `transcript_ingestion_gate.py` is an offline, provider-neutral decision function. It does not execute writes, persist a recovery journal, authenticate responses, or schedule a host. The existing SQLite coordinator is unchanged; a real YouTube ID is not invented for supplied-message sources.

The trusted single-worker host must pin the source digest and exact provider destination independently of observations. Supply prepared exact chunks and a fresh, fully paginated observation containing `destination`, `source_sha256`, `complete: true`, and ordered `{index, text}` records. The completeness flag is a host assertion, not independent proof supplied by this library.

- Unknown outcome / no observation: `READBACK_REQUIRED`, empty write plan.
- Complete observation with missing chunks: `MISSING_CHUNKS`, only absent indexed payloads returned.
- Complete exact archive: `ARCHIVE_VERIFIED`, empty plan.
- Wrong binding, incomplete pagination, malformed source, conflicting text, duplicate or unordered indices: ValueError, no plan.

The host must preserve logical index order when inserting missing chunks; sparse gaps cannot be repaired by blindly appending. After each uncertain write, discard any old plan and independently read again before replanning. Before executing any plan the host must retain its separately established authorization and exclusive ownership; this planner supplies no lease, CAS or stale-snapshot protection. It cannot protect a concurrent writer between observation and execution. Never use a plan itself as write authority.

Every returned decision keeps provider/Cortex write authority and audit promotion false. Require a new complete exact readback after planned writes before advancing the stage journal. A checksum authenticates neither the provider nor the claim content.

Validation: `PYTHONPATH=src python -m unittest discover -s tests -p test_transcript_fidelity.py -v` — 31 local offline tests passed, including eight planner cases. Lost-reply tests model supplied observations; no real process crash, provider timeout, OAuth, live write, concurrent-worker or unattended recovery is claimed. Existing dedicated CI covers these same files; workflows, inventory fingerprints and credentials are unchanged.
