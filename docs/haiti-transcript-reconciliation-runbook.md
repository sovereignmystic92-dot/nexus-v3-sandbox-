# Haiti transcript reconciliation — source-bound runbook

Status: **NOT ACCEPTED / REVIEW_REQUIRED**. This runbook does not authorize any source write, Cortex creation, or live gate promotion.

## Source anchors (read back 2026-11-06)

- Original archive: Notion page `4088c067-daa4-813b-b1f0-e1f1993120fb`, RAW-001 fenced `txt` content, 20,152 UTF-16 code units at last edit `2026-10-29T23:44:29.194Z`. These markers are NOT an exact-match proof against the original user message.
- Independent candidate: `https://podcastrex.com/shows/warfronts/el-salvador-has-invaded-haiti-heres-what-you-need-to-know/transcript`. End the main episode at the **first** `Thank you for watching.`, not subsequent podcast advertisements.
- The provider returned HTTP **403 Forbidden** to an automated GitHub Actions fetch. Do not bypass this restriction, silently substitute another source, or claim successful audio verification.

## Authorized offline path

1. Obtain a **permitted complete export** of the independent transcript, documenting its origin and retrieval method. If no permitted export is available, STOP with `CANDIDATE_UNAVAILABLE`.
2. Export only the RAW-001 original text (without Notion Markdown fences) as UTF-8 bytes to `notion-raw.txt`, documenting the page ID and revision. Keep the canonical Notion archive unchanged.
3. Save the complete independent candidate exactly as exported to `candidate.txt`. Do not silently normalize punctuation, whitespace, or line endings. Verify that it begins with the episode and ends at the first main-episode closing line.
4. On an authorized runner with the repository code checked out and `PYTHONPATH=src`, run:

```bash
python -m nexus_sandbox.warfronts_source_transfer \
  --notion-raw-file notion-raw.txt \
  --candidate-file candidate.txt \
  --candidate-provenance 'manual:podcastrex-permitted-complete-export' \
  --report haiti-diff.json
```

5. Independently review the two SHA-256 digests, UTF-16 lengths, exact-equality flag and **all** non-equal word spans. The comparator does not certify audio accuracy and does not distinguish ASR errors from editorial differences.
6. Retain report and source provenance under approved storage policy. Do **not** upload full copyrighted transcript text to public GitHub issues, logs, PRs, or artifacts. Report only bounded discrepancy evidence and hashes.
7. Confirm source archival readback and separately prove the authorized Cortex record linkage before considering a live acceptance run. No duplicate Cortex modules.

## Failure gates

- Candidate unavailable, incomplete, or source unclear: **STOP**.
- Archive extraction ambiguous or modified: **STOP**.
- Missing source provenance or reused provenance: **STOP**.
- Public endpoint returns 403: **STOP**, do not retry with evasion.
- Successful offline comparison: **REVIEW_REQUIRED_NOT_AUTHORIZED**, not live acceptance.
- Nexus live end-to-end acceptance remains **0/5** until five independent fully evidenced runs are completed.
