# Foundation sandbox review

This branch contains the Python/SQLite architecture, component interfaces, evidence requirements and acceptance cases from AUD-40. The local coordinator is now implemented; fixtures remain synthetic only.

The README replaces the initial placeholder. Sandbox exclusions are appended to the existing Python .gitignore. No workflow YAML is added. Main remains unchanged until a separate merge.

Source basis: the current owner conversation and the Notion Foundation Audit retrieved 2026-10-22. The owner selected the existing public sandbox repository and authorized continuing with publication of the review draft. Runtime isolation, execution and production integration are not validated or activated.

The local suite now applies the schema and passes 14 unit/integration tests, including transaction rollback and corruption injection. Full acceptance, concurrency, host isolation, authority resolution and deployment remain unverified. See docs/implementation-validation.md. This supersedes the earlier draft-stage no-execution statement; it does not retroactively change that historical result.
