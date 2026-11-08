# CP05: installation identity discovery gate

## Confirmed
- GitHub Actions credential-presence run 42475264163 succeeded.
- This proves nonempty SOCRA_CLIENT_ID and SOCRA_CLIENT_SECRET in the runner context, **not** their validity.
- No installation principal ID is currently confirmed for the GitHub runner.

## Required before a live token request
1. Verify the **official Socra CLI** distribution, installation, and supported authentication contract from primary documentation. Do not download an unverified executable.
2. Determine whether `socra oauth installation list` is authorized using client credentials alone or requires an existing authenticated user/session. Do not assume either.
3. Use a manually dispatched, permission-minimal workflow only after steps 1–2 are documented and reviewed. Fail closed if no valid authentication is available.
4. Record only allowlisted metadata: provider, principal ID, installation ID, owner ID, and verification status. Never log access tokens, client secrets, raw HTTP bodies, or personally sensitive metadata.
5. Match the discovered principal to the expected Cortex owner and grant before a read-only API probe.
6. No write, no scope escalation, no automatic CP05 promotion. Later bounded write/readback requires a separate verified grant.

## Current state
**BLOCKED: no independently verified GitHub-runner installation principal or confirmed installation-list authentication contract.**

The ChatGPT Cortex connector's permissions do not establish GitHub-runner permissions.
