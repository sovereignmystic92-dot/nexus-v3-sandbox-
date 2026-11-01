# Transcript ingestion checkpoint coordinator (draft)

This change adds an **offline durable state machine**, not a deployed integration. It does **not** call the Notion, Cortex or GitHub APIs, create credentials, execute background jobs, or intercept ChatGPT connectors. Do not represent its test results as live-provider validation.

## Minimal host contract

1. Capture the entire raw transcript without truncating or silently repairing words. Persist raw text in an authoritative source archive; provide immutable video ID and exact text to `receive(video_id, raw_transcript)`.
2. Archive original text in Notion in numbered chunks if necessary. To mark `NOTION_ARCHIVE_VERIFIED` as `COMPLETE`, independently fetch all parts, reconstruct their original order, and compare the full raw SHA-256 with the intake hash. Put the destination and a stable external readback reference into the evidence. A summary-only record MUST be `PARTIAL`.
3. Extract separate source claims, independently verified facts, inferences, hypotheses and gaps. Mark `ANALYSIS_COMPLETED` complete only after reading back the persisted analysis artifact; a local draft may remain partial.
4. Save derived knowledge to Cortex with a link to the Notion source. Independently search/fetch and compare the persisted record before completing `CORTEX_OUTPUT_VERIFIED`.
5. Attempt a GitHub or other designated durable execution receipt, then fetch it independently before marking `RECEIPT_RECORDED` complete. On write failure, record `BLOCKED` and retry that stage only.

`next_stage` always returns the first stage not independently verified complete. For each stage `record` takes `independently_read_back=True` only when the host has actually checked the external effect. It is a trust boundary: this local library cannot independently authenticate the provider response or caller. No `COMPLETE` claim is justified by that argument alone; include provider receipt IDs and content digest comparisons in evidence.

## Retry and integrity

- `youtube:<11-character-id>` is the idempotency key.
- A duplicate ID with different raw text is rejected, not overwritten.
- Earlier verified stages cannot be downgraded or silently replaced by a later retry.
- Completed downstream checkpoints require verified upstream completion.
- Durable SQLite allows restart recovery on the same volume.
- `PARTIAL` and `BLOCKED` are journaled but never treated as success.
- This code does not yet implement cross-provider transaction fencing, lease ownership, timeouts, or encrypted provider secrets. A scheduled host must supply those controls before claiming unattended or production readiness.

## Run offline unit tests

From repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests/unit -p 'test_transcript_ingestion.py' -v
```

Run full sandbox validation independently before merge:

```sh
python3 tools/validate.py --output local-validation.json
```

This PR intentionally contains no external write credentials, workflow schedule, or production configuration. **Foundation status remains 13/19.** Socra Cloud runtime installation remains a separate unresolved dependency.
