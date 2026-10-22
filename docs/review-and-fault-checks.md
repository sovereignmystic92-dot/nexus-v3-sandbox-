# Focused review, real fault checks and retention — 2026-10-22

## Review findings and changes

The focused inspection covered submit/resume binding checks, authority holds, artifact recovery, checkpoint/event/attempt atomicity, separate-reader verification, container boundaries and cleanup. No additional blocking coordinator defect was identified in that bounded inspection. This is author review, not independent human review or a security certification.

Two runner issues were addressed. The Python image used a mutable tag; it is now pinned to the registry digest observed in successful run 39853191498 (`python@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2`). Container output is now parsed even if Docker attachment returns a nonzero status, preserving structured failed-test evidence before reporting a blocked run. Image changes will require an explicit revision and a new run.

## Real process termination

The harness starts and signals only its own synthetic child. It waits for an explicit boundary marker, sends SIGKILL, observes the signal exit status, reopens the SQLite database, checks exact durable records and integrity, and resumes to VERIFIED. The three boundaries are:

1. After the archive checkpoint commits.
2. After output/artifact and checkpoint writes inside an open transaction, before its event/attempt and commit. The entire uncommitted snapshot must disappear on recovery.
3. After output creation commits, before registration.

All three passed in a local smoke run. The hosted container must repeat them; local process termination is not a power-loss test. Each final database must have exactly three artifacts, six checkpoint events and six attempts, with the original archive identity.

## Real filesystem exhaustion

`/fault-storage` is an explicit second container tmpfs limited to 4 MiB. Host/container checks gate execution first. The fault harness refuses to fill a path unless `/proc/mounts` identifies that exact path as tmpfs, it is separate from /tmp, and its reported capacity is at most 8 MiB. It never fills a general host filesystem.

The harness initializes a synthetic transaction to VALIDATED, captures its durable snapshot, fills only that dedicated volume until the OS raises ENOSPC and available blocks reach zero, then attempts the archive write. It requires SQLite's SQLITE_FULL, removes the filler, compares the complete durable snapshot, checks integrity, and resumes without duplicate artifacts. This covers a full filesystem before archive creation, not power loss, device loss, all possible commit-time failures or cross-service partial writes.

This check is not run on the authoring host because the dedicated mount is unavailable there. Its result must come from a hosted run, not from code existence or the local unit count.

## Evidence retention policy

- Runtime databases, filler files and staging: disposable; remove after each check and confirm ordinary container/staging teardown. Forced host cancellation remains dependent on hosted VM teardown.
- Workflow logs and synthetic runtime reports: accept only a GitHub-provided `GITHUB_RETENTION_DAYS` value from 1 through 90 inclusive. Record the observed value and block execution if absent or outside policy. No repository setting is silently changed; this is runtime evidence of the configured setting, not proof of future deletion or an independent administrative audit.
- Selected synthetic review reports committed to Git: intentionally retained with repository review history; no automatic expiration is promised. They contain fixture-only metadata and hashes. Removing a working-tree file would not erase Git history or public copies.
- No production data, raw database files, secrets or artifact upload are permitted in this harness.

GitHub documents `GITHUB_RETENTION_DAYS` as the workflow log/artifact lifetime and repository retention settings separately: [variables reference](https://docs.github.com/en/actions/reference/workflows-and-actions/variables), [repository settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).

## Verdict boundary

Local validation: 28 distinct unit/integration tests pass. Hosted run 39854172895 subsequently passed the same 28 tests, the four real fault cases and the retention guard, as recorded below. These results apply to source commit f67f643cfb7f752586c14ae50cf4882ed2a775dc. Full acceptance remains separately BLOCKED; independent review, power-loss/device tests, external reciprocal endpoints and multiworker fencing are not implied by these changes. Main and production remain outside this draft branch.

## Observed hosted result and merge decision

[Run 39854172895](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39854172895), source commit f67f643cfb7f752586c14ae50cf4882ed2a775dc, completed successfully. Its completed job logs were retrieved and parsed. All 28 distinct unit/integration tests and all four separately counted real fault cases passed. The 4,194,304-byte fault tmpfs reached ENOSPC after 4,141,056 filler bytes; SQLite returned code 13 SQLITE_FULL. The complete pre-failure durable snapshot was preserved, integrity_check returned ok, and recovery reached VERIFIED after freeing space. Each SIGKILL case recovered without duplicate artifacts/events/attempts. Host/container preflight, exact source-manifest match, container removal and staging removal all passed. The digest-pinned image pulled and executed successfully.

GitHub reported GITHUB_RETENTION_DAYS=90, within the explicit 1–90 day policy. This is observed runtime configuration, not elapsed-time deletion proof. The exact observed report is preserved in hosted-run-39854172895.json; its source hashes were checked against the current authoring copy.

The scoped single-worker synthetic baseline is ready for owner review and a merge decision. Author review and these tests support that limited milestone; they do not constitute an independent human audit. Broad full acceptance remains BLOCKED because power/device loss, forced host-kill teardown, external reciprocal endpoints and multiworker lease/fencing are not demonstrated or implemented. Those broader claims must remain excluded from any merge approval. Main remains unchanged until an explicit merge authorization.
