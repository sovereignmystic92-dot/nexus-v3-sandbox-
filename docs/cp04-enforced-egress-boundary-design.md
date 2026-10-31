# CP04: network boundary implementation proposal

Status: **DESIGN ONLY**. No network policy, credentials, infrastructure, or provider integration has been changed. Foundation Audit remains **13/19**.

## Observed baseline

GitHub Actions run 41177999986 returned HTTP 200 from example.com and example.org in a no-credential observation. This demonstrates outbound reachability on that runner, not an enforced network allowlist. Existing Docker network-none isolation covers offline synthetic tests, not the GitHub-hosted jobs executing Notion and Gemini API clients.

## Preferred minimal pilot

Evaluate a dedicated disposable execution host or isolated network, with outbound access governed by an independently administered default-deny network policy. A hostname-aware gateway may be needed for provider HTTPS endpoints. The workload identity must not be able to change the policy or bypass the gateway.

Start with a synthetic pilot without provider credentials. Confirm an explicitly approved public HTTPS endpoint succeeds and an explicitly denied public endpoint is rejected by the network enforcement system. Capture the policy decision alongside the run. Test a second client, IPv6, direct-IP attempts and DNS/proxy bypass paths. An application exception or DNS failure is not sufficient proof.

## Alternative

An independently managed outbound gateway is acceptable if workloads have no other internet route, the gateway applies a reviewable allowlist, and direct connections cannot bypass it. Merely configuring a Python HTTP client or a Docker test container does not establish host-level enforcement.

## Review and migration gates

1. Record host identity, network owner, policy revision, routing and resolver configuration.
2. Inventory every relevant workflow, GitHub App subscription, repository webhook, ChatGPT automation and direct provider connector, marking uninspected surfaces UNKNOWN.
3. Perform no-secret same-host allowed and denied tests, including alternate-client bypass attempts.
4. Obtain independent review of raw enforcement evidence and policy ownership.
5. Only then consider a separately reviewed migration of a synthetic Notion read-only workload; assess Gemini separately. Retain existing environment approvals and main-only branch controls.
6. Update CP04 only after its complete, unchanged acceptance requirement is supported.

Cost constraint: no paid host or gateway provisioning without explicit owner approval. No live provider calls, secrets, workflow changes or checkpoint promotion are part of this proposal.

Reference: Issue #91 and GitHub Actions run 41177999986.
