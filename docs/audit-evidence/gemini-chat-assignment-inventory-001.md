# Nexus collaborative mission assignment — inventory 001

Status: ASSIGNED / AWAITING OWNER-MANUAL DISPATCH. Not yet executed, reviewed, or scored.

- Mission: `synthetic:nexus-review:inventory-001`
- Classification: synthetic, fictional, nonprivate, publicly loggable.
- Coordinator: ChatGPT (created this assignment record from the owner's approved collaboration pilot).
- Lead: Google Gemini via existing manual `gemini-smoke.yml` workflow on `main`.
- Independent reviewer: ChatGPT, using only the task packet facts and a fresh run's output.
- Scope: one read-only Gemini analysis, at most one API request, no tools, app writes, scheduled triggers, or production credentials beyond the existing bounded pilot secret.
- Source task packet: `integrations/gemini/example-task.json` on `main`, exact `task_id` above.
- Workflow: https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/workflows/gemini-smoke.yml
- Dispatch: requires owner manually running on `main` after verifying Free Tier, pasting the exact synthetic JSON into `task_json` and affirming `synthetic_confirmed`. If environment approval appears, the owner reviews it independently.
- State: AWAITING_RUN. No claim this record invokes GitHub Actions.

## Review rubric (determined before the result)
1. Twelve kits require 12 notebooks and 24 pencils (12 × 2).
2. The sheet lists 12 notebooks and 20 pencils, four pencils short.
3. Listed notebooks suffice on paper; neither inventory count is physically verified.
4. No kits are assembled; therefore complete readiness cannot be confirmed.
5. Gemini must cite S1 and S2 as appropriate and distinguish inference from evidence.
6. Reviewer must flag any unsupported confidence, inventory claim, claim of physical verification, or claim of kit assembly.
7. Final collaboration record must link actual run ID, log provenance, response, independent review, disposition, disagreements, and remaining unresolved audit controls. No self-certified pass.

## Audit candidate mapping
- CP02: owner-authorized, human-mediated mission selection; automated routing NOT tested.
- CP03/04: bounded Gemini connectivity and credential boundaries; fresh run pending.
- CP05: GitHub assignment/evidence path exists, but Notion and Cortex independent readback NOT tested.
- CP10: distinct reviewer planned; a fresh independent review and its evidence are pending.

## Safety and stop conditions
No live Notion/Cortex writes, no merge, no schedule, no D26 host activation. Never repeat an uncertain provider call just to obtain a result; inspect the run log first. Offline fixture output must never substitute for a real Gemini response. A successful workflow is evidence of API receipt, not of answer correctness.
