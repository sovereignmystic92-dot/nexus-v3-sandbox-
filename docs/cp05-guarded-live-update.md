# CP05 guarded live update and restart

Status: PARTIALLY_VERIFIED. Accepted score remains 11/19. The adopted requirement/scope are unchanged.

## Live observation

Three new synthetic fixtures were separately provisioned and independently read. The opt-in BoundCortexToolTransport and CortexAdapter ran in a Python process whose JSON-line callback was bound by the host to the real connected Cortex get/update tools. No credentials or direct network client entered the process. Private plan/journal and fixture IDs remain in the authorized sandbox records, not this public repository.

The initial noninteractive attempt stopped at read-only preflight when stdin closed: no journal or update existed. The original plan was retained. An explicit preflight-resume flag required an absent journal and fresh exact source/target baseline before continuing; nothing was reset or blindly replayed.

Actual write phase: 25 provider gets and exactly one provider update. Wrong configured root ID, wrong configured root owner and an unenrolled destination were rejected with zero writes. The allowed target update returned SUCCEEDED/VERIFIED; exact repeat was NOT_ATTEMPTED/VERIFIED with no second update.

A separate actual Python process reopened the original plan/journal, with updates forbidden by both the script and host callback. Sixteen live gets produced two NOT_ATTEMPTED/VERIFIED results and zero updates. Three final independent get calls confirmed root/source full snapshots unchanged; target ID, owner, parent, permission inheritance, assignee, creation timestamp and archived state preserved. Target version advanced exactly once, v1 to v2, with exact desired content/dependencies.

## Reproduction and safety

The generic tools/bound_live_probe.py requires private initial observations and an explicit host RPC bridge. Run write once; preserve the original plan/journal and use reconcile afterward. It never creates fixtures or handles credentials. The host must independently allowlist exact names/payload and permit at most one update. Do not feed private plans or provider replies to public CI/logs. The normal offline workflow does not invoke this live probe.

## Remaining gate requirements

Owner metadata and a pinned root are not authenticated caller/account identity. This test supplies positive guarded-update/restart evidence, not provider-enforced account grants or full host path coverage. The old raw bridge remains read-only; direct connector access and arbitrary supplied transports remain outside its enforcement. Creation/enrollment needs separate assurance. Sequential reads do not supply CAS/fencing. CP05 does not become the twelfth pass from these results alone.

Standard local validation still passes 210 distinct tests. Hosted regression and exact committed-source readback are checked separately before merge. Detailed live evidence is retained privately in Notion/Cortex; only sanitized counts and outcomes are published here.
