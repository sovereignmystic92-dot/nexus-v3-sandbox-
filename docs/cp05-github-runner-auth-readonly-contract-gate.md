# CP05 GitHub runner → Cortex authentication/read-only probe gate

## Verified
GitHub runner has nonempty SOCRA_CLIENT_ID and SOCRA_CLIENT_SECRET (run 42446349632). ChatGPT-connected Socra Cortex created and independently listed synthetic module `module_01m6wpwex46vvgmsq9pr4k88d5` on 2026-11-08. These are **different credential and execution contexts**.

## Required before a real runner auth probe
1. Confirm the official Socra OAuth token exchange endpoint and grant type for a GitHub-hosted, noninteractive installation. Do not infer from CLI command names.
2. Confirm scope/audience and supported API endpoint for read-only module lookup, including the exact response contract.
3. Use GitHub Actions secret environment, never echo token, client secret, raw HTTP response or credential-bearing URL.
4. Dispatch a manual, read-only workflow with minimum permissions and a short timeout. Verify installation identity and access to only the existing synthetic module ID/name; record status/hashed metadata only.
5. On missing/invalid endpoint, grant or response contract, report BLOCKED; do not attempt guessed URLs, redirect-following, write fallback, or a credential dump.
6. Require an independently reviewed, separate synthetic write workflow only after authenticated read succeeds. Never enable automatic retries or multiwriter writes while CP09 is open.

## Current disposition
**BLOCKED — authenticated runner read not yet attempted.** Existing secrets-present test is not OAuth validation. Connected ChatGPT read/write does not establish GitHub runner access. This document does not include a runnable authentication call because the endpoint/grant contract has not been independently verified.

## Audit
CP02 effective runner grants open; CP05 end-to-end runner ingestion/write/readback open; CP09 remote fencing blocked. Single-writer operation only.
