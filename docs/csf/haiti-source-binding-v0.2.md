# Haiti CSF pilot — source binding and review handoff (read-only)

Status: **SOURCE LOCATED; REAL INGESTION NOT EXECUTED; GATE C PENDING**.
This file is a source manifest, not an extracted findings artifact or a Cortex write.

## Archived original
- Notion page: https://app.notion.com/p/4088c067daa4813bb1f0e1f1993120fb
- Page ID: `4088c067-daa4-813b-b1f0-e1f1993120fb`
- Transaction: `NXS-LIVE-TRANSCRIPT-RAXLnCNA4w8-20261029`
- Original source: https://youtu.be/RAXLnCNA4w8?is=pr485_E5dd_PJf6V
- Archive manifest: `RAW-001`, 20,152 UTF-16 code units; first marker "In the Caribbean nation of Haiti", last marker "Thank you for watching."
- Source says archival status `WRITE_SUBMITTED` and readback comparison pending; a separate Notion analysis page reports a complete 20,152-code-unit readback match. Preserve the discrepancy until an independently reproducible fresh readback.
- **No canonical UTF-8 SHA-256 digest established by this handoff.** Do not substitute a digest of a shortened excerpt or reformatted Markdown.
- User-supplied text, not a new audio transcription. Audio completeness and accuracy unverified.

## Existing derived Notion analysis (not CSF findings)
- https://app.notion.com/p/4088c067daa481a5bb0bf62e5ea3339b
- Existing claim register HAI-01 through HAI-06 distinguishes reported incidents, changing deployment estimates, mandate uncertainty, capacity gaps, incentive hypotheses, and geography.
- These are *review inputs*, not automatically promoted observations. Claims about Haiti and El Salvador require independent source corroboration, not just transcript attribution.

## Next bounded ingestion
1. Read the full `RAW-001` text, preserving exact source bytes/code points; verify archival readback and capture exact SHA-256 over UTF-8 text.
2. Use stable segment IDs that map back to the original source (currently the archive describes one segment `RAW-001`). Any derived paragraph segmentation must retain the mapping to `RAW-001` and offsets.
3. Create a small set of explicit candidate classifications with direct quotations or bounded references, marking source claims as *claims made in the video* rather than independently established events.
4. Validate CSF schema, referential integrity and idempotency offline; save the resulting artifact with digest and commit binding.
5. Submit that frozen artifact to Gemini for an independently evidenced **analytical** review; code-diff review run 42285059218 is not sufficient.
6. Obtain owner Gate D approval before any Cortex write. Existing Cortex module ID/revision and archived transcript link remain unverified.

## Gate status
A/B/E: synthetic CI green on commit `6a69933` (runs 42285429947 and 42285429905); real-source integrity and cross-run persistence unverified.
C: not performed on real findings.
D: not authorized.
