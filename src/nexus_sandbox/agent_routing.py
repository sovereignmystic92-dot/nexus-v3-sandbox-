"""Pure, fail-closed lead/reviewer choice for Nexus sandbox missions.

This produces a recommendation only, never a credential grant, event dispatch,
Gemini request, external write, or audit checkpoint promotion.
"""
from dataclasses import dataclass
import hashlib
import json

from .mission_dispatcher import Mission, dispatch


@dataclass(frozen=True)
class AgentCapability:
    name: str
    skills: tuple
    available: bool
    approved: bool


def route_mission(mission, *, required_skills, agents, observed_triggers=(),
                  satisfied_dependencies=(), verified_steps=(),
                  blocked_steps=(), authorized_active=False):
    """Choose a qualified lead and a distinct qualified reviewer.

    Sort by skills matched beyond the required minimum, then by agent name,
    so caller iteration order cannot change a decision. The coordinator
    remains ChatGPT. Caller assertions about agent availability and approvals
    are not authenticated by this pure function.
    """
    if type(mission) is not Mission or type(required_skills) is not tuple or not required_skills:
        raise ValueError("Explicit mission and required skills")
    if any(type(s) is not str or not s for s in required_skills) or len(set(required_skills)) != len(required_skills):
        raise ValueError("Invalid required skill set")
    if type(agents) is not tuple or not agents:
        raise ValueError("Explicit agent roster required")
    names = set()
    for agent in agents:
        if (type(agent) is not AgentCapability or type(agent.name) is not str or not agent.name
                or type(agent.skills) is not tuple or
                any(type(s) is not str or not s for s in agent.skills)
                or len(agent.skills) != len(set(agent.skills))
                or type(agent.available) is not bool or type(agent.approved) is not bool
                or agent.name in names):
            raise ValueError("Invalid or duplicate agent capability")
        names.add(agent.name)
    decision = dispatch(mission, observed_triggers=observed_triggers,
                        satisfied_dependencies=satisfied_dependencies,
                        verified_steps=verified_steps, blocked_steps=blocked_steps,
                        authorized_active=authorized_active)
    eligible = tuple(a for a in agents if a.available and a.approved
                     and set(required_skills).issubset(a.skills))
    ranked = sorted(eligible, key=lambda a: (-len(a.skills), a.name))
    lead = ranked[0].name if len(ranked) >= 1 else None
    reviewer = ranked[1].name if len(ranked) >= 2 else None
    if decision["state"] == "READY" and not lead:
        state, reason = "HOLD", "NO_APPROVED_QUALIFIED_LEAD"
    elif decision["state"] == "READY" and not reviewer:
        state, reason = "HOLD", "NO_DISTINCT_QUALIFIED_REVIEWER"
    else:
        state, reason = decision["state"], decision["reason"]
    roster = [dict(name=a.name, skills=sorted(a.skills),
                   available=a.available, approved=a.approved)
              for a in sorted(agents, key=lambda x: x.name)]
    provenance = dict(mission=decision["contract_digest"],
                      required_skills=sorted(required_skills), roster=roster)
    digest = hashlib.sha256(json.dumps(provenance, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
    return dict(schema="nexus.agent-routing.v1", coordinator="ChatGPT",
                mission_id=mission.mission_id, contract_digest=decision["contract_digest"],
                routing_digest=digest, state=state, reason=reason,
                lead=lead if state == "READY" else None,
                reviewer=reviewer if state == "READY" else None,
                next_action=decision["next_action"] if state == "READY"
                else "Record HOLD and obtain verified prerequisites",
                authority="NON_EXECUTING_PROPOSAL", external_calls=0)
