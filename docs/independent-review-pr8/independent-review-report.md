# Independent AI review: retained identity history safeguard

Reviewer: `/root/independent_identity_review`, a separate AI review agent. I did not implement PR #8. This is independent AI review and local test reproduction, not an independent human audit, hosted isolation audit, or production signoff. My earlier review of `618681f` remains historical and is not overwritten by this report.

## Scope and recommendation

Reviewed frozen revision: **`4b396f64b1b1174a9f3da0366a82a530453067e9`**, repository `sovereignmystic92-dot/nexus-v3-sandbox-`. Baseline adapter for contrast: `ae22d1ccc1f1dc731fbca250a06475f6830d1025`. I independently fetched and read the review handoff appended to PR #9.

**Accept the narrow retained-record identity safeguard under its documented trusted-journal, single-worker assumptions.** I found no blocking defect that changes a retained first durable VERIFIED create identity or immutable update before-ID within that scope. The missing/inconsistent-record stops, trusted legacy backfill, atomic persistence and ordinary uncertainty reconciliation passed independent reproduction. One low-severity hardening observation remains below; do not expand the claim into validation of every event's schema or complete history integrity.

Full foundation acceptance remains **BLOCKED**. Human review remains open. No live service action, production activation, canonical promotion or concurrency support follows from this recommendation.

## Source provenance and inspection

I fetched 26 frozen files through connected GitHub read tools into the new directory `/workspace/scratch/2fcd5a9b3883/independent-review-4b396f6`, without using the author's working copy. All 26 local Git blob hashes match the frozen tree (`fetched-manifest.json`, `local-blob-checks.json`). The separately fetched baseline adapter and current status document were also verified against their Git blob hashes. `extra-source-metadata.json` records their revisions/hashes and independently checked subtree IDs: `src`, `tests`, `tools`, and `.github` are identical between the frozen target and main `9a59bb7c920d7ca349faf4d3aef4cf207b3a8502`.

I inspected the full adapter, bridge, adapter/bridge test file, workflow, isolated runner, local validator, and adapter contract: `src/nexus_sandbox/cortex_adapter.py`, `cortex_tools.py`, `tests/unit/test_cortex_adapter.py`, `.github/workflows/synthetic-acceptance.yml`, `tools/run_isolated.py`, `tools/validate.py`, `docs/cortex-adapter.md`. I read `docs/foundation-audit-status.md` from `9a59bb7...` because that document does not exist at the frozen implementation revision. It is retained locally as `current-foundation-audit-status.md`, explicitly attributed to its later revision. Other suite dependencies were fetched to reproduce tests; that is not a claim of new line-by-line review of every repository file.

I changed no author source, remote repository, Cortex or Notion state. I sent no external review/comment/message and ran no live probe or callback. Only local review scripts, synthetic databases and evidence were written.

## Actual local results

Python: `3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3]`. Platform: `Linux-6.18.55-x86_64-with-glibc2.39`. Commands ran from the fresh directory with `PYTHONPATH=src:tests/unit`.

| Command | Actual result | Raw output |
| --- | --- | --- |
| `python3 tools/validate.py --output reviewer-validation.json` | Exit 0; 63 distinct tests passed; full acceptance BLOCKED | `reviewer-run-0.txt` |
| `python3 -m unittest discover -s tests/unit -v` | Exit 0; 63 passed, 0 failures/errors/skips | `reviewer-run-1.txt` |
| `python3 -m unittest -v` with the seven PR #9 regression IDs | Exit 0; 7 passed, 0 failures/errors/skips | `reviewer-run-2.txt` |
| `python3 reviewer_probes.py` | Exit 0; 12 independent cases passed their stated assertions; 0 failures/errors/skips | `reviewer-run-3.txt` |
| Same seven regression IDs with prior adapter in another temporary copy | Exit 1; 5 assertion failures and 2 missing-table errors; 0 skips | `reviewer-baseline-output.txt` |

The baseline contrast combines only the prior `cortex_adapter.py` with the frozen target's remaining source and tests. It is not a full baseline-suite run. That temporary copy was deleted after execution. Repeated suite and targeted runs overlap and must not be added as distinct coverage. The new probes also reuse the supplied FakeCortex/setup while adding independent actions and assertions.

`reproduce_review.py` preserves the reproduction driver. `reviewer-commands-results.json` records exact argument arrays/runtime/return codes. `reviewer-validation.json` records the full suite's per-case statuses and source SHA256 manifest. `reviewer-probes-results.json` records independent per-case outcomes and identifies cases demonstrating limitations. `reviewer-targeted-results.json` records targeted/baseline outcomes parsed from their raw unittest output.

