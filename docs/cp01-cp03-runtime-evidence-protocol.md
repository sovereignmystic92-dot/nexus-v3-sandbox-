# CP01/CP03 runtime evidence protocol (no credentials)

Status: **EVIDENCE COLLECTION ONLY**, Foundation Audit 13/19.

## Existing readback

- GitHub installation 174264654 has selected-repository scope and event subscriptions to check, issue, PR, repository and status events. This establishes the linked GitHub App's available surface, not the effective permissions of every other app or host.
- Isolated synthetic acceptance GitHub run 41179357097 completed successfully with Docker boundary and cleanup tests. The GitHub Actions runner job is still a trusted host outside the network-none container.
- GitHub run 41177999986 confirmed external HTTPS reachability from the host. It is not a host egress-denial test.
- GitHub run 41174629509 confirms an environment-gated no-provider-write job completed after approval. It does not independently prove exclusion of all secrets from other jobs.
- The full 13-workflow credential-reference inventory is recorded in Issue #91. Six workflows have no secret expressions; seven explicitly request provider secrets. All declare `permissions: {}`.

## Safe evidence sequence

1. Obtain authoritative read-only GitHub environment settings for `notion-sandbox` and `gemini-pilot`, including required reviewers, branch restrictions and **secret names only**, never secret values. Distinguish environment access controls from job-secret exposure.
2. Obtain a GitHub-hosted runner isolation statement, operating system image/revision, VM boundary and trust assumptions from provider documentation. A GitHub source file alone is not independent host assessment.
3. On a no-environment/no-secret manual job, test only fixed expected credential environment *names* without printing values, check for host socket exposure, and report immutable runner/run identifiers. Do not dump `env`, `/proc`, mounts or file contents to public logs. This can prove absence of those names in that specific job only.
4. Compare that no-credential job with the environment-gated provider jobs and identify any unreviewed host-side secret routes. Use safe denied-access tests that do not send provider tokens to unauthorized destinations.
5. Obtain independent review and scope-specific acceptance. Do not claim CP01 or CP03 PASSED solely from a job's self-reported assertions.

## Outstanding

The GitHub connector available in this session does not expose read-only environment secret-name enumeration or runner host configuration endpoints. Without authoritative host/environment evidence and negative exclusion tests, CP01 and CP03 remain PARTIALLY_VERIFIED. Direct ChatGPT connector and automation execution hosts remain separate inventory items.

No infrastructure, workflow trigger, secret, credential, provider or checkpoint changes are authorized by this protocol.
