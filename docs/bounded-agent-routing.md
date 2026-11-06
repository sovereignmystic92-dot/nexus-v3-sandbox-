# Nexus bounded lead/reviewer router — sandbox design

Status: **PROPOSAL-ONLY**. No Gemini or ChatGPT API call, no workflow dispatch, no background monitoring, no Cortex/Notion write, no credential reads, no production execution.

`src/nexus_sandbox/agent_routing.py` selects a lead and distinct reviewer for each mission. The ChatGPT coordinator supplies an explicit `Mission` contract, required skills, an approved roster, and the authenticated evidence *as inputs*. The underlying `mission_dispatcher.dispatch` decides READY/HOLD/COMPLETE first; agent routing cannot override it.

Selection is deterministic: select among approved, currently available agents whose declared skills contain every required skill, preferring more listed skills and then alphabetical name. This is a fixed synthetic scoring rule, **not an AI assessment of actual competence**. For production, skill claims and authorization must come from trusted verified evidence, not caller assertions.

The router returns a `routing_digest` over sorted roster and mission inputs, `lead`, `reviewer`, decision state and reason, and `NON_EXECUTING_PROPOSAL` authority. No assignment occurs if prerequisites are missing, if the lead is unavailable, or if a distinct qualified reviewer is missing. REVIEW must remain independently sourced rather than merely agreement with the lead.

Tests cover deterministic results across roster ordering, separate reviewer, missing trigger, missing dependency, ACTIVE authorization HOLD, unavailable and unapproved agents, absent qualifying lead, duplicate roster, completed missions, and changed-roster digest.

## Next integration stages

1. Persist router proposal and the source/authorization evidence in the existing `MissionJournal`. Bind assignment to immutable mission identity and revision; prevent two assignments from being promoted for the same revision.
2. Add a bounded host adapter to execute the selected lead **only with separately authenticated grants and provenance**, with no blind retry after an uncertain effect.
3. Independently read the returned receipt and route it to the distinct reviewer. Store corrections, disagreements, and next action in a journal revision.
4. Test interruption, replay, stale assignment/roster, mismatched outputs, and reviewer refusal.
5. Audit CP02 (scope/role), CP05 (durable readback), and CP10 (genuine independent reviewer evidence). No audit-gate closure without acceptance.

D26 remains deferred; no live integration, scheduling or merge is authorized by this proposal.
