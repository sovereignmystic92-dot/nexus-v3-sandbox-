"""Bounded, pure PASSIVE/ACTIVE mission dispatcher; no execution or IO.

This module evaluates explicit trigger evidence and dependencies. It neither
polls for triggers nor starts research, writes, or schedules. The caller must
persist returned decisions in its own approved durable journal.
"""
from dataclasses import dataclass
import hashlib
import json

STATES = frozenset(("READY", "HOLD", "COMPLETE"))
MODES = frozenset(("PASSIVE", "ACTIVE"))


@dataclass(frozen=True)
class Mission:
    mission_id: str
    mode: str
    trigger: str
    dependencies: tuple
    steps: tuple
    max_steps: int = 12


def dispatch(mission, *, observed_triggers=(), satisfied_dependencies=(),
             verified_steps=(), blocked_steps=(), authorized_active=False):
    """Return one fail-closed, replay-stable continuation decision.

    Never infer evidence from presence of a task or previous response. A step
    only advances after independent verification is provided by the caller.
    """
    if type(mission) is not Mission or any(type(x) is not str or not x for x in (
            mission.mission_id, mission.mode, mission.trigger)):
        raise ValueError("Explicit mission identity, mode and trigger required")
    if mission.mode not in MODES or type(mission.max_steps) is not int or not 1 <= mission.max_steps <= 100:
        raise ValueError("Invalid mission mode or bound")
    for items in (mission.dependencies, mission.steps):
        if type(items) is not tuple or any(type(item) is not str or not item for item in items):
            raise ValueError("Explicit immutable mission contract required")
        if len(items) != len(set(items)):
            raise ValueError("Duplicate contract entries")
    if not mission.steps or len(mission.steps) > mission.max_steps:
        raise ValueError("Steps must be nonempty and within bound")
    for items in (observed_triggers, satisfied_dependencies, verified_steps, blocked_steps):
        if type(items) not in (tuple, frozenset) or any(type(item) is not str or not item for item in items):
            raise ValueError("Evidence must be an immutable string collection")
    if type(authorized_active) is not bool:
        raise ValueError("Active authorization must be explicit boolean")
    triggers, dependencies = set(observed_triggers), set(satisfied_dependencies)
    verified, blocked = set(verified_steps), set(blocked_steps)
    if (not verified.issubset(mission.steps) or not blocked.issubset(mission.steps)
            or verified & blocked or not dependencies.issubset(mission.dependencies)):
        raise ValueError("Conflicting or out-of-scope evidence")
    # Unknown triggers are ignored; only the declared trigger can start work.
    contract = dict(mission_id=mission.mission_id, mode=mission.mode,
                    trigger=mission.trigger, dependencies=mission.dependencies,
                    steps=mission.steps, max_steps=mission.max_steps)
    identity = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    def result(state, reason, next_action):
        return dict(schema="nexus.mission.dispatch.v1", mission_id=mission.mission_id,
                    contract_digest=identity, mode=mission.mode, state=state,
                    reason=reason, next_action=next_action,
                    verified_count=len(verified), total_steps=len(mission.steps),
                    authority="NON_EXECUTING_DECISION")
    if mission.trigger not in triggers:
        return result("HOLD", "TRIGGER_NOT_OBSERVED", "Wait for declared trigger evidence")
    if mission.mode == "ACTIVE" and not authorized_active:
        return result("HOLD", "ACTIVE_AUTHORIZATION_REQUIRED", "Obtain bounded active mission authorization")
    missing = tuple(dep for dep in mission.dependencies if dep not in dependencies)
    if missing:
        return result("HOLD", "DEPENDENCIES_UNMET", "Verify dependency: " + missing[0])
    if blocked:
        first = next(step for step in mission.steps if step in blocked)
        return result("HOLD", "STEP_BLOCKED", "Reconcile blocked step: " + first)
    for step in mission.steps:
        if step not in verified:
            return result("READY", "NEXT_STEP_REQUIRES_EXECUTOR_AND_READBACK",
                          "Execute bounded step and independently verify: " + step)
    return result("COMPLETE", "ALL_STEPS_VERIFIED", "No remaining steps")
