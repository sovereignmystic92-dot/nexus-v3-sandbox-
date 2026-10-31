# CP01 + CP03 parallel closure assessment — 2026-10-31

**Decision: both remain PARTIALLY_VERIFIED.** This record adds source-level negative checks, not host attestation or independent assurance. Foundation Audit stays **13/19**.

## CP01: host and filesystem isolation

Verified in existing hosted synthetic acceptance: Docker inspect confirms network-none, nonroot UID 65534, read-only root and source bind, all Linux capabilities dropped, no-new-privileges, bounded CPU/memory/PIDs, isolated PID/IPC, no extra devices and no host socket. The container checks process capability flags, network interfaces/routes, TCP/UDP/IPv6 denial, no Docker socket and denied source writes. Host-side staging cleanup and container removal are reported. **This is an isolated container on a shared-kernel GitHub-hosted VM**, not an independent assessment of host or hypervisor trust.

**Outstanding:** independent review of the runner provider's isolation model and host boundary, runner identity/revision and host trust assumptions; confirmation of all privileged host-side operations and mount/secret paths. A code author cannot self-certify these by adding tests.

## CP03: credential and mount exclusion

The new `tools/check_cp01_cp03_boundaries.py` examines four specifically scoped no-credential workflow source files: `synthetic-acceptance.yml`, `gemini-offline.yml`, `cp04-environment-enforcement-probe.yml`, `cp04-host-reachability-observation.yml`. It requires `permissions: {}` and rejects explicit `secrets.*`, `github.token` and known token environment assignments. Negative tests confirm these patterns are rejected. Existing container probe also rejects credential-looking environment names and undeclared mounts inside its sandbox.

**Outstanding:** inventory of every host-mediated integration, environment secret binding, mount, GitHub App grant, automation host and direct connector. The Notion and Gemini provider jobs explicitly reference environment secrets on the host; source checks of unrelated no-secret workflows do **not** prove production credentials are absent from every in-scope execution surface. Do not print secret values or environment dumps. Provider-side effective grants belong to CP02 as well.

## Required next evidence to reach 15/19

1. CP01: independently attributable host trust assessment, runner configuration and full host boundary scope.
2. CP03: complete, redacted secret-name/mount inventory for each executing surface, verified absence from unauthorized jobs/hosts and safe negative access evidence.
3. Independent readback of the exact revision, hosted test logs and host/provider settings; explicit assessor disposition under the unchanged requirements.

This PR changes only reviewable source tests and documentation. No secrets, workflow triggers, network policies, provider writes, cloud resources, paid services or checkpoint statuses are changed.
