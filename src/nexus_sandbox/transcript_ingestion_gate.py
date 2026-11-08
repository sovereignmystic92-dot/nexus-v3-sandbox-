"""Provider-neutral transcript ingestion gate. No network or write capability."""
from nexus_sandbox.transcript_fidelity import build_receipt, split_transcript, verify_readback


def prepare_transcript(raw, chunk_bytes=12000):
    """Return exact chunks and immutable-content receipt for a supplied source."""
    receipt = build_receipt(raw, chunk_bytes)
    return {"schema": "nexus.transcript-ingestion-gate.v1",
            "receipt": receipt, "chunks": split_transcript(raw, chunk_bytes),
            "state": "AWAITING_ARCHIVE_READBACK",
            "cortex_write_allowed": False, "audit_promotion": False}


def verify_archive(prepared, readback_chunks):
    """Fail closed; emit a non-authorizing verification decision."""
    if not isinstance(prepared, dict) or prepared.get("schema") != "nexus.transcript-ingestion-gate.v1":
        raise ValueError("invalid prepared ingestion")
    chunks, receipt = prepared.get("chunks"), prepared.get("receipt")
    if not isinstance(chunks, list) or not all(isinstance(x, str) for x in chunks):
        raise ValueError("missing original chunks")
    original = "".join(chunks)
    valid = (build_receipt(original, receipt.get("chunk_bytes")) == receipt
             and verify_readback(original, readback_chunks, receipt))
    return {"source_sha256": receipt["sha256"], "archive_readback_verified": bool(valid),
            "state": "ARCHIVE_VERIFIED" if valid else "BLOCKED_ARCHIVE_MISMATCH",
            "cortex_write_allowed": False, "audit_promotion": False,
            "next_step": "BOUNDED_DERIVED_REVIEW" if valid else None}



def plan_archive_resume(prepared, destination, observation, *, expected_source_sha256):
    """Plan a single-worker retry from a complete, fresh host readback.

    The host pins destination/source independently, authenticates and paginates
    the observation, and serializes writes. None means unknown outcome: read
    again, never blindly append. This pure planner grants no write authority.
    """
    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("pinned destination required")
    if not isinstance(prepared, dict):
        raise ValueError("invalid prepared ingestion")
    receipt = prepared.get("receipt")
    chunks = prepared.get("chunks")
    if (not isinstance(receipt, dict) or not isinstance(chunks, list)
            or not chunks or not all(isinstance(c, str) for c in chunks)):
        raise ValueError("invalid prepared source")
    if type(receipt.get("chunk_bytes")) is not int:
        raise ValueError("invalid chunk size")
    if (prepared.get("schema") != "nexus.transcript-ingestion-gate.v1"
            or build_receipt("".join(chunks), receipt["chunk_bytes"]) != receipt
            or split_transcript("".join(chunks), receipt["chunk_bytes"]) != chunks
            or receipt.get("sha256") != expected_source_sha256):
        raise ValueError("source does not match pinned receipt")
    result = {"source_sha256": expected_source_sha256,
              "destination": destination, "missing_chunks": [],
              "archive_readback_verified": False,
              "provider_writes_allowed": False, "cortex_write_allowed": False,
              "audit_promotion": False}
    if observation is None:
        return dict(result, state="READBACK_REQUIRED")
    if (not isinstance(observation, dict)
            or observation.get("complete") is not True
            or observation.get("destination") != destination
            or observation.get("source_sha256") != expected_source_sha256
            or not isinstance(observation.get("chunks"), list)):
        raise ValueError("complete destination-bound readback required")
    seen, previous = set(), -1
    for item in observation["chunks"]:
        if not isinstance(item, dict):
            raise ValueError("invalid observed chunk")
        index = item.get("index")
        if (type(index) is not int or not 0 <= index < len(chunks)
                or index in seen or index <= previous
                or item.get("text") != chunks[index]):
            raise ValueError("conflicting, duplicate or unordered chunk")
        seen.add(index)
        previous = index
    missing = [{"index": i, "text": c} for i, c in enumerate(chunks) if i not in seen]
    if missing:
        return dict(result, state="MISSING_CHUNKS", missing_chunks=missing)
    # Preserve provider order rather than sorting away storage mistakes.
    verified = verify_archive(prepared, [c["text"] for c in observation["chunks"]])
    if not verified["archive_readback_verified"]:
        raise ValueError("full readback mismatch")
    return dict(result, state="ARCHIVE_VERIFIED", archive_readback_verified=True)


