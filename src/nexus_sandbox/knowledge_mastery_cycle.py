"""Compose offline mastery decisions without side effects or authority promotion."""
from dataclasses import dataclass
from nexus_sandbox.knowledge_mastery_cortex_bridge import prepare_mastery_handoff
from nexus_sandbox.knowledge_mastery_exchange import prepare_exchange
from nexus_sandbox.knowledge_mastery_history import reconcile_history

@dataclass(frozen=True)
class CycleDecision:
    status: str
    next_action: str
    mastery_level: int = 0
    provider_writes: int = 0
    constitutional_changes: int = 0

def prepare_learning_cycle(*, assessment, route_record, candidate,
                           recipient_modules, history_records,
                           active_constitution_revision,
                           archive_readback_verified=False,
                           cortex_authority_verified=False):
    """Prepare a candidate; never claim learning persisted or became authoritative."""
    if type(assessment) is not dict or type(candidate) is not dict:
        return CycleDecision("BLOCKED", "INVALID_ASSESSMENT_OR_CANDIDATE")
    if assessment.get("subject_id") != candidate.get("subject_id"):
        return CycleDecision("BLOCKED", "SUBJECT_BINDING_MISMATCH")
    if assessment.get("status") != "candidate_only":
        return CycleDecision("BLOCKED", "REQUIRE_CANDIDATE_ASSESSMENT")
    if assessment.get("demonstrated_level") != candidate.get("mastery_level"):
        return CycleDecision("BLOCKED", "MASTERY_LEVEL_MISMATCH")
    accepted = assessment.get("accepted_evaluation_ids")
    if type(accepted) is not list or not accepted or not set(candidate.get("evaluation_ids", [])) <= set(accepted):
        return CycleDecision("BLOCKED", "EVALUATION_BINDING_MISMATCH")
    handoff = prepare_mastery_handoff(
        assessment=assessment, route_record=route_record,
        archive_readback_verified=archive_readback_verified,
        cortex_authority_verified=cortex_authority_verified)
    if handoff.status != "CANDIDATE_ROUTED_NOT_PERSISTED":
        return CycleDecision("BLOCKED", "CORTEX_ROUTE:" + handoff.next_action)
    exchange = prepare_exchange(
        candidate=candidate, recipient_modules=recipient_modules,
        active_constitution_revision=active_constitution_revision)
    if exchange.status != "CANDIDATE_READY_FOR_REVIEW":
        return CycleDecision("BLOCKED", "EXCHANGE:" + exchange.reason)
    history = reconcile_history(
        records=history_records,
        active_constitution_revision=active_constitution_revision)
    if history.status != "CANDIDATE_ONLY":
        return CycleDecision("BLOCKED", "HISTORY:" + history.reason)
    return CycleDecision("CANDIDATE_READY_FOR_EXTERNAL_REVIEW",
                         "VERIFY_AUTHENTICATED_CORTEX_READBACK_BEFORE_PROMOTION",
                         assessment["demonstrated_level"])
