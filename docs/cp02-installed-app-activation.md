# Nexus CP02 dedicated Cortex runtime identity — activation runbook

Status: **HELD — review/setup required**. This is an owner-controlled provisioning procedure, not evidence that authorization has occurred.

## Provider-supported route

Socra documents a distinct **installed app** account principal for external runtimes:
https://workspace.socra.com/docs/admin/agents/create-an-agent

That installation is *not* a Socra Agents teammate and *not* a second human login. It creates a new Account member of type `app`, role `member`. A human owner/admin must approve the installation in the intended Socra Account. The installed app does not inherit owner permission on Cortex modules.

1. Owner/admin verifies the intended Account and Cloud Project. Create a dedicated Cloud Project with internal audience (or use a specifically approved existing project; avoid changing a production project).
2. Register a confidential OAuth client and one revocable secret. Retain the secret in a private supported credential store **outside this repository, issues, chats and logs**.
3. Install the client into the same intended Account using the owner/admin session and record nonsecret `installation_id`, raw `principal_id` UUID, `client_id`, and resulting Directory `user_...` ID. Confirm the installation is ACTIVE. Do not publish identifiers unnecessarily.
4. Grant this installed app **module viewer only** on the approved synthetic `Nexus Sandbox ...` test fixture. Do not give module.admin, module.edit, issue mutation, production writes, inherited parent privileges or access to denied controls.
5. Provision the dedicated nonowner runtime with `client_id`, `principal_id`, `client_secret` via protected configuration. Never expose the secret to GitHub PR runners, chat messages or Cortex module content.
6. The runtime exchanges client credentials at `https://oauth.socra.cloud/oauth/token`, then sends the **issued token** to `POST https://account.socra.cloud/directory/v1/users/me` and verifies `id=EXPECTED_USER_ID`, `type=app`, `role=member`. Use **that same access token** for Cortex GET `/v1/modules/{name}/access` and GET `/v1/modules/{name}`. This is the contract represented by `gate_bound_identity.py`, `gate_bound_runtime.py`, `gate_bound_https.py`.
7. Record only scrubbed evidence: installed principal ID reference, executed action, pinned fixture ID/version, present/absent permissions, readback result, provider response status, and timestamps. Verify an allowed positive read plus independently evidenced denied-resource access. **Do not perform a forbidden write** to test denial.
8. Only after independent PR review, verified host identity, exact source/fixture revision and complete readback should an owner separately approve any actual synthetic provider write execution. CP09 remote fencing must be independently established where multiple writers are possible.

## Current blocking facts

- PR #121 is draft. Hosted isolated acceptance proves offline behavior, **not** provisioned app identity or end-to-end live Cortex use.
- ChatGPT's present Cortex connection is the human owner account; its secret cannot be imported into Nexus runtime by this code.
- There is no verified account installation, token/Directory readback, or installed-app access denial in current evidence.
- All provider write functions remain withheld. No deployment or checkpoint promotion is authorized.
- If the owner has only an iPhone, Socra Admin and Cloud setup are browser-accessible; never paste token/secret values in ChatGPT. Share only redacted status screenshots or nonsecret installation outcomes.

## Strict success criteria

`REAL_RUNTIME_IDENTITY=VERIFIED`, `RESTRICTED_PRINCIPAL_ACCESS=VERIFIED`, `EXPECTED_FIXTURE_READBACK=VERIFIED`, `NEGATIVE_RESOURCE_ACCESS=VERIFIED`, `PR_REVIEW=ACCEPTED`, and `DEPLOYED_ENFORCEMENT=VERIFIED` must **all** be independently supported before claiming the adapter's operational integration complete.

Until then: `EXECUTION_BOUNDARY=HELD`; `CP02/CP05/CP09` unchanged; foundation audit **13/19**.
