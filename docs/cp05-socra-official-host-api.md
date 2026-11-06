# CP05 — Official Socra Cortex host API discovery (read-only integration)

Status: **DOCUMENTED PROVIDER SURFACE; RUNNER AUTH NOT VERIFIED**. This does not authorize production activation, new credentials, or provider writes.

## Verified public provider documentation

- Cortex API: https://workspace.socra.com/docs/cortex/reference/api — base `https://cortex.socra.cloud`; API endpoints under `/v1`. Requests use `Authorization: Bearer <Socra access token>`. The API documents Modules and module access/permission operations.
- Cortex MCP: https://workspace.socra.com/docs/cortex/reference/mcp — `https://cortex.socra.cloud/mcp`, OAuth protected-resource metadata, issuer `https://oauth.socra.cloud`; hosted MCP is a separate transport choice.
- Socra OAuth overview: https://cloud.socra.com/docs/oauth — registered clients belong to a Cloud Project; tokens are Account-scoped; an Account-owner installation/consent and client-credential exchange can produce an installation token. Scopes must correspond to enabled services.
- Security: https://workspace.socra.com/docs/cortex/administration/security — each host maintains its own grant. ChatGPT connector authorization is not GitHub Actions authorization.

**Correction to older blocker language:** Provider API documentation exists. What remains unverified is *this repository's* authorized runner client/installation, exact OAuth token request/response contract, scoped effective grants and fresh authenticated hosted reads. Do not confuse the unrelated `cortexbanking.com` service with Socra Cortex.

## Proposed manual-only, read-only host proof

1. Owner securely provisions an appropriately scoped Socra Cloud Project OAuth client and Account-approved installation using Socra's official documentation. Confirm actual grant type, token endpoint parameters and installation identity from provider contract; do not assume that a Web client used for ChatGPT can act as an unattended service client.
2. Store any required client secret/installation identifiers only in approved GitHub Actions secret storage. Never commit or print credentials, bearer tokens, refresh tokens or token responses. Do not grant write/admin permissions for a read-only proof.
3. A separately reviewed manual-only runner obtains a fresh Account-scoped access token using the provider-supported flow. Verify its own principal and effective `module.view` grant via the documented Cortex access endpoint; a successful response body alone does not attest identity.
4. Read the exact pre-existing synthetic fixture and its version/content/source provenance through the documented read endpoint. Match exact module ID and name; reject stale versions, incomplete pagination/inventory, mismatches, unexpected redirects and unexpected response schemas.
5. Produce a zero-write, bounded, redacted evidence receipt with run/job reference, principal reference, provider source revision, module ID/version, reads/writes, provenance result and independently verifiable readback. Do not label this a CP05 PASS until both host authorization and receipt are independently confirmed.

## Existing code to reuse

- `src/nexus_sandbox/cp05_cortex_reader.py`: injected authenticated reader interface.
- `src/nexus_sandbox/cp05_host_evidence.py`: shape-only evidence validator, **not authentication**.
- `src/nexus_sandbox/cp05_cortex_callback.py` and `src/nexus_sandbox/cortex_tools.py`: operator-mediated callback history, not unattended runner credentials.
- `docs/cortex-c05-live-result.json` and `docs/cortex-c11-live-result.json`: historical synthetic live results; do not replay stale fixtures or infer remote fencing.

## Fail-closed controls

No scheduled workflow, automatic OAuth registration, new client secret, unreviewed live REST implementation, mutations, CP05/CP09 closure, or permission promotion. Inability to verify the installation's OAuth flow or effective runner grant is `BLOCKED_HOST_AUTH`, not a synthetic success. See Issues #91 and #144.
