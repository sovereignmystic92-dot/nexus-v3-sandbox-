# Independent review packet — C15

**Status: INDEPENDENT AI REVIEW COMPLETED for the frozen revision. Independent human audit NOT ESTABLISHED; full foundation acceptance remains BLOCKED.**

## Exact target

- Repository: [nexus-v3-sandbox-](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-).
- Frozen reviewed revision: `618681fdc6d1767358cca993e857f68fd2202879` (merged PR #6).
- Fix head before merge: `35e764254d2aa97dd29e3d3ace321c953d150eec`.
- Baseline with reproduced defect: `ce7ad5e8bf1f5b968e6cd9334b91716f90ad76ed`.
- [Merged PR #6](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/pull/6).
- [Actual main CI 39893032352](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39893032352): author retrieved its logs reporting 56 tests and four separately counted bounded faults, boundaries/manifests and cleanup.
- No submitted GitHub review returned for PR #6 when this packet was prepared. The subsequent independent AI review is recorded below; it is not a GitHub human-review approval.

Review the frozen revision even if main later moves. The independent reviewer must inspect actual code and produce their own findings/results; the statements here are review inputs, not their conclusions.

## Source entry points

- [src/nexus_sandbox/cortex_adapter.py](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/blob/618681fdc6d1767358cca993e857f68fd2202879/src/nexus_sandbox/cortex_adapter.py) — Git blob `765e4b51d61a76b023a3abc8d7388385761f4222`
- [src/nexus_sandbox/cortex_tools.py](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/blob/618681fdc6d1767358cca993e857f68fd2202879/src/nexus_sandbox/cortex_tools.py) — Git blob `4d3000535815624ac7c623e0ad503813ceb17904`
- [tests/unit/test_cortex_adapter.py](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/blob/618681fdc6d1767358cca993e857f68fd2202879/tests/unit/test_cortex_adapter.py) — Git blob `4e54bda0c58f95d07244b112b43c3e275156280a`
- [tools/run_isolated.py](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/blob/618681fdc6d1767358cca993e857f68fd2202879/tools/run_isolated.py) — Git blob `3a69b1fb704f0bae34e0c24d96d363bcba84fe0e`
- [.github/workflows/synthetic-acceptance.yml](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/blob/618681fdc6d1767358cca993e857f68fd2202879/.github/workflows/synthetic-acceptance.yml) — Git blob `65e3da585100b8ff7f502e710e8e8ad5ed769ea0`

Also inspect [the original author review](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/blob/618681fdc6d1767358cca993e857f68fd2202879/docs/implementation-review.md) and [adapter contract/history](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/blob/618681fdc6d1767358cca993e857f68fd2202879/docs/cortex-adapter.md). Their pending-merge statements are historical snapshots; PR status and exact post-merge CI establish that the fix landed.

## Defect and patch to challenge

Old behavior: create verified at A; observe replacement B with identical name/content/dependencies/version; first retry saved B in the latest receipt, second retry could verify B. A foreign preflight conflict could also cause a later legitimate create/update to fail verification.

The patch chooses create identity from the earliest VERIFIED journal event for the immutable request key. Updates choose the exact before-snapshot ID. Latest observation receipts cannot redefine that identity. Existing complete journals retain the original verification without schema reset. Journal integrity/authenticity is trusted; preserving history is required.

Author evidence: four regressions failed old code and passed the fix. C14 additionally made 18 real Cortex gets and zero live writes using exact merged code: verify A, locally substitute B twice, both blocked, restore original observations, verify A and repeat. Final raw source/archive reads were unchanged. This was local observation injection, not remote module replacement/deletion.

## Independent reproduction

Use an isolated review checkout with no production credentials or connected live callback:

```sh
git clone --no-checkout https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-.git nexus-review
cd nexus-review
git checkout --detach 618681fdc6d1767358cca993e857f68fd2202879
python3 tools/validate.py --output reviewer-validation.json
```

Run critical identity regressions explicitly:

```sh
PYTHONPATH=src:tests/unit python3 -m unittest \
  test_cortex_adapter.CortexAdapterTests.test_verified_create_identity_never_changes_across_replacement_retries \
  test_cortex_adapter.CortexAdapterTests.test_legacy_wrong_latest_verified_receipt_does_not_replace_first_identity \
  test_cortex_adapter.CortexAdapterTests.test_unverified_preflight_conflict_does_not_pin_foreign_identity \
  test_cortex_adapter.CortexAdapterTests.test_update_baseline_identity_survives_an_unverified_foreign_conflict
```

The offline suite uses standard-library synthetic transports and temporary databases; it does not invoke Cortex or Notion. Record the exact Python/platform/revision, commands, complete failures/skips and results. Do not label the supplied CI report as a test independently rerun by the reviewer. Review the hosted fault logs separately; a local unit run does not independently establish container isolation or all four hosted faults.

## Required review questions

1. Can any repeated nonmatching observation still change the first verified create identity?
2. Does update identity remain pinned to the immutable before snapshot after conflicts and uncertain outcomes?
3. Are legacy journals with a later incorrect receipt/event handled conservatively? What happens if history is malformed, absent, truncated or tampered with? Distinguish supported recovery from trusted-history limitations.
4. Can a journal/transport/readback failure lead to false VERIFIED status or an unauthorized blind write?
5. Are request keys, name allowlists, source bindings, exact content/version/dependencies and separate outcomes enforced before side effects?
6. Are new tests adversarial enough? Add independent cases rather than simply repeating implementation logic.
7. Does the workflow test the actual merge candidate/current base with empty permissions and preserve the stated isolation/retention limits?
8. Are evidence claims restricted to the performed tests? In particular, do not infer remote CAS/fencing, real network or power loss, long-term durability, reciprocal registration or knowledge mastery.
9. Is the trusted event-history requirement operationally clear, including retention and any future journal compaction?

## Required reviewer response

Provide reviewer identity/type (human or AI), independence from implementation, exact revision, inspected files, reproduced commands/results and findings with severity, trigger, impact and evidence. State residual risks, unresolved questions and the decision for this bounded fix. A second AI review must be labelled AI review; it does not establish an independent human audit. Do not approve broad production acceptance from this package.

## Automated material-sufficiency precheck

[Exact supplied inputs and returned outputs](automated-evidence-precheck.json) are retained without rewriting the tool's verdict.

The connected AI Delivery Evidence Checker evaluates supplied descriptions/results. It cannot inspect repositories, run tests, verify authenticity or provide code-review/release sign-off. It classified delivery F1–F3 supported, T1/A1 partial, A2 unsupported; its test check was partially supported and its combined verdict was not_supported because A2 remained unsupported.

A2 explicitly represents broader concurrent-worker ownership/fencing, which is excluded from the bounded identity fix. That aggregate verdict is not evidence that the 56 reported tests failed or that the merged fix is incorrect. A1's partial label is not completion: **no independent code reviewer inspected or reproduced tests through that service**. Its classifications are retained as an automated assessment of the supplied material, not promoted to verified implementation facts.

## Audit disposition and boundaries

- C13 specific implementation defect: author-remediated and validated in merged main/C14, with independent reviewer confirmation requested.
- Independent code review/reproduction: OPEN; human audit: NOT ESTABLISHED.
- Full foundation acceptance: BLOCKED. Concurrency/fencing, full live permission isolation, reciprocal registration, real network/power/device-loss and long-term durability remain unproven.
- Notion remains authoritative and paused. No live module mutations, autonomous callback deployment, production activation or canonical promotion are authorized by this packet.
- Do not assign/request an external reviewer or send notifications without the owner's chosen reviewer/route.

## Completed independent AI review

The owner explicitly selected a separate review agent. `/root/independent_identity_review` fetched frozen files through GitHub into a new directory rather than using the author checkout. All 27 materialized files matched their Git blob SHAs before the final reported runs. Its [report is preserved verbatim](independent-review/independent-review-report.md), with [commands/results](independent-review/reviewer-commands-results.json), [validation JSON](independent-review/reviewer-validation.json), raw logs, [independent probes](independent-review/reviewer_probes.py), and source manifests in the same directory.

The reviewer reproduced 56 suite tests with no errors/skips; the four critical regressions passed the fix and failed the baseline adapter as expected. Seven independent adversarial cases passed their assertions, including assertions that demonstrate limitations rather than safe behavior. Repeated suite/critical runs overlap and are not added to the 56-case total. The independent reviewer did not rerun Docker/hosted faults or live Cortex probes; those remain earlier author-observed evidence.

Scoped recommendation: accept the first persisted VERIFIED create identity / immutable before-ID update identity correction, under complete trusted journal history and one-worker assumptions. No blocking defect was found within that scope. Confirmed residual risks: deleting create event history can allow B to verify; observing A before a persisted VERIFIED event does not pin it. The reviewer requested low-severity contract wording clarification. This PR proposes that documentation clarification without changing implementation; the report/repro artifacts remain unchanged.

To run the published independent probes from a checkout of this documentation branch: `PYTHONPATH=src:tests/unit python3 docs/independent-review/reviewer_probes.py`. The reviewed implementation remains the frozen revision above; any later runtime change requires new review. The earlier automated-material precheck is a historical assessment prepared before the independent agent's actual inspection/reproduction and is retained unchanged. Independent AI review is now evidenced; independent human audit and broader foundation acceptance remain open.
