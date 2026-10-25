# First useful Nexus automation — source-linked draft for review

Status: IMPLEMENTATION PLAN, NOT DEPLOYED.
Foundation assessment remains COMPLETE_WITH_DOCUMENTED_EXCEPTIONS; full acceptance BLOCKED and production NOT_AUTHORIZED. Current score remains 11/19.

## Outcome

Reduce repeated copying and formatting: accept one complete source packet, preserve its original wording and provenance, produce a proposed Nexus analysis, and return one review bundle with explicit unknowns and processing status. Human review remains required before canonical integration. A future operational run should turn a selected source into a reusable draft rather than merely replay storage tests.

## Current evidence and limits

At base `11b12e374cf46ea6ff75ad85b85f99806db714d6`, `integrations/gemini/smoke.py` accepts synthetic task packets, limits source/task sizes, makes one bounded request only after free-tier confirmation and returns ANALYSIS_RECEIVED / PROPOSED / app_writes NOT_ATTEMPTED. It is an optional manual analysis bridge, not a queue worker or source-ingestion pipeline. No current implementation authenticates real-source completeness or proves semantic citation support.

The SQLite coordinator preserves fixture payloads and verifies storage; that is not knowledge synthesis. Reusing its status vocabulary must not mislabel analysis as completed research.

## First release contract

| Element | Definition |
| --- | --- |
| Trigger | Manual submission of one explicitly identified packet; no schedule, watch folder or unattended ingestion |
| Input | Packet ID/revision, source IDs, original text, provenance, completeness declaration, question, classification and permitted output destination |
| Scope | First implementation remains synthetic and single-worker; real user-selected sources require an explicit scope amendment and relevant exception review |
| Output | Review bundle: original source and hash, proposed analysis, claim-to-source map, inference/unknowns, missing evidence, packet/result identities, operation outcome and protocol verdict |
| Destination | Review-only sandbox output; no production Notion/Cortex writes or canonical status changes |
| Stop | Missing/incomplete source, changed packet binding, invalid citation IDs, blocked provider result or permission uncertainty stops progression and preserves the confirmed state |
| Billing | No billing enablement or paid provisioning; retain manual free-tier confirmation and stop rather than retry on quota/provider error |

## States and separation

RECEIVED -> VALIDATED -> DRAFT_RECEIVED -> CHECKED_FOR_REVIEW -> AWAITING_REVIEW.
A reviewed output remains PROPOSED until a separately authorized publication route exists. CHECKED_FOR_REVIEW means structural/provenance checks passed, not that the analysis is correct or canonically integrated. BLOCKED/INCOMPLETE records include an explicit reason and next action.

## Implementation sequence

1. Add a deterministic packet intake/validation interface and canonical packet hash. Reject duplicate source IDs, missing provenance, incomplete declarations and changed reuse of a packet ID/revision.
2. Produce a review-bundle writer with stable identities and readback. Preserve the original source exactly; keep analysis separate. No automatic deletion; superseded bundles retain provenance and clear noncurrent state.
3. Adapt the existing synthetic-only analysis bridge to structured draft output. Keep single-call/no-blind-retry behavior, source-as-data instructions, bounded sizes and explicit uncertainty.
4. Validate the claim/source mapping, missing source references and required fields. Syntax/reference validation cannot establish entailment or research quality; human review assesses whether cited text actually supports each claim.
5. Expose a manual run command and readable summary reporting what happened and what awaits review. Repeating a confirmed completed local packet must not duplicate its review bundle. An uncertain live API outcome must hold rather than automatically repeat a chargeable call.
6. Only after the above exists, propose a controlled real-source draft pilot. Review CP02/03/04/05 for any new account, secret, input classification, network path or destination. Do not activate a scheduled worker or production publisher as part of that decision.

## Acceptance cases tied to user value

| Case | Required result |
| --- | --- |
| Complete supported packet | Review bundle preserves exact source, has stable packet/result hashes and identifies supporting source IDs |
| Repeated packet | Existing confirmed review result is reused; no duplicate review bundle |
| Same ID/revision, changed content | Hold with immutable-binding conflict |
| Partial transcript | No false full-fidelity or complete-processing claim; specific missing-source hold |
| Conflicting sources | Conflict and uncertainty remain visible, without silently selecting an unsupported resolution |
| Unsupported claim/reference | Invalid source IDs fail structural checks; valid but unsupported claims require human rejection |
| Source contains commands | Commands remain quoted evidence; no tool or permission escalation |
| Interrupted/uncertain analysis | Preserve confirmed state; no blind API replay or duplicate output |
| Review/publishing boundary | Completing draft checks cannot set Integrated, modify production pages or claim research mastery |
| No-cost boundary | Missing free-tier confirmation or provider limit prevents execution; no paid fallback |

A good first automation is accepted when it reliably creates a usable, inspectable draft and reduces manual handoff without overstating quality. Counting tests or completing another synthetic storage run is insufficient.

## Tonight's completion criteria

The planning deliverable can be established now: this contract, implementation order, acceptance cases and exception triggers. Actual automation is not established until implemented and tested. The foundation assessment already closed in PR #43; this plan does not promise full 19/19 acceptance tonight. Provider-assurance and independent-human-review gaps cannot be closed by draft automation.

## Deferred work

Automatic scheduling, bulk ingestion, external source crawling/transcript acquisition, real-source classification, production Notion/Cortex publication, paid services and multiworker execution are outside the first release. Host-loss cleanup and standalone artifact deletion remain deferred under the closure record. No reminder or scheduled automation is created by this plan.
