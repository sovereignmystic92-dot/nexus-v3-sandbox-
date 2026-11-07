# Nexus unattended maintenance — initial runtime inventory (2026-11-06)

## Confirmed from GitHub Actions

- Repository reports 1,511 historical workflow runs. In the most recent 100: 82 `pull_request`, 14 `push`, two `workflow_dispatch`, two `issues`, **zero `schedule`**. This is a bounded sample, not proof that no older scheduled execution exists.
- The most recent merge-to-main push launched successful [isolated synthetic acceptance](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/42331883745) and [Gemini bridge offline tests](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/42331883675). These are automatic CI tests, not demonstrated backlog processing.
- `.github/workflows/nexus-cp03-cp04-evidence.yml` has `schedule: cron '22 2 * * *'` plus manual dispatch. Manual [run 42330430915](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/42330430915) saved an `OBSERVED_TRIGGER_ONLY` receipt with `audit_pass=false`. A scheduled receipt was **not observed in the latest 100 runs**.
- `synthetic-acceptance.yml` is triggered on push and pull request; `gemini-offline.yml` is triggered on push and pull request. Both have `permissions: {}` and are not scheduled maintenance processors.
- `warfronts-source-tests.yml` runs on scoped pull requests or manual dispatch, not a caption ingestion schedule.

## Classification and missing proof

| Claim | Current disposition | Needed evidence |
| --- | --- | --- |
| Automatic repository CI | CONFIRMED | Existing successful push/PR runs suffice |
| Daily CP03/04 receipt scheduled in code | CONFIGURED | First real `event=schedule` run and its artifact |
| Actual unattended backlog processing | NOT VERIFIED | Source trigger, job logs showing queue consumption, output/ledger readback |
| Actual unattended daily maintenance | NOT VERIFIED | Schedule/controller identity, job logs and persisted maintenance outcome |
| CP03 full credential isolation | OPEN | See `docs/cp03-cp04-operational-evidence-reconciliation-20261106.md` |
| CP04 host-enforced egress | OPEN | See same reconciliation |

## Recommended safe follow-through

1. Observe the next naturally triggered CP03/04 scheduled run; do not substitute manual dispatch for a scheduled receipt.
2. Inventory ChatGPT scheduled controllers and any external maintenance runner separately from GitHub CI; repository-only history cannot establish those executions.
3. Before adding schedules, identify a real bounded maintenance command and durable result destination. Do not label synthetic tests as operational maintenance.
4. Keep manual-only approval/secret-bearing Gemini, Notion and CP04 security probes manual-only. Do not change credentials, permissions, provider data, or CP09 fencing.

This document records observed evidence only. It neither closes an audit checkpoint nor claims a new automation was deployed.
