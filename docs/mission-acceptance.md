# Mission scenarios and foundation-audit coverage

Scope: one synthetic transaction is treated as one mission. The coordinator preserves a fixture payload through archive, output and registry artifacts in one SQLite database. It does not research, synthesize knowledge, create a distinct durable mission record, or register anything in Notion/Cortex. A complete local trace demonstrates only this declared scope.

| Case | Expected observation | Foundation-audit requirement |
| --- | --- | --- |
| M01 complete and repeat | Six exact states, three exact artifact identities/destinations/payload hashes, linked attempt/event evidence, fresh-reader receipt, unchanged snapshot on retry after reopen | AUD-02 persistence; AUD-06 completion; AUD-07 idempotency |
| M02 interrupted and resumed | Stop after committed output, reopen storage, preserve checkpoint and prior artifacts, finish with exactly six events/attempts and three artifacts | Failure/recovery acceptance: checkpoint resume without duplicate output |
| M03 incomplete evidence | NEW/BLOCKED, no artifacts, explicit next action, NOT_ATTEMPTED/BLOCKED envelope, unchanged repeated hold | Provenance and completion gates; no success without complete source |
| M04 conflicting current authority | NEW/BLOCKED, no artifacts or verification receipt, retained blocking attempt and unchanged repeated hold | AUD-09 source precedence; unresolved authority fails closed |

These four tests are included in the total unit/integration count, not an additional count. `tools/validate.py` requires all four named cases to be present and successful and records each observed status. A missing or skipped case cannot yield a mission pass.

M02 is a controlled checkpoint interruption and coordinator recreation. Actual process termination is covered separately by the existing three SIGKILL cases. Neither proves power-loss behavior. Registration means a local registry artifact; external reciprocal endpoints remain outside scope. A fresh SQLite connection is an independent storage observation, not an independent human review.

The existing hosted workflow is extended only to the exact `mission-scenarios` branch, retaining its standard runner, time limit, empty token permissions, public credential-free source fetch, digest-pinned image, restricted container and bounded fault volume. No schedule or production integration is added.

Validation status: observed hosted pass, as recorded below. No merge or deployment is included in this change.


## Observed acceptance evidence

[Hosted run 39857370613](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39857370613) completed successfully for source commit `e8df5490c4d5edb7893c681cf0f9d383bcf3ee12`. Completed job logs were retrieved and the structured report parsed. All 32 distinct tests passed, including M01–M04 (four cases within the total). The three SIGKILL recovery checks and bounded tmpfs ENOSPC/SQLITE_FULL check also passed, counted separately. Source manifests matched; all host/container preflight checks passed; container and staging removal were confirmed. GitHub reported 90-day log retention, within policy; future deletion remains unproven.

The exact observed report is preserved in `hosted-run-39857370613.json`. Scoped verdict: **PASS for the four single-worker synthetic transaction missions at the tested revision**. Full acceptance remains BLOCKED. This author assessment is not independent human review. No actual Notion/Cortex persistence, semantic knowledge processing, external reciprocal endpoints, power/device loss, host-kill cleanup or multiworker fencing has been established. The follow-up evidence-only commit does not alter runtime source. Owner review and separate merge approval remain pending.
