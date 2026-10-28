# One-checkpoint live write verification

Owner authorization in the 2026-10-28 conversation covers this bounded live test,
publication and governed sandbox adoption after review. Broader bridge activation
and production changes are excluded. CP09 assessment/testing was separately
reauthorized; this workflow does not establish remote ownership or fencing.

The manual `Notion bounded checkpoint write verification` workflow uses the existing
`notion-sandbox` environment and `NOTION_SANDBOX_TOKEN`. It runs on main only with
`checkpoint_test_confirmed=true` and retains the native environment approval gate.
No secret, permission, platform-setting or paid AI API is created or changed.

Exactly one initial NXS_CHECKPOINT_V1 enrollment/test checkpoint may be appended
on Foundation Audit page 4018c067daa48122b82ec2ae8067d021. It contains synthetic
binding metadata and empty receipts; it is declarative evidence, never executable
work. Marker NXS-LIVE-CHECKPOINT-<GitHub run ID> and source SHA identify the attempt.
The marked record is retained as evidence; no deletion is authorized by this test.

The preflight inventory must be complete and valid before append. A fresh complete
inventory independently verifies the exact generated event after append, including
uncertain acknowledgment. At most one PATCH attempt and 22 GETs are permitted.
Malformed JSON, conflicting identity, duplicate records, incomplete pagination or
readback mismatch hold. No blind retries. Reruns of the same GitHub run disable
writes in both probe and HTTP client, and can only observe. A new dispatch creates
a new identity: do not launch a second dispatch to recover an uncertain first run.
This is not atomic CAS, remote exclusivity or a CP09 implementation.

Ten focused tests and all 405 local unit tests passed. Both independent initial
review sessions approved the exact four implementation/test/workflow/policy files:

- /root/transport_review_a: 405 full tests, 10 focused tests, workflow verification,
  and an independent exact-boundary simulation with 22 GETs and one PATCH.
- /root/transport_review_b: 10 focused tests, workflow verification, independent
  repeated-pagination and duplicate-block rejection checks.

Both recorded initial findings before seeing the other's conclusions. Same
inherited Codex model family; exact runtime model identity not independently
observable. Neither reviewer changed files or made live provider requests.

Reviewed SHA-256 bindings:
- tools/notion_checkpoint_write_probe.py: 082165902d5addd498c2e745cc0b48c0459c1eeb5a44395355ffd4fe10c1c838
- tests/unit/test_notion_checkpoint_write_probe.py: e14c3a56248d4e56e52948e97a81af63cfc2bdc9900dc0355c5c278c119fd4d4
- .github/workflows/notion-checkpoint-write-probe.yml: 68544b1caad034ba63c1bf4c50c787c109e3a218a3fb2c9d753c16a9d6d00048
- tools/workflow_policy.json: bed31ce05a47cdac56d01bbb47edeccb94af94eb7e5a7107f7af9143f3e325eb

Hosted validation, adoption and actual provider outcome must be verified separately.
The connected GitHub API exposes no workflow-dispatch operation in this session;
the owner may need to launch this manual workflow and approve its environment.
A successful Chat Notion tool write would not establish Actions-token write access.

## CP09 reproduction

The existing deterministic offline overlapping-worker probe was rerun on the
working checkout based on main 0ce8234bfa0e0b40f1910c32312a78f6ee61a702. Its source
and current adapter hashes matched the original recorded hashes. Three observation
assertions passed; two reproduce stale overwrites before readback detects them.
The one same-key/shared-journal schedule prevents a second write, which does not
prove general fencing. No provider calls occurred. CP09 remains BLOCKED for
multiworker use. The original result's frozen-implementation label is historical;
this rerun does not claim a newly implemented protection.

Required next CP09 step: establish a destination-supported conditional mutation
or an exclusively enforced writer gateway with definitive quiescence before
ownership transfer. Client locks, GitHub concurrency and readback alone are not
remote stale-worker fencing. No concurrent live race is enabled here.
