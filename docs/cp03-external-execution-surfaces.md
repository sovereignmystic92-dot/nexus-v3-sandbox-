# CP03 external service and execution-surface inventory — 2026-10-31

**Scope:** distinguish credential-free GitHub CI host evidence from other connected execution services. This is a routing map, not a provider grants audit or credential absence attestation.

| Surface | Established | Remaining gap |
| --- | --- | --- |
| GitHub Actions no-environment Gemini offline CI | The existing PR workflow executes a host-side check for seven fixed protected credential variable names, without reading values. | Other processes, filesystem/mounts, other names, host Docker and Actions service internals. |
| GitHub Actions Notion sandbox | Six manual provider workflows use protected environment; owner screenshots show main-only, required reviewer, no admin bypass, three secret entries with truncated names. | Complete provider-side names, effective grants, exclusion from other hosts. |
| GitHub Actions Gemini pilot | One manual provider workflow uses protected environment; owner screenshots show main-only, required reviewer, no admin bypass, one truncated secret name. | Effective key scope and exclusion from other hosts. |
| GitHub App connector | Selected-repository installation was read back. GitHub tools permit session-authorized operations. | Full effective grants, other app installations and execution-host isolation. |
| ChatGPT Notion connector | Available separately from GitHub Actions Notion environment. | Workspace grants, OAuth scope, credential injection and Nexus automation access. |
| Socra Cortex connector | Available separately from GitHub Actions. | Project permissions, storage, credential isolation and cross-service sync. |
| ChatGPT Automations | Nexus maintenance, backlog and integration-readiness schedules exist. | Host environment, trigger paths, service tokens and workflow independence. |
| Browser Use / cloud browser | Available as an independent interactive execution service. | Session/cookie identity, permissions and separation from CI. |
| Gemini CLI / Google Cloud Shell | Previously explored by owner; current operational status unverified. | Cloud project grants, keys and runtime boundaries. |
| Codex | Previously explored as GitHub-capable agent; current runtime access unverified. | Effective repository write grants and workflow routing. |

## Interpretation

The fixed-name negative test runs in the host process of an existing no-environment GitHub Actions CI job. It can establish only the absence of those names from that specific process environment at test time. It does not establish secret absence in other jobs, ChatGPT-connected services, cloud browsers, Gemini CLI or automation hosts.

No secret values, environment dumps, credential-bearing files, production provider writes, new workflow triggers or paid resources are required. CP03 remains PARTIALLY_VERIFIED until complete independent cross-surface inventory and safe denied-access evidence are accepted.
