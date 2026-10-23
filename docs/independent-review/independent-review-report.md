# Independent AI review of the bounded Cortex identity fix

Reviewer: `/root/independent_identity_review`, a separate AI review agent. I did not implement the patch. This is independent AI code review and local test reproduction, not an independent human audit or production signoff.

Repository: `sovereignmystic92-dot/nexus-v3-sandbox-`. Reviewed frozen revision: `618681fdc6d1767358cca993e857f68fd2202879`. Review packet: `docs/independent-review-packet.md` at `8cf1803df28c07ec5a1a2f8006b2b0d7e5f8564e`. Baseline adapter: `ce7ad5e8bf1f5b968e6cd9334b91716f90ad76ed`.

## Recommendation

Accept the bounded correction to the **first VERIFIED create identity / immutable before-ID update identity** claim, assuming complete, trustworthy journal history and one worker. No blocking implementation defect was found within that scope. The four supplied regressions independently fail with the baseline adapter and pass with the frozen merged adapter. The broader foundation audit remains BLOCKED. No concurrency/fencing, human audit, full live permission isolation, production acceptance, or live integration claim is established here.

## Materials and provenance

I fetched the packet and frozen files through the connected GitHub read tools into a new directory, without using the author's working copy. `fetched-manifest.json` records 27 source/test/tool/config/document blobs. `local-blob-checks.json` confirms all 27 local files match the frozen Git blob SHAs. The baseline adapter separately matches Git blob `65ae2404d10c20525d1677c93cb021e0ac7817f1`.

I inspected the full `src/nexus_sandbox/cortex_adapter.py`, `cortex_tools.py`, `coordinator.py`, `tests/unit/test_cortex_adapter.py`, `test_runner_boundary.py`, `tools/validate.py`, `run_isolated.py`, `container_probe.py`, `fault_checks.py`, `fault_worker.py`, `.github/workflows/synthetic-acceptance.yml`, `docs/cortex-adapter.md`, and `docs/implementation-review.md`, plus the review packet. Fetching other suite dependencies is not a claim of line-by-line review of every file.

No repository/remote modification, GitHub review/comment, Cortex or Notion access, live callback, or live probe execution occurred. All added tests and evidence are local temporary review artifacts.

## Actual reproduction

Directory: `/workspace/scratch/2fcd5a9b3883/independent-review-618681f`.

Runtime: Python `3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3]`; `Linux-6.18.55-x86_64-with-glibc2.39`. All unittest commands used `PYTHONPATH=src:tests/unit`.

| Command | Actual result | Output |
| --- | --- | --- |
| `python3 tools/validate.py --output reviewer-validation.json` | Exit 0; 56 distinct tests passed; 0 failures/errors/skips; full acceptance BLOCKED | `reviewer-run-0.txt`, `reviewer-validation.json` |
| `python3 -m unittest discover -s tests/unit -v` | Exit 0; 56 passed, 0 failures/errors/skips | `reviewer-run-1.txt` |
| `python3 -m unittest -v` followed by the four packet critical test IDs | Exit 0; 4 passed, 0 failures/errors/skips | Exact arguments in `reviewer-commands-results.json`; output `reviewer-run-2.txt` |
| `python3 reviewer_probes.py` | Exit 0; 7 independent cases passed their assertions, 0 failures/errors/skips | `reviewer-run-3.txt` |
| Same four critical IDs using baseline adapter in a separate temporary copy | Exit 1; 4 assertion failures, 0 errors/skips, as expected | `reviewer-baseline-output.txt` |

The baseline contrast uses only `cortex_adapter.py` from the baseline and the frozen merged revision's other source/tests. It is not a claim that the full baseline suite was run. That temporary copy was deleted after execution. Repeated suite/critical runs overlap and must not be added together as distinct test coverage.

## Findings and limitations

1. **Bounded correction confirmed; no blocking finding.** In adapter lines 138–159, create identity is the earliest VERIFIED event's nonempty ID, rather than the mutable latest receipt. `_desired` checks that ID alongside exact name/content/dependencies/version. Update requests use `before.id` and additionally compare it directly in `_desired`. Repeated mismatches can update observation receipts without redefining either identity. The supplied legacy-history regression confirms a later erroneous VERIFIED B event does not supersede earlier VERIFIED A. My independent probe cycles through twelve replacement IDs and intermittent read outages, then restores A: none of the replacements verify; A verifies again; writes remain one. Another independent probe exercises an uncertain update and removes its event history: foreign B still cannot verify because before.id remains binding, then original A at the desired updated version verifies without another write.

