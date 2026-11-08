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

## Verified Socra documentation (2026-11-08)
- Official CLI reference: https://cloud.socra.com/docs/oauth/reference/cli
- `socra oauth installation list` requires the CLI's authenticated **Account context**. It does **not** accept client ID/client secret directly. Do not invoke it on a clean runner expecting those secrets to work.
- `socra oauth token create` requires `--client`, `--principal`, and `--client-secret-file`; optional `--scope` should be explicitly restricted. Do not invoke until the principal is verified.
- Official CLI installation instructions: https://cli.socra.com/ (install script https://cli.socra.cloud/install.sh). Review/pin the installer before running in CI; do not pipe a mutable script directly to a privileged runner.
- OAuth API reference: https://cloud.socra.com/docs/oauth/reference/api
- **Resolution:** use an already authenticated Account context to discover the installation principal through a supported account-side process, then configure a bounded runner token exchange. Client credentials alone cannot discover the principal.
