# C9 ownership and stale-worker fencing — 2026-10-23

**Disposition: BLOCKED for multiworker execution.** Keep the adapter within its documented single-worker scope. This assessment changes no runtime or service permissions.

## Evidence and reproduction

Frozen implementation: `ac954ff9759771d48020ba4700797841b7968d3d`, merged PR #11. The local adapter was fetched independently from that exact GitHub commit and matched the probe's source byte for byte. The probe result includes SHA-256 hashes of the adapter and probe.

Run from a checkout of this branch:

```sh
python3 docs/c9/overlapping-workers-probe.py --output c9-local-result.json
```

[Probe source](overlapping-workers-probe.py) and [recorded result](overlapping-workers-result.json). The script uses two bounded Python threads, synthetic SQLite journals and an in-memory transport. A five-second event wait/join bounds each interleaving. A pause is injected after A's durable intent/preflight and before its transport update; B then completes before A resumes. No live Cortex call, real network race, process restart or host takeover was performed.

| Case | Observed outcome | Meaning |
| --- | --- | --- |
| Different keys, separate journals | B verified v2; delayed A then wrote its payload as v3 and reported SUCCEEDED/FAILED/READBACK_MISMATCH | A stale mutation was detected after it happened |
| Different keys, shared journal | Same B-v2 then A-v3 sequence; both updates occurred | Journal sharing alone does not provide target ownership |
| Same key and shared journal | B held at RECONCILE_ONLY; A alone wrote and verified v2 | Durable intent prevented a duplicate in this specific schedule; this is not a general concurrency proof |

All three cases passed their observation assertions. Two intentionally demonstrate missing protection, not safe behavior. All synthetic journals returned integrity_check=ok; the source and target ID remained unchanged. The payload/version overwrite, rather than journal corruption or identity rebinding, is the demonstrated gap. B's earlier verification was valid at its readback time, not a guarantee that its state would remain unchanged.

These three cases are separate from the existing 65-test suite and four hosted coordinator fault checks. Their counts must not be added together as new hosted coverage.

## Exposed service boundary

The currently available connected-tool definitions were inspected without invoking any live Cortex operation. context_update exposes name, content, dependencies, owner, parent, inherit_permissions and default_assignee. context_create exposes name, content, dependencies, parent and inherit_permissions. Neither definition accepts an expected version or a monotonic fencing token. This is a statement about the exposed tools, not a claim that no other vendor API can ever provide conditional mutations.

The host bridge sends only name, content and dependencies. It cannot attach a conditional version/token that the exposed tool does not accept. Sequential preflight and readback cannot reject a stale write at the service boundary. A local lock would only coordinate cooperating processes using that lock, excluding other journals, hosts and direct callers.

## Required decision and implementation boundary

Preferred route: obtain a service-supported conditional mutation tied to expected identity/version and an ownership generation. The actual mutation must atomically reject an outdated generation; a client-side comparison alone is insufficient.

A sole write gateway is an alternative only if exclusive write authority is enforced and stale or already in-flight requests cannot execute after ownership changes. A gateway lease by itself does not fence an old instance or a request already accepted downstream. Without downstream conditional writes, failover must stop until prior writers/in-flight mutations are conclusively quiescent; automatic takeover cannot be assumed safe. A grant inventory and exclusivity check would require separate authorized service/host configuration work, which this assessment does not perform.

Do not add a lease table or file lock and label C9 complete. No backend conditional-write capability or exclusive gateway enforcement has been demonstrated. Remaining single-worker scope is a real operating constraint.

## Acceptance cases for a future design

| Test | Required evidence at the real mutation boundary |
| --- | --- |
| Simultaneous ownership acquisition | Exactly one generation wins; loser cannot mutate |
| Expiration and takeover | New generation obtains authority while old generation is refused |
| Delayed stale write | A's write after B takes over is rejected before changing content/version |
| Accepted but in-flight old request | Old request cannot commit after takeover, or takeover is held until definitive quiescence |
| Service/gateway restart | Persisted ownership prevents old generations from regaining authority |
| Uncertain mutation acknowledgment | Reconciliation avoids duplicate writes without treating a timeout as absence |
| Direct caller bypass | Non-gateway/unauthorized callers cannot bypass the claimed boundary |

Record exact source/service versions, effective grants, request generations, before/after observations and raw failures. Offline models can guide this work but cannot establish remote enforcement. No live race test should be inferred from this artifact.

## Review and audit disposition

The prior independent AI review covers PR #8's identity safeguard and does not independently review this author-run C9 probe. PR #11's object-type fix remains a distinct author-validated follow-up. Human review, effective live grants, forced host cleanup, power/device loss, long-term durability and other broader audit limits remain open. Full foundation acceptance stays BLOCKED; Notion remains authoritative and paused. No production or canonical activation follows.
