# CP05 supervised read receipt contract (draft)

This is a **shape and fixture binding verifier**, not a provider authentication
verifier. It does not read Notion or Cortex, dispatch workflows, or grant permissions.

To prepare a receipt for later independent review, record:
- `schema`: `NEXUS_CP05_SUPERVISED_READ_V1`
- `mode`: `READ_ONLY`
- `attestation`: `NOT_ATTESTED`, `SOURCE_MATCHED`, or `BLOCKED`
- `notion_page_id`: `40e8c067-daa4-8199-9f12-c9b6486de444`
- `cortex_module_id`: `module_01m6kzebbfdk4ptbsg88gsf0ja`
- `fixture_payload_sha256`: SHA-256 of exact UTF-8 synthetic phrase
  `The copper lantern stays lit at dawn.`
- `source_last_edited_at`: fresh provider-reported UTC timestamp, not the
  manually authored `fixture-r1` label
- `github_run_id`, `github_job_id`: **actual** hosted run identifiers
- `provider_writes`: 0

Use `python3 tools/cp05_supervised_receipt_verify.py receipt.json`.
The validator fails closed on missing fields, invalid bindings, nonzero writes,
or unearned attestation labels. The digest here is only the **fixture phrase**
digest; it is **not** a digest of the full Notion block inventory or Cortex
module. No test run, full provider readback, authenticated Cortex host identity,
or CP05 gate promotion is claimed by adding these files.

Before any acceptance, separately retrieve and verify the run's original
artifact and logs, confirm provider principal/grants, obtain a full source
inventory digest and revision reconciliation, and independently re-read the
Cortex target. A missing artifact is a BLOCKED acceptance condition.
