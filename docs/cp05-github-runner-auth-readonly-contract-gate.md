# CP05 GitHub runner → Socra identity authentication gate

## Official verified contract (2026-11-08)
Socra's published agent identity guide documents the **client credentials** exchange:
- POST `https://oauth.socra.cloud/oauth/token` as application/x-www-form-urlencoded with `grant_type=client_credentials`, `client_id`, `client_secret`, and `principal_id`.
- The `principal_id` is the **raw UUID** returned by the active OAuth installation; it is **not** the Directory `user_...` ID.
- Identity verification: POST `https://account.socra.cloud/directory/v1/users/me` with the Bearer access token and JSON `{}`; require `type=app`, `role=member`, and match the installation's expected identity.
- Cortex MCP endpoint: `https://cortex.socra.cloud/mcp`. A valid token alone does not prove Cortex resource grants.
Sources: https://workspace.socra.com/docs/admin/agents/create-an-agent and https://workspace.socra.com/docs/cortex/reference/mcp

## Evidence and boundary
GitHub runner preflight 42446349632 confirmed only SOCRA_CLIENT_ID and SOCRA_CLIENT_SECRET are nonempty. ChatGPT-connected Cortex separately created and read back module `module_01m6wpwex46vvgmsq9pr4k88d5`. Neither proves runner OAuth. **SOCRA_PRINCIPAL_ID has not been verified in the runner**.

## Next test
1. Owner verifies active installation and securely adds raw principal UUID to GitHub Actions secret `SOCRA_PRINCIPAL_ID`; never post ID or secrets into a public issue.
2. Manually dispatch `.github/workflows/cp05-socra-installed-principal-identity.yml`.
3. Runner requests token and verifies app identity without printing secrets, token, raw HTTP bodies, or full principal IDs. Output only PASS/BLOCKED and bounded reason.
4. Only after identity PASS, separately verify Cortex read access to a known synthetic module with a documented read-only Cortex API request contract.
5. No live write, automatic retry, multiworker activation, or CP02/CP05/CP09 closure from identity PASS.

## Fail-closed
Missing principal, 401/403, malformed JSON, unexpected identity, redirect, or HTTP timeout means BLOCKED. No guessed token exchanges or write fallback. All GitHub runner actions remain single-writer-proposal-only until remote fencing is verified.
