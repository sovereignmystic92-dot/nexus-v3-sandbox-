# CP04 host-egress enforcement: acceptance evidence and bounded test design

Status: **DRAFT / NOT EXECUTED**. This document does not change workflow triggers, permissions, secrets, environments, or the checkpoint register.

## Verified current facts
- The 12 `tools/workflow_policy.json` workflows declare `permissions: {}`. This limits the GitHub Actions token; it does **not** restrict outbound traffic from a runner, or GitHub App / ChatGPT connector authority.
- The `notion-sandbox` environment has owner-observed required review and `main` branch admission; the isolated CP04 probe succeeded on main (run 41174629509) and was rejected on a non-main branch (run 41175088742; see Issue #91).
- `gemini-pilot` has owner-observed required review and main-only deployment policy; actual negative server-side enforcement for this separate environment is **not tested**.
- Repository-level webhooks were absent on the owner-observed GitHub settings page. The installed ChatGPT Codex Connector has GitHub App event subscriptions and selected-repository grants, which are separate from repository webhooks.
- Three enabled ChatGPT-hosted automations have schedules outside GitHub Actions.
- The reviewed Notion client targets `https://api.notion.com` and the Gemini smoke client targets `https://generativelanguage.googleapis.com`. Both avoid inherited proxies and redirects in their Python clients. Scripts are fetched from `raw.githubusercontent.com` over HTTPS. These are **code restrictions**, not a host egress firewall.

## What a meaningful CP04 network test must demonstrate
1. **Host identified:** exact execution host, trust boundary, actor, runner image/revision, network policy revision, and network-policy owner.
2. **Enforced deny:** a harmless HTTPS request to an explicitly unapproved, public test endpoint is denied by an **external enforcement boundary**, not merely a Python allowlist, DNS failure, application exception, or an absent credential. Capture the enforcement policy decision and run ID. Do not send secrets or private content.
3. **Enforced allow:** a harmless request to an approved, non-mutating endpoint succeeds from the same runner under the same policy; record request method, status and destination without logging credentials.
4. **Policy bypass check:** demonstrate that a different client/library or direct socket cannot reach the denied destination from the same workload identity. Otherwise the denial may be application-only.
5. **Control plane:** verify who can change egress policy, dispatch workflows, edit workflow code, approve environments, install apps, and use direct provider connectors. Branch protection and workflow job `permissions: {}` alone do not prove this.
6. **Inventory:** enumerate GitHub Actions, GitHub App event subscriptions, repository webhooks, ChatGPT automations, direct Notion/Cortex/Gemini connectors, and any other deployed runner/listener. Mark any inaccessible surface UNKNOWN rather than absent.
7. **Independent review:** reviewer verifies original host policy, raw test evidence, source revision and destination inventory; update CP04 only if the unchanged full requirement is supported.

## Current blocker and safe next step
Standard GitHub-hosted `ubuntu-24.04` runners in the inspected workflows have **no demonstrated outbound network firewall or proxy policy**. Running a no-secret `curl` probe there may show that a public destination is reachable, but a denial by Python client code is not host-enforced isolation. Do **not** manufacture a PASS from that outcome.

First obtain authoritative evidence of an existing host/network egress control from the execution-host administrator or provider. If none exists, design a reviewed isolated execution boundary (e.g. constrained runner/network egress proxy), and test it in a separate synthetic environment before using provider credentials. This is a security architecture change requiring review; it is **not authorized by this document**.

## Related checkpoints
- CP01: exact hosted isolation/mount and independent trust assessment.
- CP02: all executing identities, GitHub App grants and safe provider-side denied out-of-scope access.
- CP03: complete secret/mount inventory and exclusion from unauthorized hosts.
- CP05: independently verified provider-side destination binding and denial before mutation.
- CP09: remote fencing remains paused; single-worker assumption does not prove fencing.

**Scoring:** CP04 PARTIALLY_VERIFIED; full Foundation Audit 13/19. No provider dispatch, secret inspection, network probe, production integration, or checkpoint promotion performed.
