# Interim single-worker mode and recovery checks — 2026-10-23

**Owner-selected interim operating mode:** one designated runtime may perform authorized synthetic writes; other agents may analyze and propose changes. Defer vendor clarification as an external dependency rather than treating it as a prerequisite for continued bounded offline audit work. C9 remains BLOCKED for multiworker use. This is an operating rule, not newly enforced exclusive authority.

## Operating rule

Use one persistent original request plan and journal for the designated writer. Do not start a second writer against the same fixtures, even with another journal. Do not interpret a timeout as absence, blindly retry a mutation, reset/compact the journal, or automatically transfer ownership after uncertainty. Reconcile the original request by reading first; if reads or journal integrity are unavailable, hold. A handoff requires the prior writer and outstanding work to be quiescent and the original evidence available. The current tools cannot prove or fence a remote in-flight writer.

Other hosts must remain proposal-only for these fixtures. This publication does not configure Gemini/Claude/other sessions, revoke their grants or establish that they lack write authority. The current Cortex connection previously reported owner capabilities on the four fixtures; C2 least privilege remains open. No permission change, account creation, live callback deployment or canonical promotion is performed here. Notion stays authoritative and paused.

## New offline recovery evidence

Frozen implementation: `20735ddade16c47588486252c95d3ffc2192954d`. The local adapter was fetched from that exact GitHub revision and matched byte for byte. [Probe](recovery-probe.py) and [recorded results](recovery-result.json) include source/probe SHA-256 hashes.

Run from a checkout:

```sh
python3 docs/single-worker/recovery-probe.py --output recovery-local-result.json
```

| Case | Actual observation |
| --- | --- |
| SQLite capacity exhausted before intent | SQLITE_FULL (13); zero remote writes and zero receipts/events; after releasing the page ceiling, one create independently verified |
| SQLite capacity exhausted during verification after remote commit | SQLITE_FULL (13); receipt stayed WRITE_INTENT, one event and zero anchors; verification transaction rolled back; later reconciliation verified with one total create |
| Uncertain create followed by three read outages | Each reopening held NOT_ATTEMPTED/UNKNOWN/READ_BLOCKED; reads resumed and reconciliation verified with one total create |

The first capacity ceiling was seven SQLite pages; the second eight pages. The script asserts the database stayed within its configured page ceiling after failure and verifies SQLite integrity before/after recovery. The post-commit capacity fault uses a test-only event trigger that attempts to grow the database during VERIFIED persistence; its insertion also rolled back.

All three cases passed their stated assertions. These are additional author-run manual probes, separate from the existing 65-test suite and four hosted coordinator fault checks. They do not increase the hosted test count. No production adapter code or workflow changes are required by these observations.

## What this establishes and what remains open

The adapter's intent/verification transaction boundaries and read-only reconciliation withstand these bounded SQLite-capacity and modeled read-outage cases. SQLite max_page_count exhaustion produces a real SQLITE_FULL result, but is not physical filesystem ENOSPC, device failure or power loss. The remote is in memory, timeouts are injected locally, and adapter reopenings occur within one Python process; this does not repeat the earlier actual-process/live observations or prove host restart durability.

No forced host teardown, long-term retention, complete database-loss protection, authenticated history, multiworker lease/fencing, restricted-principal setup or independent human review is established. The earlier independent AI reports remain attributed to their own reviewed revisions and do not review this author probe. The complete foundation audit remains BLOCKED. Continue single-worker synthetic verification while these exclusions remain explicit.
