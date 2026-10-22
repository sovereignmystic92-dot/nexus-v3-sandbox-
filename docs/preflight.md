# Execution preflight — unverified

Owner-selected repository: public, `sovereignmystic92-dot/nexus-v3-sandbox-`.
Current authorization: prepare and publish this review draft on a separate sandbox branch with a draft pull request. Runtime provisioning, paid services and acceptance execution remain outside this step.

| Control | Required evidence | Current state |
| --- | --- | --- |
| C1 host/filesystem isolation | Disposable host, mount map, permissions | NOT VERIFIED |
| C2 test identity | Effective grants and inherited permissions | NOT VERIFIED |
| C3 production exclusion | No production credentials, mounts or intermediary routes | NOT VERIFIED |
| C4 egress and triggers | Host-enforced network denial; schedulers/webhooks disabled | NOT VERIFIED |
| C5 fixtures and routing | Synthetic manifest, deterministic IDs, test-only allowlist | Draft present; enforcement NOT VERIFIED |
| C6 durable state | Atomic checkpoint/event updates and uniqueness behavior | Schema draft; behavior NOT VERIFIED |
| C7 independent readback | Fresh reader, exact identity/hash/location comparison | NOT VERIFIED |
| C8 stop and teardown | Stop mechanism, baseline/final inventory, retention deadline | NOT VERIFIED |
| C9 fencing | Atomic ownership and stale-worker rejection evidence | NOT VERIFIED; later concurrency scope |

Open: runtime host and operator, separate reviewer or explicit reviewer limitation, retention/teardown deadline, enforced credential/filesystem/network isolation. Free-first preference does not establish provider eligibility or authorize spending.

Review record: reviewer, date, package revision, observed evidence, unresolved controls, decision, exact authorized scope and expiry. This template is not approval or a readiness verdict.
