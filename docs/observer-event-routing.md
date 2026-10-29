# Observer-only event routing groundwork

This opt-in library persists job proposals. It does not install a listener,
schedule, provider transport or execution worker, and never calls selected actions.
Existing maintenance and deferred live handoff/diagnostic work remain unchanged.

| Accepted event | Proposed job | Stop / review boundary |
| --- | --- | --- |
| SOURCE_READY / SOURCE_REVISION_CHANGED | INSPECT_TRANSCRIPT | Plan only; review enrollment before execution |
| CHECK_FAILED | DIAGNOSE_CHECK | Inspect existing evidence; no write replay |
| JOB_INTERRUPTED | INSPECT_CHECKPOINT | Observe confirmed state; no automatic resume |
| Output-origin or unknown event | None | Ignore to suppress feedback loops |

`ObserverQueue` requires explicit initialization of a new trusted local SQLite
path. Reopening missing/partial storage holds instead of recreating history.
Each accepted job binds source revision, policy/code revision, authorization
reference and mission type. The stable digest deduplicates multiple arrival events
for the same work; reuse of a recorded event ID with a different binding holds.
Changed revisions create separate plans without erasing prior evidence. No source
text, provider secret or response body belongs in an event: IDs only.

One immediate SQLite transaction stores the job and first event identity together.
Duplicate aliases do not grow the event log; their IDs are not globally reserved.
The queue-wide job cap counts all retained plans, across sources/enrollments. It
does not promise per-mission quotas, execution time/tool-call/cost enforcement,
automatic garbage collection or proof of future deletion. A job is only PLANNED,
never COMPLETE. Current enrollment pause and scope are checked on every call.

## Trust and implementation boundaries

Enrollment, event origin and authorization references are caller inputs, not
authenticated grants. A future reviewed host must authenticate events, establish
canonical destinations, enforce permissions/budgets and check policy at execution
time. A changed authorization reference is not inherently a renewed grant.
This queue is not tamper-evident, encrypted, remote-CAS protected or resilient to
database/host loss. It must be used by one cooperating worker; no provider fencing
or CP09 claim follows from SQLite serialization. Trusted-path checks are not a
hostile-filesystem security boundary.

Reuse the existing processing pipeline, checkpoint journal and reviewed transport
contracts when adding an executor. Do not run a proposal merely because a queue
row exists. Later steps: observation-only authenticated event intake, exact-source
snapshot parser, durable custody, execution budgets, reviewed completion boundary,
and an explicitly authorized bounded pilot. Live handoff stays deferred.

## Validation

Run `PYTHONPATH=src python3 -m unittest discover -s tests/unit -p test_event_router.py -v`.
Synthetic cases cover routes, duplicate/reopen behavior, source/policy/code changes,
event-ID conflict, output feedback, pause/scope/budget holds, malformed input and
missing/partial storage. The existing validation runner discovers these tests.
No tests request a model, provider API, credential or network access.
