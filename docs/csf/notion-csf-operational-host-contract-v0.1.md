# Notion → CSF operational host contract (Issue #191)

**Status:** adapter and CLI implemented; no authenticated automatic host dispatch proven. This document is an integration contract, not an execution receipt.

## Required real input
The trusted Notion reader fetches the canonical page `4088c067-daa4-813b-b1f0-e1f1993120fb`, extracts the complete single RAW-001 fenced text segment without rewriting whitespace, and independently checks the page's last-edited timestamp and account/workspace identity. The original user-supplied text is **not** verified against the source video's audio.

The reader constructs a local JSON envelope containing exactly:
- `source_url`: `https://app.notion.com/p/4088c067daa4813bb1f0e1f1993120fb`
- `source_revision`: the last-edited timestamp returned by the authenticated Notion fetch
- `document_id`: `notion:4088c067-daa4-813b-b1f0-e1f1993120fb`
- `transcript`: complete RAW-001 text, without transformation
- `expected_sha256`: lowercase SHA-256 of the exact UTF-8 transcript bytes, computed **by the trusted reader** before processing

The reader must reject incomplete/paginated/truncated page content, missing RAW-001, multiple conflicting raw blocks, missing identity or ambiguous source revision. No secrets or raw transcripts should be printed in CI logs or attached to public PRs.

## Processing boundary
Run `python3 tools/prepare_csf_notion_intake.py --source-envelope /secure/source.json` in a pinned Nexus checkout. This validates the digest, creates deterministic segments and prints a JSON receipt. The current receipt includes full segments, so treat stdout as **sensitive transcript content**: capture to a restricted artifact store, not public logs. The source envelope and stdout must be kept out of Git history and untrusted artifacts. The CLI itself has no Notion, Gemini, Cortex or GitHub write privileges.

An orchestration worker must record: event ID, source page/revision/hash, checkout SHA, workflow run/job ID, authorized caller, timestamp, result digest and independently checked artifact readback. Persist the event intent before any downstream write, reconcile uncertain outcomes, and enforce single-worker execution until CP09 fencing is implemented.

## Two consumers after one intake
1. Existing Nexus transcript-processing path may extract tasks and metadata; Notion remains the canonical raw archive.
2. CSF path consumes the source-bound segments, and later a separate authorized Gemini reviewer may **propose** candidates. Unreviewed candidates are not established facts. The Cortex destination is derived output only and requires the separate guarded live adapter in #183.

## Acceptance
- A CI-green PR proves offline implementation only.
- A real read-only operational milestone requires a genuine source event, authenticated read, pinned checkout, validated source receipt, durable artifact and independent readback.
- Real Notion/Cortex writes, Gemini calls and Foundation Audit gate closure require their own independently evidenced approvals. No additional audit gate passes are claimed here.
