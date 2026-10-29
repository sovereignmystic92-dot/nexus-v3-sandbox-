# Synthetic GitHub-to-Cortex execution runner

Implementation for PR #76; disabled by default, no service or production trigger
registered. This is executable event-consumer code with synthetic validation,
not evidence of a deployed integration or promotion of an audit gate.

The host supplies a `CortexHostTransport`, a pinned synthetic source `Module`,
a target prefix beginning `Nexus Sandbox `, and an `observe_run(run_id, attempt)`
callback backed by an authenticated GitHub read. Callbacks must enforce approved
account, owner, destination, network and credential scope. A webhook payload is
only a hint; it is compared with a fresh normalized authoritative observation.
This library neither authenticates webhook signatures nor obtains credentials.

Provision a private durable directory outside the checkout. Explicitly call
`ExecutionRunner.initialize(path, identity, source=source,
target_prefix='Nexus Sandbox Run ', transport=host, observe_run=observe,
fixture_execution=True)` once for approved synthetic fixtures only. On restart,
use `ExecutionRunner(path, identity, ...)` with identical bindings; never replace
a missing journal or initialize a new one as a retry strategy. Without the
explicit fixture flag, processing returns `DISABLED` and never calls Cortex.

Wire an approved host event callback to `runner.handle_event(run)`. Alternatively,
`runner.enqueue(run)` commits the bounded normalized event before returning;
`runner.recover(limit=100)` drains pending/held events after restart. No polling,
webhook listener, Actions workflow, or background service is installed here.
Invalid event envelopes/conflicting duplicate bindings raise before mutation.
The host must report enqueue failures; they must not be silently acknowledged.
Processing failures return `HOLD` without callback exception text. Database and
lock failures may raise and require operator attention rather than a success ack.

SQLite uses FULL synchronous commits and stores the immutable source/prefix
binding, normalized inbox, and the existing adapter receipts/events/identity
anchors in one journal. A private advisory lock covers each consumer operation.
Deterministic event-derived names and request keys make duplicate delivery
reconcile the same destination. A distinct workflow run attempt gets its own
record. The adapter commits write intent before host invocation, performs fresh
source and destination reads, pins verified identities, and forbids blind retry
after intent even when no remote effect is observed. Lost acknowledgments HOLD;
recovery reads rather than repeating the uncertain write. Verified redelivery
also performs fresh readback. Recovery does not periodically recheck completed
records absent a new event.

Trusted single-host/single-journal custody remains required. Advisory locks do
not fence remote writers or different journal copies. No remote CAS, cross-host
lease, authenticated history, power-loss durability proof, automatic repair,
retention policy or journal-loss recovery is claimed. The operator must preserve
trusted complete backups. A host read returning `None` must prove exact absence;
outages must raise. Complete candidate lookup/duplicate absence and provider
identity/ownership authorization remain host responsibilities. Synthetic markers
and a flag are scope restrictions, not provider-side authorization.

Validation: 13 offline runner tests include duplicate delivery, durable pending
restart, actual subprocess exit after a synthetic remote effect, lost ack,
uncertain no-effect reconciliation, mismatch, authoritative GitHub drift,
immutable binding conflicts, disabled operation, read failure/source drift,
missing journal/identity failure, lock exclusion, private permissions and removal
of arbitrary webhook fields. No real GitHub-to-Cortex writes were performed.

Full local validation at this implementation passed 427 distinct native tests
with no skips, plus 13 mocked Gemini tests. Compilation, workflow inventory and
diff whitespace checks passed. This is author-run synthetic evidence, not an
independent review or a hosted/live-run result.

Run from the checkout:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests/unit -p 'test_github_cortex_runner.py' -v
python3 -m py_compile src/nexus_sandbox/github_cortex_runner.py tests/unit/test_github_cortex_runner.py
python3 tools/validate.py --output /tmp/nexus-pr76-validation.json
python3 -B -m unittest discover -s integrations/gemini -p 'test_*.py' -v
```
