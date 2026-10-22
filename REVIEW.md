# Foundation sandbox review

This branch contains the Python/SQLite architecture, component interfaces, evidence requirements and acceptance cases from AUD-40. The local coordinator is now implemented; fixtures remain synthetic only.

The README replaces the initial placeholder. Sandbox exclusions are appended to the existing Python .gitignore. No workflow YAML is added. Main remains unchanged until a separate merge.

Source basis: the current owner conversation and the Notion Foundation Audit retrieved 2026-10-22. The owner selected the existing public sandbox repository and authorized continuing with publication of the review draft. Runtime isolation, execution and production integration are not validated or activated.

The local suite now applies the schema and passes 14 unit/integration tests, including transaction rollback and corruption injection. Full acceptance, concurrency, host isolation, authority resolution and deployment remain unverified. See docs/implementation-validation.md. This supersedes the earlier draft-stage no-execution statement; it does not retroactively change that historical result.

Follow-through: structured synthetic authority resolution and attempt evidence are now implemented; 24 distinct local tests passed. Full acceptance is BLOCKED because host isolation is unverified. Current coverage and reproducible evidence are in docs/authority-and-acceptance.md and docs/validation-results.json. The earlier 14-test result remains historical. No merge or deployment is authorized by test success.

Runner follow-through: the owner authorized an isolated hosted-runner setup. The workflow is scoped to source/test/tool pushes on foundation-audit-draft, with no repository token passed into the container and no merge/deployment. Twenty-eight distinct local tests pass, including container-boundary rejection tests. Hosted execution remains to be observed; see docs/isolated-runner.md. This supersedes the earlier no-workflow design for this expressly authorized scope.

Observed hosted follow-through: run 39853191498 completed successfully at commit 68c51fa22d36ff5fed7a46c09b731dbd5d35972b; 28 tests passed, host/container preflight passed, source manifests matched, and ordinary cleanup was confirmed. Evidence is preserved in docs/hosted-run-39853191498.json. This supersedes the earlier hosted-execution-pending statement for that commit only; full acceptance remains separately BLOCKED.

Focused review follow-through: mutable image acquisition is now digest-pinned and nonzero container execution preserves structured diagnostics. Three owned-child SIGKILL checks passed locally. A dedicated-volume ENOSPC test and runtime log-retention guard are ready for hosted execution. See docs/review-and-fault-checks.md; no independent human review is claimed.