2. **High impact if the trusted-history assumption is violated; accepted explicit residual risk, outside this fix.** Deleting all create events while retaining a latest VERIFIED A receipt makes `_first_verified_id` return None. A same-name/content/dependencies/version replacement B then returns VERIFIED B, with no new write. The independent `test_history_loss_can_rebind_create_even_when_latest_receipt_retains_A` reproduces this. This is not fail-closed recovery from missing/truncated history. Deleting just the earliest A verification while retaining a later erroneous B verification similarly leaves B as the first available identity by inspection. History authenticity and retention are operational prerequisites: do not reset, truncate or compact journals without preserving the original verified identity. No automatic corruption/loss detection or tamper protection is claimed.

3. **Low-severity documentation ambiguity; clarify before expanding the identity claim.** The host contract says an unacknowledged create reconciles by name/content/dependencies/version “until its ID has been independently observed.” Actual pinning starts at a persisted VERIFIED event, which is stricter than merely observing an ID. In independent `test_preverification_observed_identity_is_not_pinned`, a successful create A is independently read back, but a concurrent source-version change yields SOURCE_CHANGED and stores A without VERIFIED. Restore the source and substitute B with identical desired fields: the next invocation returns VERIFIED B. This is an observed-but-not-yet-VERIFIED identity transition, with no extra write. It does not violate the scoped first-VERIFIED guarantee, and the implementation-review document correctly identifies that scope. Clarify the host-contract wording to say “until the first VERIFIED event has been durably recorded,” explicitly including source-change/readback-failure paths. Do not describe the current implementation as pinning every observed create ID.

4. **Malformed history and journal-failure behavior checked.** Corrupt JSON before the first verification and a VERIFIED event lacking module_id raise before any transport call. This is fail-closed via exception, not a normalized UNKNOWN outcome. The scan stops at the earliest valid VERIFIED event, so it does not validate the integrity of later history. A deliberately aborted final VERIFIED journal insert rolls back both latest receipt and event, raises instead of returning VERIFIED, preserves WRITE_INTENT, and later reconciles without a duplicate write. Durable intent precedes external writes; the existing deny-event test confirms a failed intent transaction prevents the write. A failure after remote commit still cannot undo that remote operation and remains an uncertainty requiring retained intent.

5. **Transport/scope enforcement inspected.** The adapter validates request key, explicit synthetic names/dependencies/content marker, source snapshot and update baseline before calls. Reused request keys bind the full serialized request. Fresh readback checks source and target; write replies alone never produce VERIFIED. Only the bridge's exact error-code/text missing response means absence; generic errors/malformed reads remain unknown. Dependencies are allowed names, not recursively verified; account identity, fixture classification and callback behavior remain trusted host inputs. The coordinator is a separate local SQLite protocol, not a cross-service scheduler or security boundary. Sequential reads do not establish atomic cross-module consistency or prevent a write racing after preflight.

## CI scope

By source inspection, the workflow has `permissions: {}`, fetches public source without credentials, checks the requested SHA, and for pull requests requires merge parents matching the freshly observed base-branch tip and event head. This establishes the candidate at the time of that check; it is not protection against subsequent base movement. The runner stages source without `.git`, requests network-none/read-only/nonroot/capability and resource restrictions, compares manifests, requires four coordinator fault results, and checks ordinary teardown. Container/credential probes and retention bounds are implemented; shared-kernel/provider trust and future retention remain limits.

I did not execute Docker isolation, hosted workflow runs, the four container fault cases, real network failures, or live probes. I inspected fault implementations: three owned child-process SIGKILL boundaries and dedicated bounded tmpfs ENOSPC are coordinator tests, not Cortex network/power/device-loss tests. My local unit/probe success must not be represented as independent reproduction of hosted isolation, cleanup, retention, or those four fault results. Hosted run 39893032352 was supplied in the packet; I did not independently retrieve its logs during this review.

The seven independent cases include assertions demonstrating unsafe behavior beyond the declared boundary; their passing status proves those observations occurred, not that history loss or pre-VERIFIED identity replacement is safe. Human audit, full foundation acceptance, concurrent worker ownership/fencing, real outages, long-term durability, reciprocal registration and semantic knowledge/mastery remain unestablished. Notion remains paused; no production activation or canonical promotion is recommended.
