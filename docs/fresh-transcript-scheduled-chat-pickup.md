# Scheduled Chat pickup — existing-output replay

This candidate is restricted to read-only source verification and reuse of the existing Cortex analysis. Keep the Chat readiness task paused during review. A fresh unattended write requires a separate reviewed binding to the pending Isaac Arthur candidate.

## Exact source and existing output

- Notion page: `4188c067-daa4-8134-9cda-f30c901aa875`.
- Video: `bEjwo1yUK8c`, Matt Madigan, Alien Technology Just Arrived.
- RAW v1: four chunks, 21,528 UTF-8 bytes, joined without separators.
- SHA-256: `f2122b71e7762479e026c7f4614378526410f1560bd560e1eadc03d6f0d2e0c8`.
- Exact REST `last_edited_time`: `2026-11-15T17:34:00.000Z`.
- Chat connector observation: `2026-11-15T17:34:35.196Z`. Preserve this separately. It cannot satisfy the REST revision check.
- Existing Cortex module: `module_01m7dte8edyhqkykrtzmczdjm9`.
- Existing exact name: `Nexus Analysis — Alien Technology Just Arrived — Matt Madigan — bEjwo1yUK8c — RAW v1`.
- Supervised receipt: [issue #202, comment 6883422224](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/202#issuecomment-6883422224).

## Replay procedure

1. Inspect the deployed `.github/workflows/nexus-fresh-transcript-pilot.yml` and verifier at the native scheduled run's exact commit on main. Require the corrected REST pin. Record run ID, attempt, commit, event and artifact ID. PR validation and manually retried runs cannot establish a new native scheduled execution.
2. Download the source-ready ZIP, verify its published digest, and inspect `source-ready.json`. Require SOURCE_READY, event schedule, matching run/attempt/commit, the exact page ID, REST revision, digest, 21,528 bytes and video ID above. The current artifact's `destination_module` value is the legacy proposed name `Nexus Analysis — 4188c067-daa4-8134-9cda-f30c901aa875 — f2122b71e7762479e026c7f4614378526410f1560bd560e1eadc03d6f0d2e0c8`. Verify that field as artifact identity only. Resolve Cortex through the existing module ID and name above.
3. Independently read all four archived chunks and recompute their combined UTF-8 digest and byte count. The runner requires the archive's literal pending flag as a source-state assertion. That flag is stale relative to the supervised completion receipt and provides no authorization to create another analysis. Compare REST timestamps only with REST observations. Record the Chat connector timestamp separately, and stop if its observation differs from the separately recorded connector value.
4. Retrieve the existing Cortex module by exact name and confirm its native ID, source page, RAW v1 digest and complete saved analysis. Search by page ID and video ID and reconcile any competing output. Missing, ambiguous or mismatched output is a blocker requiring investigation. This procedure has no create or update branch.
5. Read the existing GitHub supervised receipt and match the source and module identities. Report this run as source verification and existing-output replay. Record any missing evidence and stop. A successful replay earns zero fresh unattended ingestion credit.

## Runtime checks and acceptance order

The verifier fetches metadata and child blocks from `https://api.notion.com/v1/` using Notion API version 2022-06-28. It checks exact metadata string equality against REVISION, complete child coverage, ordered chunk headings, four chunks, the literal pending flag, UTF-8 byte count and the full SHA-256. It reads page metadata again after verification and requires the same exact REST revision before writing the local metadata artifact. The script and scheduled workflow perform Notion reads and artifact publication. Cortex lookup/replay belongs to the separately invoked Chat controller.

Scheduled run [44230859690](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/44230859690) observed the REST timestamp above. Independent Chat readback reassembled the archived bytes and matched their checksum. A successful post-fix native scheduled run remains an acceptance step after the reviewed fix reaches main. Code merge, scheduled source verification, replay verification and fresh unattended ingestion are recorded as separate outcomes.

Rollback is to revert this PR's commits. Keep the readiness task paused until a separately reviewed activation scope is satisfied.
