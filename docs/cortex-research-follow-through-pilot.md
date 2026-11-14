# Cortex research follow-through pilot

Proposed addition to the existing hourly Nexus Automation Readiness task. Review against issue #201 before applying it. The pilot measures background research and Cortex readback. It does not count toward the unattended transcript-ingestion acceptance runs.

## Proposed prompt addition

> For this pilot only, process Cortex issue `issue_01m7axybngmb0y0a1nhave3sze` on module `module_01m7ahp87wtnyervxgtwq1enhy` (Nexus Analysis — 5th Generation Warfare — Dirty Civilian — M1nBemfznkA — RAW v1) using Chat's connected Cortex account. This instruction is limited to the cited research addendum and status or blocker on that exact issue. Keep the existing cadence and all existing handoff, credential, and audit limits for other work.
>
> Read the issue and owning module. Verify the module ID and source binding to Notion page `4168c067-daa4-8111-bda6-ef07325583ed`. If the issue is closed, skip it. If the module already contains the exact issue ID and a complete cited addendum, independently read it back and reconcile the issue without another module write. If an existing addendum is incomplete or ownership is ambiguous, retain the blocker for supervised reconciliation.
>
> Compare two or three peer-reviewed sources, including an online headline experiment, on how repeated exposure affects perceived accuracy. Capture the study population, what was repeated, the outcome measured, and differences and limits across studies. Distinguish perceived accuracy from durable belief, real-world behavior, and evidence of coordination. Record stable source links and a concrete condition for revisiting the finding.
>
> Verify current edit access and ensure this scheduled task is the only writer for this pilot. Immediately before appending, re-read the module and check its version, content, and issue marker. If concurrent or uncertain writes cannot be reconciled, stop and record the exact blocker. Append only the research addendum, including the issue ID. Independently fetch the module after the write and verify its identity, preserved source binding, and exactly one matching addendum. Only then close the issue and verify its status. On failure preserve the failed step, observed reason, and next corrective action in the issue or existing task result if Cortex is inaccessible. Keep raw transcript content in Notion.
>
> Report the issue ID, Cortex module ID and readback result, and the background execution receipt when available. Report a launch requested through Run now as a manually launched background pilot.

## Acceptance

- A background execution reads the existing issue and produces a cited update to the named module.
- Independent Cortex readback confirms the addendum and source binding and the issue closes with a reopening condition.
- A subsequent check recognizes the completed issue or existing addendum and creates no duplicate.
- Missing connector access, grants, or execution evidence remains visible as a blocker.
