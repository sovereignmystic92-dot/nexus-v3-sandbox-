# Manual Notion archive adapter live probe

This manual-only probe uses synthetic text, not original transcripts. It proposes one additional reviewed secret route: existing NOTION_SANDBOX_TOKEN in existing notion-sandbox environment, only in the live step of notion-archive-live-probe.yml. Existing routes are unchanged. No credential, provider grant or environment setting is created by this PR. Review/merge this exact route before execution.

## Execution prerequisites

Provision a new empty page for this probe and explicitly share it with the sandbox integration that owns the token. The connected ChatGPT Notion identity may differ; its ability to create a page is not proof of runner access. Supply the page's canonical hyphenated UUID as fixture_page_id and confirm the bounded test on workflow_dispatch. Do not select the Foundation Audit, Mass Relays archive or any existing mixed-format archive. The port rejects non-probe/foreign blocks. Page creation and integration sharing remain owner/setup work; no fixture identity or effective-grant success is invented.

Run only from main after this PR is merged and all offline checks pass. The workflow has no schedule or push/PR live trigger, empty GitHub token permissions, fixed repository/ref checks, protected notion-sandbox environment and non-cancelling concurrency. Public code is staged at github.sha before the token is supplied to the test step. No SDK installation is needed; a pinned-origin REST shim implements the merged adapter's client shape, rejects redirects, has bounded responses/timeouts and does not automatically retry writes. API version 2025-09-03 and position support require live compatibility verification; unsupported responses fail closed.

## Bound and evidence

At most three requests append one code block each on run attempt 1. Every child process reopens the same local SQLite journal, each client has a one-write budget, and final observation is read-only. Workflow reruns are strictly observe-only. A failure is not evidence of no side effect; never run a fresh write-enabled dispatch against an uncertain fixture until pending writes are reconciled. No settled-non-commit override is supplied.

Success requires ARCHIVE_VERIFIED after exact source/chunk comparison and a final read-only process reporting zero writes. Logs emit fixed summaries/digests/destination only; never tokens, raw provider bodies or private transcripts. A failure prints BLOCKED and OBSERVE_ONLY_NO_BLIND_RETRY. Retain the synthetic page and Actions evidence for review. Staged code and ephemeral local journal are removed; the run is not proof of durable recovery across Actions hosts or workflows. Same-run process reopening is not fault injection or independent AI review.

No CP05/CP09 promotion, runner-wide identity certification or unattended readiness follows from this probe. A successful bounded authenticated write/readback establishes only the operation observed on its selected fixture. The journal remains local to this job; no external durable volume is configured.

## Validation

Six offline probe guard tests and 48 existing transcript tests passed locally. Workflow inventory and credential routing matched after adding the exact workflow fingerprint and explicit route. Hosted CI must independently pass. No live execution occurred while preparing this PR.

Manual dispatch is not exposed by the current GitHub connector; after merge an owner can run the workflow from GitHub Actions. Do not substitute rerunning a different checkpoint workflow or forwarding ChatGPT connector credentials.


## Optional controlled lost-reply mode

After this change is reviewed and merged, use a NEW empty fixture shared with
the sandbox integration and enable discard_first_reply in the same manual
workflow. Leave it false for the original healthy-transfer probe. The existing
successful fixture is retained; do not delete its evidence or use it to claim a
new write/fault.

On attempt 1, the first child makes one bound append request, receives a success
response, emits a fixed ACK_DISCARDED_AFTER_SUCCESS marker, then SIGKILLs itself
before the archive host can observe/verify the write. Durable intent already
exists. The parent accepts only that exact marker plus actual SIGKILL exit
status, and starts the next bounded child using the same journal. Fresh
readback must find the committed chunk and omit it from new write plans. The
remaining two chunks may then be written. Final observation is read-only and
must verify all exact chunks; the maximum remains three requests.

Missing marker, unexpected exit, absent commit, denied access or any other
failure stops execution without blind retry. No settled-absence override is
provided. A fixture already containing the first chunk does not inject a fake
success: the child rejects zero-new-write fault injection. All workflow reruns
are observe-only and disable injection regardless of the original flag.

This tests real process termination against a live provider AFTER its successful
response, not packet loss, mid-request timeout, provider rollback or power loss.
The local journal is still ephemeral to one Actions job. It cannot establish
cross-host durable recovery or unattended readiness. A failed probe needs
observation/reconciliation before any new write-enabled dispatch.

Offline validation for this revision: 10 probe guard/driver tests passed,
including expected-kill control flow, unexpected-failure stop, new-write-only
injection and observe-only rerun behavior. SIGKILL is mocked in the new callback
unit test to avoid terminating the test runner; actual process-kill coverage
remains in the existing transcript host suite. Workflow inventory/routing
verification passed. Live fault-mode execution remains pending.
