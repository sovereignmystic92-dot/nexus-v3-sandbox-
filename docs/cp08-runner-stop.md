# CP08 catchable runner interruption

SIGTERM and SIGINT now request a controlled stop of the isolated runner. The handler raises a bounded stop reason; the existing finally path attempts container removal, verifies staging deletion and publishes a BLOCKED report. Subsequent catchable stops are ignored during bounded cleanup and prior handlers are restored afterward. SIGKILL, host/power loss and retention deletion remain outside this guarantee.

Two tests send actual signals to an owned child running the real main/finally path. The tests use a fake Docker backend and ledger/preflight responses; they remove actual disposable staging and verify BLOCKED status, reported signal, simulated removal invocation and observed staging absence. They do not establish real container removal, GitHub cancellation behavior or host-shutdown cleanup.

Validation: final local suite passed 216 distinct tests. Initial test harness used two buffered output notifications, causing readiness timeouts; one explicit ready/path notification fixed synchronization and the complete suite passed. No sleep-based readiness assumption remains. Hosted checks are pending at publication. No workflow, retention-policy, provider-data or production changes. CP08 remains PARTIALLY_VERIFIED and score stays 11/19.
