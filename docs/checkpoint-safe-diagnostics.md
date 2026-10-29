# Checkpoint probe diagnostics — inactive repair

This revision combines PR72 stage/ack diagnostics and PR77 D24 mode/state/outcome diagnostics on current main. Original tests are retained under unit discovery, with four added raw-client/privacy/outcome tests. No workflow or authority change is made.

The HTTP boundary preserves only a validated integer status (400–599) and fixed category. It never prints provider messages, bodies, URLs, headers or arbitrary exception text. Missing status remains null/UNKNOWN; HTTP status is an observation, not proof of effect absence or a complete root cause.

Probe output keeps execution mode, checkpoint observation, write outcome, write acknowledgment, failure stage, append error and observation error separate. An acknowledged append followed by failed readback stays BLOCKED_UNCERTAIN. An HTTP error followed by bounded absence also stays BLOCKED_UNCERTAIN; never replay it blindly. Reruns remain observe-only, both write switches remain off after attempt1, and request/read budgets are unchanged.

Original run40781386183 used older source1ff5dbffbcd900687b4477490ded37827b0cc892. Its omitted HTTP/error detail cannot be recovered by this patch, and rerunning that existing run still uses its original source. No new live run or write is performed or authorized by this diagnostic repair. Live test resumption needs reconciliation and applicable native gates; production/bridge activation and CP09 acceptance remain outside this proposal.

Rollback: normal reviewed revert of this scoped change, retaining earlier failing run evidence. PR72 and PR77 review statements are claims until corroborated; final hosted and independent review must bind the exact new revision.

