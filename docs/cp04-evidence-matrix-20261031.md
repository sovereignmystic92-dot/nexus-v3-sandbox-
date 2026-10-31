# CP04 evidence matrix — acceptance gate (2026-10-31)

**Status: NOT ACCEPTED.** The Foundation Audit is **13/19**. This matrix is not evidence that a provider-host egress policy exists.

| Requirement | Observed evidence | Verdict | Missing acceptance evidence |
|---|---|---|---|
| Reviewed workflow inventory | 12 YAML workflow names pinned in `tools/workflow_policy.json`; GitHub workflow job tokens use `permissions: {}` | OBSERVED | Independent complete inventory of all non-YAML execution surfaces |
| Synthetic offline network denial | `tools/run_isolated.py` creates Docker `--network none`; `tools/container_probe.py` checks loopback-only and denied TCP/UDP/IPv6 to documentation IPs; `gemini-offline.yml` uses Docker `--network none` | IMPLEMENTED IN TEST CONTAINERS | Do not extend conclusion to host or provider jobs |
| Notion environment review/branch admission | Owner-authenticated settings and GitHub run 41174629509 (approved main), run 41175088742 (rejected non-main) | OBSERVED | Complete independent evidence capture/assessment |
| Gemini environment review/branch admission | Owner-authenticated settings show required review and main-only | CONFIGURATION OBSERVED | Independent safe negative branch run for `gemini-pilot`, if approved |
| GitHub App event hooks | Installation API: selected repository, GitHub App event subscriptions; owner screenshot lists one Codex connector | OBSERVED | External service-side actor, grant, event delivery and action inventory |
| Repository webhooks | Owner-authenticated GitHub settings screenshot: none listed | OBSERVED AT INSPECTION | Recheck on changes; does not cover GitHub Apps |
| ChatGPT automations | Three enabled Nexus automation schedules identified, outside YAML | OBSERVED | Host identities, outbound reachability and enforced policy for these execution surfaces |
| Provider HTTPS destinations | Notion client: `api.notion.com`; Gemini smoke: `generativelanguage.googleapis.com`; source retrieval: `raw.githubusercontent.com` | CODE PATHS OBSERVED | Network policy independent of Python code, alternate-client denial, full dynamic destination coverage |
| Host-enforced allow/deny | No configured firewall or policy was established for standard `ubuntu-24.04` GitHub-hosted provider jobs | **NOT PROVEN** | Same-host allowed + denied network tests with authoritative policy evidence |
| Identity/secret exclusion | Some workflow-level secret references and isolated container checks inspected | PARTIAL | Full effective grants, host secrets/mount inventory and safe denied-access tests (CP02/CP03) |

## Decision tree to 14/19

1. **Existing enforced policy found?** Retrieve authoritative policy config, owner, runner/workload identity and change control. Conduct approved *no-secret* positive and negative tests from the **same** execution context, with alternate-client bypass attempt. Record raw evidence and independent review.
2. **No policy found?** CP04 remains partial. Reuse existing Docker `--network none` for offline synthetic workloads, but **do not** route provider credentials into a network-none container expecting provider requests to work. Propose a narrowly network-enabled, independently filtered execution boundary as a separate security-reviewed change.
3. **All paths inventoried and approval gates verified?** Only then seek independent adjudication against the full CP04 requirement. A test passing alone does not change score.

## Safety
No live provider dispatch, secret inspection, new credentials, network configuration, workflow activation or checkpoint promotion is authorized by this document. CP09 remains deferred.
