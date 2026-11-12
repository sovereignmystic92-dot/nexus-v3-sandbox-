"""Read-only Knowledge Mastery -> Cortex handoff preparation.

This adapter prepares a candidate only. It cannot grant permission, create a
Cortex module, certify an independent review, or claim a provider readback.
"""
from dataclasses import dataclass
from nexus_sandbox.output_authority import validate_output_route


@dataclass(frozen=True)
class MasteryHandoffDecision:
    status: str
    next_action: str
    demonstrated_level: int = 0
    provider_writes: int = 0
    completion_verified: bool = False


def prepare_mastery_handoff(*, assessment, route_record,
                           archive_readback_verified=False,
                           cortex_authority_verified=False):
    def blocked(action):
        return MasteryHandoffDecision("BLOCKED", action)
    if type(assessment) is not dict or assessment.get("status") != "candidate_only":
        return blocked("RECONCILE_MASTERY_ASSESSMENT")
    level = assessment.get("demonstrated_level")
    if type(level) is not int or not 1 <= level <= 6:
        return blocked("REQUIRE_EVIDENCE_BACKED_MASTERY")
    if not assessment.get("accepted_evaluation_ids"):
        return blocked("REQUIRE_ACCEPTED_EVALUATION")
    if type(archive_readback_verified) is not bool or type(cortex_authority_verified) is not bool:
        return blocked("VERIFY_TRUSTED_HOST_ASSERTIONS")
    verdict = validate_output_route(
        route_record,
        archive_readback_verified=archive_readback_verified,
        cortex_authority_verified=cortex_authority_verified,
        cortex_output_readback_verified=False,
    )
    if verdict.status != "ROUTED_NOT_COMPLETE":
        return blocked(verdict.next_action)
    return MasteryHandoffDecision(
        "CANDIDATE_ROUTED_NOT_PERSISTED",
        "REQUIRE_EXISTING_CORTEX_PROMOTION_GATE_AND_AUTHENTICATED_READBACK",
        level,
    )
