# Declared-review Notion handoff proposal

This draft connects the PR57 declared-review API to its existing
`ApprovedWriteBoundary`. It does not install a connector, change workflows,
activate dispatch, merge PR57, or intercept ordinary ChatGPT connector calls.

The host calls `declared_notion_write.execute` with one independently enrolled
canonical `notion:<page UUID>` destination, current context, independently held
review snapshots/digests and exact full JSON before/after snapshots. The two
reviews bind the existing intent hash (revision, operation, destination, baseline
hash and payload hash). The same context/reviews are reobserved after baseline
read and immediately before the mutation callback. Current authority and native
gates remain the host's responsibility; this API does not authenticate those.

The existing boundary persists DISPATCHING before the callback and requires
readback. Lost acknowledgments or failed readback remain UNCERTAIN. Reopening
the same journal can reconcile an observed exact target without another write;
an unapplied or different result is held, never blindly replayed. The journal
and provider callbacks remain single-worker, caller-provisioned capabilities.
Local SQLite is not evidence of cross-run or VM-loss custody. Direct provider
callers are not fenced and context checks are not provider-atomic enforcement.

The declared validator still defaults to GitHub-only behavior. Notion requires
an exact explicit host enrollment argument. The validator alone still reports
dispatch_authorized=false. Only this explicitly invoked handoff translates its
accepted declared evidence into the existing boundary's internal receipt.
That receipt is not authenticated reviewer evidence or a waiver of native gates.
ChatGPT/Gemini names in synthetic fixtures are declared labels, not live agents.

Validation: eight new integration regressions plus six existing declared-review
and nine existing write-boundary tests (23 total) passed locally. Cases cover
enrollment, exact intent, context/review changes during the baseline read,
successful readback/resume, lost acknowledgment, no blind replay and missing
owner/review evidence. These use synthetic callbacks, not the Notion connector.

Coherence review: REFINE existing gate/boundary rather than build a second
journal or transcript processor. Security-control classification: draft proposal
for review; no activation/merge authority inferred from routine maintenance.

Live handoff remains blocked until reviewed code is adopted through applicable
native gates and the host has a lossless, complete connector-backed snapshot /
write callback, fresh actual operation-bound review records, current authority
and independently verified durable intent custody. The archived Haiti transcript
must be reused, not recreated. Its prior connector success is manual evidence,
not a retroactive adapter pass. No full integration, CP05, CP09 or production
closure follows. No schedule, workflow, credentials, permissions or protections
are changed by this proposal.
