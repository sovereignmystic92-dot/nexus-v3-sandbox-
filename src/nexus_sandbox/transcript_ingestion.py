"""Fail-closed, local transcript ingestion checkpoints.

This module DOES NOT invoke Notion/Cortex/GitHub, hold tokens, or schedule work.
A trusted host must execute steps and independently supply provider readback.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

STAGES = ("SOURCE_RECEIVED", "NOTION_ARCHIVE_VERIFIED",
          "ANALYSIS_COMPLETED", "CORTEX_OUTPUT_VERIFIED",
          "RECEIPT_RECORDED")
STATUSES = frozenset(("NOT_STARTED", "COMPLETE", "PARTIAL", "BLOCKED"))
MAX_EVIDENCE = 16384


def source_id(provider: str, external_id: str) -> str:
    """Stable idempotency key; currently supports only immutable YouTube IDs."""
    if provider != "youtube" or not isinstance(external_id, str):
        raise ValueError("Source identity must be youtube:<video_id>")
    if len(external_id) != 11 or not all(c.isascii() and
            (c.isalnum() or c in "_-") for c in external_id):
        raise ValueError("Invalid YouTube video identifier")
    return "youtube:" + external_id


def digest_source(transcript: str) -> str:
    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError("Nonempty raw transcript required")
    return hashlib.sha256(transcript.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Checkpoint:
    source: str
    stage: str
    status: str
    verified: bool
    evidence: dict
    recorded_at: str


class TranscriptCoordinator:
    """SQLite journal with monotonic, readback-gated transitions.

    Use one coordinator per durable DB. Callers own external provider actions.
    A retry must use exactly the same transcript hash, preventing silent source
    replacement when a URL is reused.
    """

    def __init__(self, path: str):
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=15000")
        self.db.execute("CREATE TABLE IF NOT EXISTS source (id TEXT PRIMARY KEY,"
                        " raw_sha256 TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS checkpoint ("
                        "source TEXT NOT NULL, stage TEXT NOT NULL,"
                        "status TEXT NOT NULL, verified INTEGER NOT NULL,"
                        "evidence_json TEXT NOT NULL, recorded_at TEXT NOT NULL,"
                        "PRIMARY KEY(source,stage),"
                        "FOREIGN KEY(source) REFERENCES source(id))")
        self.db.execute("PRAGMA foreign_keys=ON")

    def close(self) -> None:
        self.db.close()

    def receive(self, video_id: str, transcript: str) -> str:
        key = source_id("youtube", video_id)
        sha = digest_source(transcript)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT raw_sha256 FROM source WHERE id=?",
                                       (key,)).fetchone()
            if existing is not None and existing[0] != sha:
                raise ValueError("Conflicting transcript: no silent overwrite")
            if existing is None:
                self.db.execute("INSERT INTO source VALUES (?,?)", (key, sha))
                self._save(key, STAGES[0], "COMPLETE", True,
                           {"raw_sha256": sha, "source_url":
                            "https://youtu.be/" + video_id})
            self.db.execute("COMMIT")
            return key
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _save(self, key, stage, status, verified, evidence):
        payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        self.db.execute("INSERT INTO checkpoint VALUES (?,?,?,?,?,?) "
                        "ON CONFLICT(source,stage) DO UPDATE SET "
                        "status=excluded.status, verified=excluded.verified,"
                        "evidence_json=excluded.evidence_json,"
                        "recorded_at=excluded.recorded_at",
                        (key, stage, status, int(verified), payload,
                         datetime.now(timezone.utc).isoformat()))

    def record(self, key: str, stage: str, status: str, evidence: dict,
               *, independently_read_back: bool = False) -> Checkpoint:
        """Accept a verified success ONLY with explicit provider readback evidence.

        Caller must conduct the readback independently. This library cannot
        attest to the caller's identity or the truth of external receipts.
        """
        if stage not in STAGES[1:] or status not in STATUSES:
            raise ValueError("Invalid stage or status")
        if type(evidence) is not dict:
            raise ValueError("Evidence must be a dictionary")
        payload = json.dumps(evidence, sort_keys=True, allow_nan=False)
        if len(payload.encode("utf-8")) > MAX_EVIDENCE:
            raise ValueError("Evidence exceeds maximum size")
        if status == "COMPLETE":
            if independently_read_back is not True:
                raise ValueError("COMPLETE requires independently read-back proof")
            if not isinstance(evidence.get("destination"), str) or not evidence["destination"]:
                raise ValueError("COMPLETE requires a destination identifier")
            if not isinstance(evidence.get("readback"), str) or not evidence["readback"]:
                raise ValueError("COMPLETE requires readback reference")
        else:
            if independently_read_back:
                raise ValueError("Non-complete state cannot assert readback")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            src = self.db.execute("SELECT 1 FROM source WHERE id=?", (key,)).fetchone()
            if src is None:
                raise ValueError("Unknown source")
            i = STAGES.index(stage)
            prior = self.db.execute("SELECT status,verified FROM checkpoint "
                                    "WHERE source=? AND stage=?", (key, stage)).fetchone()
            if prior and prior == ("COMPLETE", 1):
                if status != "COMPLETE":
                    raise ValueError("Verified stage cannot be downgraded")
                existing = self.get(key, stage)
                self.db.execute("COMMIT")
                return existing
            if status == "COMPLETE":
                predecessor = self.db.execute(
                    "SELECT status,verified FROM checkpoint WHERE source=? AND stage=?",
                    (key, STAGES[i-1])).fetchone()
                if predecessor != ("COMPLETE", 1):
                    raise ValueError("Previous stage not independently verified")
            self._save(key, stage, status, status == "COMPLETE", evidence)
            result = self.get(key, stage)
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def get(self, key: str, stage: str) -> Checkpoint | None:
        row = self.db.execute("SELECT status,verified,evidence_json,recorded_at "
                              "FROM checkpoint WHERE source=? AND stage=?",
                              (key, stage)).fetchone()
        if row is None:
            return None
        return Checkpoint(key, stage, row[0], bool(row[1]),
                          json.loads(row[2]), row[3])

    def next_stage(self, key: str) -> str | None:
        if not self.db.execute("SELECT 1 FROM source WHERE id=?", (key,)).fetchone():
            raise ValueError("Unknown source")
        for stage in STAGES[1:]:
            row = self.get(key, stage)
            if row is None or row.status != "COMPLETE" or not row.verified:
                return stage
        return None

    def receipt(self, key: str) -> dict:
        if not self.db.execute("SELECT 1 FROM source WHERE id=?", (key,)).fetchone():
            raise ValueError("Unknown source")
        steps = {stage: self.get(key, stage) for stage in STAGES}
        return {"source": key, "next_stage": self.next_stage(key),
                "status": "COMPLETE" if self.next_stage(key) is None else "INCOMPLETE",
                "stages": {stage: {"status": cp.status, "verified": cp.verified,
                         "evidence": cp.evidence} if cp else
                         {"status": "NOT_STARTED", "verified": False, "evidence": {}}
                         for stage, cp in steps.items()}}
