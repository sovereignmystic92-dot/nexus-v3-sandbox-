# Failure collector — first test-and-refine component

This is an offline deterministic collector, not an autonomous repair agent or GitHub retriever. It consumes a normalized packet containing repository/current SHA and revision-bound run attempts with explicit case outcomes and precomputed failure-signature hashes. It emits a machine-readable handoff; it never executes logs, calls providers, writes fixes, creates issues or changes audit gates.

Run: `python3 tools/failure_handoff.py packet.json`. Invalid input produces only a fixed INVALID_EVIDENCE result and exit 2. Valid classifications return exit 0 even when tests failed; this is collector success, not a passing-test verdict.

Only completed failure runs on the explicitly supplied current SHA with named FAILED/ERROR cases produce findings. Healthy, cancelled, pending, timed-out, unavailable/empty, skipped, inconsistent and stale evidence do not produce a repair handoff. Classification depends on supplied evidence, not authenticated retrieval. A future retrieval adapter must establish run/repository/SHA authenticity and log completeness; missing parsed cases must not be synthesized.

Deduplication is deterministic within the supplied batch: repository, source revision, test ID, failure kind and signature hash identify a finding. Repeated reports do not duplicate it; distinct runs retain separate observations. For the same run, the latest observed attempt controls proposed work while prior failed-case counts remain visible. Successful reruns remove old findings from the current handoff. This is not persistent cross-day deduplication or a complete external issue inventory.

Schema: top-level repository/current_sha/reports. Reports require repository, positive integer run_id/attempt, source_sha, status, conclusion and cases. Cases require test_id, status and failure_signature (64 lowercase hex for FAILED/ERROR, null otherwise). Raw logs and additional fields are rejected; normalized signatures must be computed by a future bounded log adapter. URLs are not inferred or invented. Full examples can be built from tests/unit/test_failure_handoff.py.

Validation: 226 distinct local tests passed, including ten new regression methods for duplicate observations, success after failure, stale/cancelled/pending/timeout results, inconsistent success, skipped/missing evidence, conflicting attempts, cross-repository records, malformed signatures and command-shaped input. No live failing run was retrieved or diagnosed in this checkpoint. Hosted checks pending at initial publication.

Next: connect read-only actual CI retrieval and bounded failure extraction, retain observation provenance, then add persistent deduplication and an assessed code-agent draft executor. Existing CI already runs tests automatically; this PR adds the classifier component and its regressions, not the entire repair loop. Score remains 11/19, production paused, no billing or new permissions.
