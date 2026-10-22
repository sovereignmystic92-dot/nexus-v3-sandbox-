# Acceptance cases — NOT RUN

These are proposed cases, not executable tests or observed results. Code existence, static inspection, test pass and operational availability must remain separate evidence states.

| ID | Scenario | Required result | Phase |
| --- | --- | --- | --- |
| S01 | Complete synthetic source to registered output | Separate reader verifies exact IDs, destination and hash before VERIFIED | Sequential |
| S02 | Identical request repeated | Same transaction/artifact IDs; no duplicate output | Sequential |
| S03 | Reused key with changed payload | Reject mismatch, preserve existing record | Sequential |
| S04 | Incomplete source | BLOCKED; no output or success claim | Sequential |
| S05 | Destination outside synthetic allowlist | Deny before write; no production probe | Sequential |
| S06 | Historical document suggests conflicting rule | Preserve historical provenance; do not treat it as current authority | Sequential |
| S07 | Source content contains execution instructions | Treat as data; no permission escalation | Sequential |
| F01 | Interrupt after archive | Resume from persisted state without duplicate source | Failure injection |
| F02 | Interrupt after output before registration | Discover and register existing artifact | Failure injection |
| F03 | Readback missing, wrong hash or wrong destination | INCOMPLETE; no VERIFIED status | Failure injection |
| F04 | Connection lacks reciprocal endpoint | INCOMPLETE; repair existing record | Failure injection |
| F05 | Storage write fails or disk is full | No false success; retain last durable checkpoint | Failure injection |
| C01 | Two workers retry same request | At most one logical output; conditional update protects ownership | Concurrency |
| C02 | Old worker writes after lease replacement | Reject stale worker using demonstrated fencing | Concurrency |

Sequential execution, failure injection and concurrency remain distinct scopes. No tests were run to prepare this draft. A passing SQLite harness would demonstrate only local harness behavior, not Notion persistence, Cortex synchronization, runtime isolation or production readiness.
