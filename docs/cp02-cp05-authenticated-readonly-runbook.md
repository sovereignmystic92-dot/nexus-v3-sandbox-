# CP02 / CP05 authenticated read-only verification runbook

Date: 2026-11-08 UTC. Purpose: move from secret-presence assumptions to bounded identity and fixture readback. This runbook **does not grant access**, change secrets, authorize writes, or close CP02/CP05.

## Existing workflows — no new provider adapter

1. **Socra runner credential presence**: [cp05-socra-credential-preflight.yml](../.github/workflows/cp05-socra-credential-preflight.yml). Manually dispatch on `main`. It checks `SOCRA_CLIENT_ID` and `SOCRA_CLIENT_SECRET` are nonempty in the runner and explicitly does **not** attest validity, installation identity, effective grants, or Cortex access. Do not print secret values. An environment-scoped secret may not be visible to this job; absence is not proof no credential exists.
2. **Notion token principal identity**: [notion-token-identity-read.yml](../.github/workflows/notion-token-identity-read.yml). Manually dispatch on `main` with `identity_confirmed=true` only after operator approves one identity-only read. Uses `notion-sandbox` environment and `NOTION_SANDBOX_TOKEN`; no transcript reads or writes. Record run ID, head SHA, job result, returned principal/installation metadata (nonsecret only), and scope limitations.
3. **Notion synthetic fixture readback**: [cp05-authenticated-notion-fixture-probe.yml](../.github/workflows/cp05-authenticated-notion-fixture-probe.yml). Manually dispatch on `main` with `read_confirmed=true` only after operator approves one read. It checks exact fixture page `40e8c067-daa4-8199-9f12-c9b6486de444` and expected synthetic marker `The copper lantern stays lit at dawn.`. Record exact run/job status, page identity, last edit timestamp, block count, digest, and zero writes. Fixture matching does **not** prove original transcript preservation or Cortex persistence.

## Interpretation

- A workflow being present or a job being skipped is **not** a pass.
- A nonempty secret is **not** a validated OAuth client or effective grant.
- A Notion token identity read is **not** a fixture readback.
- A fixture readback is **not** a Cortex installation identity check or a provider write/readback.
- A GitHub receipt artifact verifies GitHub durability only; run [42444882398](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/42444882398) is the bounded evidence.
- No provider writes, autonomous dispatch, credential changes, or production promotion are authorized by this runbook.
- CP02 and CP05 remain **OPEN** until required acceptance criteria and independently verified evidence are documented.

## Evidence record to append per run

```text
workflow:
run_id:
head_sha:
job_conclusion:
authorized_input:
authenticated_principal_nonsecret:
effective_grants_attested: yes/no
fixture_page_id_and_digest:
provider_writes: 0
limitations:
reviewer:
```

## Next implementation decision

If Socra preflight reports only credential presence, do **not** convert that to an OAuth success claim. Determine the documented token exchange and safe identity endpoint from authoritative Socra material before adding an identity-only runner. Fail closed if the exchange or installation principal cannot be independently verified. Keep Cortex writes disabled.
