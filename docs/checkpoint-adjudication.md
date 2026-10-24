# Checkpoint adjudication — 2026-10-24

Owner instruction: proceed with individual pass decisions following adoption of PR #23.
Assessor: ChatGPT, author assessment; not an independent human reviewer.
Definition set: proposal-1 (owner adopted). Evidence revision: `709a4d39d1c0058d3f4dc8c8832025ad324d55b5`.

## Decision

Eight requirements pass in their **previously declared single-worker synthetic SQLite scope**: CP11–CP17 and CP19. Seven controls remain PARTIALLY_VERIFIED and four remain BLOCKED. The new itemized baseline is 8/19 after this change is accepted on main. No ninth gate is claimed. The historical 8/19 is retained but superseded for scoring; matching totals do not identify the historical eight.

No requirement, denominator or scope was narrowed for this adjudication. CP11–CP19 already declared the local SQLite boundary in the owner-adopted register. Requirements involving real host/service controls, external readback or independent human review remain open. These local passes do not depend on treating C1–C9 as passed; broad activation still depends on those controls.

## Evidence examined

The committed [actual main report](checkpoint-evidence-main-709a4d3.json) was separately fetched and parsed. Run [40135860508](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/40135860508) reports exact source revision above, 162 distinct passing cases, three actual owned-child SIGKILL cases and bounded tmpfs ENOSPC/SQLITE_FULL recovery. Four fault cases remain separately counted.

Source inspection at the same frozen SHA covered `src/nexus_sandbox/coordinator.py`, `src/nexus_sandbox/authority.py` and `tools/fault_checks.py`. Earlier source inspections covered the named mission, coordinator and authority tests. No new tests were run for this documentation/status adjudication. GitHub retrieval is independent of the original write response, but not an independent human review or physical fault domain.

## Itemized decisions

| ID | Requirement | Verdict | Reason |
| --- | --- | --- | --- |
| CP01 | Host and filesystem isolation | PARTIALLY_VERIFIED | Container boundary checks passed. Broader host trust and independent host-boundary assessment remain open. |
| CP02 | Identity and effective grants | BLOCKED | Complete effective grants and restricted provider-side test identity are unavailable. |
| CP03 | Credential and mount exclusion | PARTIALLY_VERIFIED | Container credential-name/mount checks passed; host-side complete credential exclusion remains unverified. |
| CP04 | Network and triggers | PARTIALLY_VERIFIED | Container denial probes and reviewed workflow inventory passed. Full hooks/settings/scheduler/host-egress inventory, approval release and branch-denial evidence remain missing. |
| CP05 | Synthetic fixture and destination binding | PARTIALLY_VERIFIED | Local fixture markers, immutable binding and destination denial have passing tests. Host/operator account and synthetic classification assurance remain incomplete. |
| CP06 | Durability and recovery | PARTIALLY_VERIFIED | SIGKILL, ENOSPC and staged restore checks passed. Protected latest witness, coherent rollback resistance and declared total-local-state-loss recovery remain open. |
| CP07 | Independent readback | PARTIALLY_VERIFIED | Local fresh storage and fresh-process restored-identity checks passed. Complete intended external adapter/readback scope is not established. |
| CP08 | Stop, cleanup and retention | PARTIALLY_VERIFIED | Ordinary container/staging cleanup and killed-child staging cleanup passed. Forced host-stop cleanup and future deletion remain unverified. |
| CP09 | Remote ownership and fencing | BLOCKED | Remote CAS/fencing not established; single-worker deferral is not acceptance. |
| CP10 | Independent human review | BLOCKED | Independent human review has not been established. |
| CP11 | Complete transaction and exact repeat | PASSED | M01 verifies all six states, three exact artifact identities/destinations/payload hashes and linked receipts, then reopens and repeats with an unchanged full snapshot. S01/S02 corroborate separate committed-storage readback and identity reuse. |
| CP12 | Idempotency binding conflict | PASSED | S03 rejects four changed bindings and retains the original checkpoint. Inspection of submit confirms binding comparison precedes any INSERT/UPDATE or event creation and all exceptions roll back the transaction. |
| CP13 | Incomplete source hold | PASSED | M03/S04 persist NEW/BLOCKED with explicit next action, zero artifacts and NOT_ATTEMPTED/BLOCKED envelope; repeated submit/resume leave the full snapshot unchanged. |
| CP14 | Forbidden destination hold | PASSED | S05 rejects an out-of-allowlist destination before transaction insertion. Inspection confirms _fixture runs before any write in the new-request path; rollback covers exceptions and no external transport exists in this coordinator. |
| CP15 | Authority precedence and source instructions | PASSED | S06 retains historical/source/hypothesis provenance while only current records govern. Current conflicts hold without artifacts; S07 persists instruction-shaped prose literally. Authority code binds a hash of current metadata to each transaction and resume holds changed authority. |
| CP16 | Recovery after source archive | PASSED | SIGKILL-after-archive observes actual owned-child SIGKILL, reopens the database at ARCHIVED, checks integrity, retains archive identity and finishes with exactly three artifacts, six events and six attempts. |
| CP17 | Recovery after output before registration | PASSED | SIGKILL-after-output observes actual owned-child SIGKILL and reopens at OUTPUT_CREATED; recovery reaches VERIFIED with three artifacts/six events/six attempts. M02 and immutable artifact IDs support existing-output reuse. No external adapter belongs to this already-declared checkpoint scope. |
| CP18 | Reciprocal connection registration | BLOCKED | External reciprocal endpoint registration is documented as absent; no exact repair/readback evidence satisfies this requirement. |
| CP19 | Readback and storage failure safety | PASSED | Wrong/missing/misrouted readback remains INCOMPLETE; event-write failure rolls back artifacts/checkpoint. REAL-TMPFS-ENOSPC observes ENOSPC and SQLITE_FULL, compares the entire recovered snapshot to baseline, and reaches VERIFIED after space is freed. |

## Pass evidence conditions

CP12: the S03 assertion retains the checkpoint rather than directly comparing every table. Code inspection supplies the missing causal evidence: changed binding raises before write statements and transaction rollback runs on every exception. No stronger empirical snapshot assertion is claimed.

CP14: request validation occurs before transaction insertion, and the local coordinator contains no external transport. “Zero transport writes” therefore applies only to this local component; no production endpoint was probed.

CP15: authority labels are trusted operator metadata. The pass establishes deterministic structured precedence and source-as-data handling, not authentication of arbitrary Nexus prose or general prompt-injection resistance.

CP16/17: actual process SIGKILL and subsequent reopened database are observed; the host remains alive. Neither checkpoint claims total-host-loss recovery. CP06 retains that broader gap.

CP19: bounded tmpfs ENOSPC is observed; power/device loss is excluded by the already-adopted requirement. Failed writes preserve the full durable baseline before recovery.

## Next gate

CP07 is a candidate for further work, not a promised ninth pass. Its full intended persistence-surface inventory and exact fresh readback/mismatch evidence must be established, including active external test adapters. Paused Notion integration must stay explicitly excluded from current execution and unaccepted for future integration. Do not silently redefine CP07 to SQLite-only.

CP04 is also still incomplete: workflow inventory and container probes cannot substitute for complete host/settings/hooks/scheduler inventory, successful approval release and server-side branch-denial evidence.

## Record integrity

Original evidence and prior history entries remain intact. Current decisions append new observations and acceptance identity/time. Superseded proposal-pending statements are historical at their earlier observation dates. Every PASS must be reassessed after relevant implementation/configuration changes; later documentation-only revisions do not automatically invalidate source evidence, but that applicability decision must be explicit.
