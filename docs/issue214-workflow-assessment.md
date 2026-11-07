# Issue #214: workflow inventory assessment

## Authorization and execution receipt

Owner decision: [issue #214 comment](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/214#issuecomment-6705159423), dated 2026-11-07.
The current ChatGPT Codex task additionally authorizes a draft repair PR.
This assessment was executed manually through the existing ChatGPT Codex session:
repository inspection, GitHub log readback, offline reproduction and tests actually ran.
This is not a receipt for unattended Codex or a GitHub Actions Codex job.
No OpenAI API key, API billing, new credentials or external service mutations were used.
GitHub draft publication is the only proposed remote write; no merge is authorized.

Base main: `7049030783dc25bbc83949b2235f7768530ee089`.
Read AGENTS.md, OWNER_APPROVAL_POLICY.md, SECURITY.md, REVIEW.md,
the architecture and CI coverage documentation, and current workflow/test contracts.
This is an author assessment, not independent approval or checkpoint promotion.

## Observed failure and reproduction

[Run 42360473691](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/42360473691),
job `128367587698`, fetched PR #213 merge candidate
`377fc380ed0af5d28c3b47d08ed35387a79af518`.
`python3 -I checkout/tools/verify_workflows.py` failed during inventory verification;
the mocked test step was skipped. This was not a provider authentication failure.

Offline reproduction from fetched Git archives established:

| Revision | Unreviewed workflow | Other inventory differences |
| --- | --- | --- |
| PR #212 `3892192127e9426ed6e8c47d017ddfc5a9c16847` | `nexus-codex-task-intake.yml` | None |
| PR #213 `8ef814fe67e19e80aee42cdfc4a278e72eea1497` | `nexus-codex-readonly.yml` | None |
| Observed #213 merge candidate above | `nexus-codex-readonly.yml` | None |

Both PRs omit their new workflow from `tools/workflow_policy.json`.
Calling `verify_credential_routing` separately on each snapshot also rejects its
nonempty top-level permissions. Both reference `github.token`, which the checker
separately prohibits. #213 additionally references unapproved `OPENAI_API_KEY`.
Thus adding hashes alone cannot make either proposal policy-compliant.

## Minimal compliant disposition

- Leave `tools/workflow_policy.json` unchanged on current main: its 29 files match.
  Do not regenerate an allowlist to bless unreviewed workflow bytes.
- Keep API-dependent PR #213 draft and undispatched, per owner decision.
  Do not add an `OPENAI_API_KEY` exception, obtain credentials, or loosen
  `verify_credential_routing` to admit it. It is unnecessary for manual Codex access.
- PR #212 is intake only, not Codex execution. If retained, first revise
  `.github/workflows/nexus-codex-task-intake.yml` to `permissions: {}` and remove
  `GH_TOKEN`/`github.token`. This public repository permits unauthenticated issue
  reads; denial or rate limiting must remain BLOCKED. Preserve the open-issue,
  structured-handoff and approval-label checks, and add dispatch-actor and bounded
  response/body checks. Review action pins and receipt retention before activation.
  Then explicitly add only that revised file's SHA-256 to the policy, together
  with negative tests for missing approval, invalid issue and failed lookup.
  No such workflow revision or activation is included here.
- Publish clearer inventory diagnostics in `tools/verify_workflows.py`, with
  regression coverage in `tests/unit/test_workflow_policy.py`. Rejection remains
  mandatory; diagnostics contain filenames only, never workflow bodies or secrets.
  No workflow, permission, credential allowlist or source-provenance guard changes.

## Verified local results

Evidence classification: **offline/synthetic**, plus authenticated read-only
GitHub metadata/log retrieval. No live Socra, Notion, Gemini or OpenAI API calls.

| Command/check | Result |
| --- | --- |
| `PYTHONPATH=src python3 -m unittest discover -s tests/unit -p test_workflow_policy.py -v` | 3 passed |
| `PYTHONPATH=src python3 -m unittest discover -s tests/unit -p test_ci_source.py -v` | 6 passed |
| `python3 tools/validate.py --output /workspace/scratch/issue214-validation.json` | 833 distinct tests passed; full acceptance BLOCKED |
| `python3 -m unittest discover -s integrations/gemini -p 'test_*.py' -v` | 13 passed, mocked only |
| Direct `verify` and `verify_credential_routing` on this main-based branch | 29-file inventory and routing passed |
| `python3 -I tools/verify_workflows.py` in development shell | Inventory/routing passed; CI-only protected-credential-name absence assertion rejected this host |
| `git diff --check` | Passed |

The focused tests are included in the 833-test total, not additional distinct tests.
No environment was sanitized to manufacture the CI-host assertion.
`tools/run_isolated.py` remains for the intended trusted GitHub runner; no source
or retention assertions were fabricated locally. Fresh PR CI must verify the
published revision. Existing run 42360473691 remains failed historical evidence.

## Remaining blockers and next step

Review this diagnostic-only draft and obtain fresh GitHub CI results. Original
PRs #212/#213 remain intentionally blocked by unchanged policy. Any future #212
workflow/hash revision needs its own exact-byte review and negative intake tests.
#213 stays deferred while the owner chooses existing ChatGPT Codex access.
No provider access, production readiness or unattended execution is established.

Rollback: revert the diagnostic draft commit; no workflow or remote configuration
rollback is needed because neither is changed.