class ArchiveRecoveryHost:
    """Bounded host wiring; injected provider ports, owned Linux state directory.

    Reader must authenticate and return a complete, strongly consistent snapshot.
    Writer must preserve index order. Authorizer must check current effective
    grants for the exact destination/source/index. No built-in provider or token.
    """

    def __init__(self, journal_path):
        self.path = journal_path

    def attempt(self, prepared, destination, *, expected_source_sha256,
                read_archive, write_chunk, authorize_write, confirm_absent=None):
        """Read/reconcile, at most one write, then read/verify; never trust ACKs.

        A local advisory lock spans the attempt and releases on process death.
        All workers on this host must use this same journal path. Remote workers
        and uncooperative writers require separate provider fencing.
        """
        import fcntl
        import json
        import sqlite3

        # Copy caller-owned structures so callbacks cannot silently change source.
        prepared = json.loads(json.dumps(prepared))
        plan_archive_resume(prepared, destination, None,
                            expected_source_sha256=expected_source_sha256)
        binding = json.dumps({"destination": destination, "prepared": prepared,
                              "source_sha256": expected_source_sha256}, sort_keys=True)
        with open(str(self.path) + ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            db = sqlite3.connect(self.path)
            try:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("CREATE TABLE IF NOT EXISTS archive_binding "
                           "(singleton INTEGER PRIMARY KEY CHECK(singleton=1), binding TEXT NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS archive_events "
                           "(id INTEGER PRIMARY KEY, state TEXT NOT NULL, chunk_index INTEGER)")
                prior = db.execute("SELECT binding FROM archive_binding WHERE singleton=1").fetchone()
                if prior is not None and prior[0] != binding:
                    raise ValueError("journal source/destination binding changed")
                if prior is None:
                    db.execute("INSERT INTO archive_binding VALUES (1,?)", (binding,))
                    db.commit()

                def record(state, index=None):
                    db.execute("INSERT INTO archive_events(state,chunk_index) VALUES (?,?)",
                               (state, index))
                    db.commit()

                def observe():
                    record("READBACK_REQUIRED")
                    observation = read_archive(destination, expected_source_sha256)
                    decision = plan_archive_resume(
                        prepared, destination, observation,
                        expected_source_sha256=expected_source_sha256)
                    record(decision["state"])
                    return decision

                decision = observe()
                if decision["state"] != "MISSING_CHUNKS":
                    return decision
                item = decision["missing_chunks"][0]
                last_intent = db.execute(
                    "SELECT chunk_index FROM archive_events WHERE state='WRITE_INTENT' "
                    "ORDER BY id DESC LIMIT 1").fetchone()
                if last_intent and any(c["index"] == last_intent[0]
                                       for c in decision["missing_chunks"]):
                    # Absence in a snapshot alone cannot rule out a delayed
                    # earlier write. Require host proof of settled non-commit.
                    if (confirm_absent is None or confirm_absent(
                            destination, expected_source_sha256, last_intent[0]) is not True):
                        record("BLOCKED_UNCERTAIN_WRITE", last_intent[0])
                        raise ValueError("prior write unresolved; absence is not proof of non-commit")
                if authorize_write(destination, expected_source_sha256, item["index"]) is not True:
                    record("BLOCKED_AUTHORIZATION", item["index"])
                    raise PermissionError("exact chunk write not authorized")
                # Durable intent precedes external side effect. Any exception or
                # process death leaves recovery dependent on a new provider read.
                record("WRITE_INTENT", item["index"])
                try:
                    write_chunk(destination, expected_source_sha256,
                                item["index"], item["text"])
                except Exception:
                    record("WRITE_OUTCOME_UNKNOWN", item["index"])
                    raise
                return observe()
            finally:
                db.close()
