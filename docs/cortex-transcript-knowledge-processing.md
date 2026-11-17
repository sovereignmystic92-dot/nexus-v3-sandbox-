# Cortex transcript knowledge processing

Status: proposed design for an offline pilot.

## Intake and processing

1. Notion holds the original transcript verbatim. The intake step verifies the archived copy against the source and flags it as **Pending Cortex Processing**. The flag indicates readiness for pickup.
2. A separate worker picks up a bounded batch of flagged records. Bind each run to the Notion record ID, exact source checksum, and processing contract version. A changed source or processing contract is a new run. Verify source bytes before analysis and recheck the current source version before updating its Notion status.
3. Use the existing `execute_supervised` entry point with its complete `analysis_gate` for qualifying transcript processing. Verify the intended Cortex account, destination, and effective grants through the existing provider controls before any live writes. Keep transcript text and analytical payloads out of the public repository and CI artifacts.
4. Write and independently read back the three derived outputs in Cortex. After the readbacks match the intended outputs, record the receipt and update the Notion processing status for that source version. A receipt carries the source binding, output IDs and revisions, and readback results.

## Derived outputs

| Output | Contents |
| --- | --- |
| Source analysis | Claims, concepts, and assumptions. Each important assertion carries a timestamp or passage reference plus the speaker's framing, such as reported fact, opinion, or hypothesis. |
| Concept updates | Existing concept ID or proposed new concept, the prior revision where applicable, what the source adds or challenges, evidence references, and rationale. Keep source assertions distinct from cross-source conclusions. |
| Open questions | Specific unresolved question, linked concept and source references, and the evidence that would help answer it. |

Keep concept IDs stable across revisions. Preserve prior conclusions and their evidence when a new source changes the interpretation. Record disagreement as competing claims with their own provenance. Apply revisions against the expected prior revision and reevaluate against current evidence if the baseline changes.

## Retry and reconciliation

Use stable output identifiers within a run and persist intent before writing. After a timeout or interruption, read back the intended outputs and reconcile before retrying. Verify all required outputs before marking the exact source version processed. A newer source version keeps its own pending status. Missing evidence, stale baselines, and mismatched readbacks remain visible in the receipt. Start with a single worker.

## First Codex implementation

Add an offline contract for the source binding, evidence references, three derived output types, and completion receipt. Use synthetic inputs and the existing supervised workflow for the implementation boundary. Reuse the repository's existing validation and reconciliation contracts where they cover the same behavior.

The pilot uses two overlapping synthetic transcripts. The first establishes a concept, and the second adds or challenges it. Verify that both contributions remain traceable, a repeated run creates no duplicate outputs, a stale concept baseline cannot overwrite a newer revision, and a partial write cannot produce a completion receipt. Include recovery after readback succeeds but the status update is interrupted.

Live activation is a separate milestone after the offline contract passes and provider authorization and readback are demonstrated for the intended destinations.