## Findings

**No blocking identity-safeguard defect found.** In adapter lines 112–131, first VERIFIED anchor insertion, latest receipt and event occur inside one SQLite transaction. Identity mismatch or insert failure cannot return VERIFIED. Lines 152–191 check retained events/receipt and anchor before transport, bind updates to `before.id`, and commit trusted legacy backfill before reads. Latest receipt comparison uses decoded JSON, so irrelevant whitespace/key-order changes do not cause a false integrity hold.

The seven supplied regressions independently reproduce missing history with both original/replacement targets, trusted restore, latest receipt/event divergence, loss of earliest verification while a conflicting later identity survives, legacy migration, anchor insert failure, and orphaned records. My additional tests confirm anchor-only orphans, legacy receipt with no events/anchor, and anchor-ID disagreement stop before any transport access. Update history loss now holds before transport even though its before-ID is available; restoring the exact saved events permits read-only verification, with writes unchanged.

**Atomicity and recovery confirmed in additional fault injections.** I aborted the VERIFIED event insertion after anchor insertion would have occurred: anchor, verification receipt and event rolled back together, leaving the earlier WRITE_INTENT and one event. Removing the trigger let the same request reconcile to VERIFIED with one total create. Separately, I removed the anchor to model legacy migration, then denied anchor insertion: ensure raised before any transport read, left no anchor, and resumed without another create once the trigger was removed. Pending write intent without any VERIFIED anchor remained eligible for ordinary read-only reconciliation after the supplied synthetic process-stop condition.

**Low severity — event schema validation stops at the first VERIFIED event.** `_journal_identity` parses all event JSON, but lines 165–172 stop the dictionary/schema walk at the earliest VERIFIED event. My `test_boundary_nonobject_event_after_first_verification_is_not_validated` appends a JSON array event `[]` after verified A, then appends a final event equal to the retained receipt. Ensure makes four transport reads and returns VERIFIED A. This does not rebind A or enable another write, and the declared guarantee is detection of specific inconsistencies rather than authenticated or complete history validation. It is therefore nonblocking for this bounded fix. However, the malformed-event check is incomplete; consider validating that every decoded event is an object before selecting the first verification, and avoid describing the current check as validating every retained event. Syntactically invalid JSON anywhere in the tail instead raises JSONDecodeError before transport, as independently tested. Such decoder errors are not normalized to JournalIntegrityError, although they still stop execution.

## Confirmed boundaries and residual risks

Two independent cases intentionally assert unsafe behavior outside the guarantee: deleting the whole database permits an identical desired-state replacement B to become VERIFIED; a create ID A read back while source change withholds first VERIFIED remains unpinned and can later become VERIFIED B. Both occurred with no additional write. Their passing assertions confirm those limitations, not their safety. The updated adapter contract now correctly states the durable-VERIFIED threshold.

Complete database replacement/loss, coherent rewriting of related records, or history selectively lost before trusted legacy migration remain undetectable. An absent anchor is indistinguishable from a legacy journal, so backfill trusts retained history; it cannot certify completeness. Checks also do not prove absence of every omitted intermediate event. Retain complete journals and independently trusted backups; restore rather than reset/compact after an integrity stop. The safeguard detects the specified inconsistent retained conditions and does not provide cryptographic authenticity or forensic integrity.

The bridge still treats only the exact observed missing-module error combination as absence; reads/acknowledgments do not bypass adapter readback. Validation restricts request keys, names, dependencies, content markers and source/baseline snapshots, while account binding, truthful synthetic classification and callback trust remain host assumptions. Dependency names are allowlisted, not recursively certified. One worker remains mandatory: no remote CAS, enforced lease/fencing, atomic multi-module snapshot, or protection from other hosts/direct callers is added.

By source inspection, the unchanged workflow has empty token permissions, exact public-source SHA checkout, and a pull-request merge-parent check against the base branch tip observed at that time. The runner checks container restrictions/manifests, requires four coordinator fault results, and reports ordinary teardown and bounded runtime retention. These are implementation observations only. I did not retrieve hosted run logs or execute Docker, container boundary probes, the four coordinator fault checks, real network outages, live Cortex calls, device/power-loss tests, or long-term durability tests. Local success must not be represented as independent reproduction of those hosted/live claims. Shared-kernel/provider trust, effective live grants, future retention/deletion, reciprocal registration, semantic mastery and human audit remain unresolved broader gates. Notion stays authoritative and paused.
