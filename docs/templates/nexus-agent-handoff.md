# Nexus — Lightweight agent handoff template

Copy this for each bounded mission. Keep entries brief; put detailed evidence in links, not copied logs.

**Mission ID:** `[unique id]`  
**Status:** `ASSIGNED | IN_PROGRESS | REVIEW | HOLD | COMPLETE`  
**Coordinator:** ChatGPT  
**Lead agent:** `[ChatGPT | Gemini | other approved agent]`  
**Reviewer:** `[different agent/person]`  
**Trigger / approval:** `[who initiated, explicit authorization, record link]`  
**Task and boundaries:** `[one sentence; what is allowed, excluded, and budgeted]`

## Lead result
**Finding / output:** `[short summary]`  
**Evidence:** `[source IDs, run URL, commit, receipt or response link]`  
**Unknowns / uncertainties:** `[what is not proven]`

## Independent review
**Reviewer contribution:** `[confirmed facts, correction, second opinion, or improvement]`  
**Review outcome:** `PASS | REVISE | DISAGREE | HOLD`  
**Reviewer evidence:** `[links and source checks; not agreement alone]`

## Next action
**Disposition:** `[COMPLETE | HOLD | RETURN_TO_LEAD | NEXT_BOUNDED_STEP]`  
**Owner / next actor:** `[agent or person]`  
**Next step / stop condition:** `[specific action and prerequisite]`  
**Audit checkpoint(s):** `[CP IDs; candidate evidence only unless criteria accepted]`  
**Write / scheduling status:** `[not attempted | explicitly authorized and independently verified]`

---

## Minimal operating rules

1. ChatGPT receives every mission and chooses the lead based on capability, scope, and approval; the other agent reviews when useful. Being named as lead/reviewer never grants new credentials or execution rights.
2. Record an **assignment** before invoking the lead. Keep one mission ID across retries. An uncertain external result is `HOLD` for reconciliation, never blindly retried.
3. Never claim an actual Gemini call, independent review, source verification, app write, or completed operation without its own evidence link.
4. Reviewer can contribute new insight, not merely error-check; disagreements and unresolved claims stay visible.
5. Mark `COMPLETE` only for the bounded, evidenced task. Passing a fixture does **not** close a Nexus foundation audit checkpoint.
6. This template is documentation, not automatic routing, event monitoring, durable hosting, or a live write authorization. D26 host provisioning, scheduled runs, and live Notion/Cortex writes remain deferred or disabled unless separately authorized and tested.
