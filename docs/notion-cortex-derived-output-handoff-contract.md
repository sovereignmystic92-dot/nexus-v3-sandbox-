# Nexus Notion → Cortex derived-output handoff contract

Status: PROPOSED / NOT AUTOMATICALLY DEPLOYED. This documents the verified manual Haiti pilot and acceptance criteria for a future guarded adapter.

## Storage and destination
- Notion remains canonical for the **complete, unmodified original transcript** and provenance.
- Cortex receives **derived analysis only**, not a duplicate raw transcript; retain direct canonical links to Notion source and analysis.
- Bind the intended Cortex account, effective caller, and destination module namespace **before** writes. A connected account ID alone does not prove project selection.
- Never infer cross-account absence from a single account registry. Require explicit destination confirmation.

## Preflight and idempotency
- Stable transaction key: `NXS-LIVE-TRANSCRIPT-RAXLnCNA4w8-20261029`; original video ID `RAXLnCNA4w8`.
- Read source and analysis in Notion; verify links and source version. Search target Cortex registry for exact transaction key, video ID, source URL, and output title; exhaust pagination.
- If a matching module exists, inspect it and reconcile instead of creating another. If multiple matches, uncertain ownership, wrong account, or conflicting contents: STOP and escalate; do not overwrite.
- If absent in confirmed destination, perform **one authorized create**, recording the module ID, caller, timestamp, source revision, and resulting version. No automatic retry after ambiguous write result; first reconcile with a fresh read.

## Readback and acceptance
- Independently fetch the newly created Cortex module; check ID, exact transaction key, canonical Notion links, content, version, and owner/destination.
- Record separate outcomes for: Notion source fidelity; Notion analysis; Cortex write; Cortex readback; guarded adapter authorization; automatic trigger; reviewer identity; independent source/audio comparison.
- A manual connector call does NOT count as guarded-adapter execution or an automated live acceptance run.
- On failure preserve original Notion content, emit a failure record, and stop. Do not silently reprocess, duplicate, or promote audit gates.

## Haiti pilot evidence (manual only)
- Notion transcript: https://app.notion.com/p/4088c067daa4813bb1f0e1f1993120fb
- Notion analysis: https://app.notion.com/p/4088c067daa481a5bb0bf62e5ea3339b
- Cortex module: `module_01m6s0gjt99920pps5bmrg7rg2`, version 1, visible in connected account after manual creation on 2026-11-06.
- Audio accuracy and independent full transcript diff: NOT VERIFIED. Automatic adapter dispatch: NOT RUN. Live acceptance: 0/5.
- This pilot does not establish the destination project identity independently; do not extrapolate its permission scope to production.
