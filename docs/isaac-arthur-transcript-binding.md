# Isaac Arthur transcript binding for unattended Cortex pilot

Review candidate for [issue #202](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/202). Activation requires the evidence below.

| Field | Expected value |
| --- | --- |
| Notion page | `4178c067-daa4-81fc-bef3-e9f310a0b65a` |
| Title | Life As A Planetary Governor |
| Video ID | `RfD1fOoRl3s` |
| Source | RAW v1, four numbered chunks, 42,075 UTF-8 bytes, joined without separators |
| Source SHA-256 | `54b14c492fffa2a046292132a84b486f28719f87777c2a1f8a93ec0239d095c0` |
| Notion transfer status | Pending Cortex Processing |
| Chat Notion revision | `2026-11-13T13:47:13.023Z` |
| Runner Notion REST revision | Pending authenticated runner observation |
| Proposed Cortex destination | `Nexus Analysis — 4178c067-daa4-81fc-bef3-e9f310a0b65a — 54b14c492fffa2a046292132a84b486f28719f87777c2a1f8a93ec0239d095c0` |

Connected Chat reassembled the four Notion chunks and recomputed each chunk checksum and the combined checksum. Searches across visible active and archived Cortex records by title, video ID, page ID and checksum returned no matches.

## Activation and acceptance

1. Use the pilot runner's current Notion credential for a read-only observation of the exact page. Capture the REST revision, source fidelity, pending status and repeated metadata read. Treat any source mismatch or access failure as a blocker. Use the observed REST revision as the runner pin after review.
2. Verify the background Chat runtime can enumerate native scheduled runs, download and verify the actual source-ready ZIP, and reach Cortex. Keep write activation paused until review and runtime checks pass.
3. Require a successful native scheduled run on main for this binding. Match event, run ID, attempt, commit, ZIP digest and source fields. Independently recheck Notion and resolve the proposed Cortex destination and any source-bound matches before creating.
4. Create one source-bound analysis through the scheduled Chat runtime. On collision or uncertain outcome, reconcile by exact destination and source identity before any retry. Independently read back the stored analysis and verify its source binding. Replay the same handoff and require zero additional writes.
5. Record the run, artifact, independently attributable background execution, Cortex module and replay evidence on issue #202. Advance acceptance only when the full receipt is verified.
