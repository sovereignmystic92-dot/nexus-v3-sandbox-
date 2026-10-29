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

## Research execution contract — owner clarification, proposed

Follow-up research is part of the original mission, not a separate optional job
after a superficial workflow completion. The intended research executor continues
within scope until the current evidence frontier is exhausted, a real blocker is
reached, or a bounded execution limit requires a checkpoint.

This section specifies future behavior. The router above still only plans jobs;
it does not call search tools, reason over sources or implement this loop.

### Internal loop

1. Load the preserved source, existing Nexus findings and exact mission scope.
2. Maintain a frontier of unresolved claims, contradictions and useful connection
   candidates. Each item records its question, reason, priority and evidence needed.
3. Select the most consequential unexamined item whose investigation is authorized
   and feasible with available sources/tools.
4. Search or retrieve evidence, preserving source identity and passage context.
   Distinguish a search attempt from obtaining and assessing the actual source.
5. Compare with prior evidence, test alternative explanations and update confidence.
   Repeated pages or derivative retellings are not independent corroboration.
6. Evaluate Nexus connections by mechanism, supporting evidence and counterexamples;
   label analogies/hypotheses and reject connections with no explanatory value.
7. Save new evidence, revised findings, inspected connections and remaining frontier;
   independently verify persistence before advancing its checkpoint.
8. Continue with any newly justified question that remains inside the same mission.
   This controlled internal frontier is distinct from unrestricted output-event
   recursion, which the router continues to suppress.

### End and pause conditions

- FRONTIER_EXHAUSTED: every current in-scope avenue is resolved, duplicate,
  demonstrably unproductive after documented appropriate attempts, or has a
  specific reason it cannot presently be pursued. Record unresolved uncertainty.
- BLOCKED: an otherwise worthwhile avenue needs unavailable access, tools,
  evidence or authority. Save the missing dependency and resume condition.
- PAUSED_BUDGET: time, calls, cost or size limits were reached. Save the remaining
  frontier and next action; this is not research completion or saturation.
- AWAITING_REVIEW: the current findings are ready for required review before
  consequential routing, promotion or effects.
- CANCELLED / DEFERRED: preserve the last confirmed checkpoint and stop.

These are proposed research dispositions, not constitutional-state replacements.
Frontier exhaustion means no justified next step under the present scope and
capabilities, not that the subject is completely known or the internet exhausted.
Contradictions may remain unresolved. One weak search or repeated failure alone
does not establish exhaustion. Source unavailability must not be called a factual
resolution. New evidence can reopen a previously exhausted frontier.

### Checkpoint and completion evidence

Retain mission/source/policy/code bindings, current questions, attempted queries,
retrieved source IDs, claim-to-evidence links, novelty decisions, contradictions,
connection candidates, counterexamples, uncertainty, remaining budget, confirmed
writes, last verified checkpoint and exact next action. Protect sensitive data.

Research disposition, output preservation, required review and overall workflow
completion remain separate. An executor must not issue a completed research
receipt merely because it generated a summary or because the queue has no rows.
A budget pause must not silently abandon useful in-scope research.

### Acceptance tests required before implementation claims

Use scripted researcher/search/reader callbacks to prove: new useful evidence
causes another round; duplicate evidence does not inflate confidence; newly
supported questions join the same frontier; contradictions remain visible; useful
connections retain evidence/counterexamples; unavailable sources block explicitly;
budgets pause with pending questions; restored checkpoints avoid replaying confirmed
effects; only an evidenced exhausted frontier permits that research disposition.
Then separately validate real research-tool integration. Synthetic callback tests
cannot establish evidence quality, independent review or live autonomous research.

No new listener, schedule, live provider write or research worker is activated by
this contract. Existing handoff/activation deferrals remain in force.
