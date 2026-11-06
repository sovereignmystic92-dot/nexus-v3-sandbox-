"""Record bounded agent-routing proposals in an existing Nexus SQLite journal.

No agent execution or remote side effect. Routing proposals have their own
immutable rows tied to an existing, already-committed mission decision revision.
The caller must authenticate roster/trigger evidence independently.
"""
from contextlib import closing
import json

from .mission_journal import MissionJournal, _canonical
from .mission_dispatcher import Mission
from .agent_routing import route_mission


def provision_routing_records(journal):
    """Explicit one-time schema extension; never create or replace a journal."""
    if type(journal) is not MissionJournal:
        raise ValueError("Existing mission journal required")
    with closing(journal._connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        journal._validate(db)
        db.execute(
            "CREATE TABLE IF NOT EXISTS routing_proposals("
            "mission_id TEXT NOT NULL, revision INTEGER NOT NULL,"
            "payload TEXT NOT NULL, PRIMARY KEY(mission_id, revision))"
        )
        db.commit()


def _evidence_args(entry):
    evidence = entry["evidence"]
    return dict(observed_triggers=tuple(evidence["trigger"]),
                satisfied_dependencies=tuple(evidence["dependencies"]),
                verified_steps=tuple(evidence["verified"]),
                blocked_steps=tuple(evidence["blocked"]),
                authorized_active=evidence["active"])


def record_routing_proposal(journal, mission, *, required_skills, agents,
                            expected_revision):
    """Pin routing decision to one committed journal revision.

    A previous identical entry replays idempotently; a changed roster,
    authorization claim or skill requirement for the same revision HOLDS.
    New routing after changed evidence requires a newly committed journal
    revision; no executing permission is conferred.
    """
    if type(journal) is not MissionJournal or type(mission) is not Mission:
        raise ValueError("Explicit journal and mission required")
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("Existing journal revision required")
    with closing(journal._connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        journal._validate(db)
        rows = journal._history(db, mission.mission_id)
        if not rows or len(rows) != expected_revision:
            raise ValueError("Stale or missing mission revision: HOLD")
        entry = json.loads(rows[-1][1])
        decision = route_mission(mission, required_skills=required_skills,
                                 agents=agents, **_evidence_args(entry))
        if (entry["decision"]["contract_digest"] != decision["contract_digest"]
                or entry["decision"]["state"] == "COMPLETE"
                and decision["state"] != "COMPLETE"):
            raise ValueError("Contract/decision mismatch: HOLD")
        candidate = dict(mission_id=mission.mission_id, revision=expected_revision,
                         journal_entry_hash=rows[-1][3], routing=decision)
        payload = _canonical(candidate)
        try:
            existing = db.execute(
                "SELECT payload FROM routing_proposals WHERE mission_id=? AND revision=?",
                (mission.mission_id, expected_revision)).fetchone()
        except Exception as exc:
            raise ValueError("Routing journal not provisioned: HOLD") from exc
        if existing:
            if existing[0] != payload:
                raise ValueError("Conflicting routing proposal for revision: HOLD")
            db.commit()
            return json.loads(existing[0])
        db.execute("INSERT INTO routing_proposals VALUES (?,?,?)",
                   (mission.mission_id, expected_revision, payload))
        db.commit()
    saved = observe_routing_proposal(journal, mission.mission_id, expected_revision)
    if saved != candidate:
        raise ValueError("Routing journal readback mismatch: HOLD")
    return saved


def observe_routing_proposal(journal, mission_id, revision):
    """Read back proposal, verifying its pinned decision-chain hash."""
    if (type(journal) is not MissionJournal or type(mission_id) is not str
            or not mission_id or type(revision) is not int or revision < 1):
        raise ValueError("Valid journal, mission and revision required")
    with closing(journal._connect()) as db:
        journal._validate(db)
        rows = journal._history(db, mission_id)
        if len(rows) < revision:
            raise ValueError("Mission revision missing: HOLD")
        result = db.execute(
            "SELECT payload FROM routing_proposals WHERE mission_id=? AND revision=?",
            (mission_id, revision)).fetchone()
        if not result:
            return None
        item = json.loads(result[0])
        if (_canonical(item) != result[0] or
                item.get("mission_id") != mission_id or
                item.get("revision") != revision or
                item.get("journal_entry_hash") != rows[revision - 1][3]):
            raise ValueError("Routing proposal mismatch: HOLD")
        return item
