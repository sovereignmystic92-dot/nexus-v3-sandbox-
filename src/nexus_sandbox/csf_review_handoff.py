"""Durable offline handoffs between CSF intake and an independent reviewer."""

import json
from contextlib import closing
import sqlite3

from .csf_source_intake import prepare_findings, require_review_binding
from .csf_v02 import CSFValidationError


def prepare_handoff(database, batch_id, source_envelope, assignments=None):
    """Create or replay a frozen batch in a private host directory.

    A new batch requires explicit claim assignments. For edited wording, use
    a new batch ID and carry over the existing claim IDs. Replay recomputes
    the pending findings from the saved assignments and pinned source.
    """
    if not isinstance(batch_id, str) or not batch_id or batch_id != batch_id.strip():
        raise CSFValidationError("batch ID required")
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS csf_review_batches (
            batch_id TEXT PRIMARY KEY, assignments TEXT NOT NULL,
            payloads TEXT NOT NULL
        )""")
        db.execute("BEGIN IMMEDIATE")
        saved = db.execute(
            "SELECT assignments, payloads FROM csf_review_batches WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()
        if saved is not None:
            stored_assignments = json.loads(saved[0])
            if assignments is not None and assignments != stored_assignments:
                raise CSFValidationError("batch assignments conflict")
            findings = prepare_findings(source_envelope, stored_assignments)
            if findings != json.loads(saved[1]):
                raise CSFValidationError("batch source or payload conflict")
            return findings
        if assignments is None:
            raise CSFValidationError("unknown batch")
        findings = prepare_findings(source_envelope, assignments)
        db.execute(
            "INSERT INTO csf_review_batches VALUES (?, ?, ?)",
            (batch_id, json.dumps(assignments), json.dumps(findings)),
        )
        return findings


def require_batch_review_binding(findings, reviews):
    """Check full coverage of a frozen batch by submitted review references."""
    expected = {item["payload"]["finding_id"]: item for item in findings}
    if not expected or len(expected) != len(findings) or not isinstance(reviews, list):
        raise CSFValidationError("invalid review batch")
    seen = set()
    for review in reviews:
        if not isinstance(review, dict) or not isinstance(review.get("finding_id"), str):
            raise CSFValidationError("review finding ID required")
        finding_id = review["finding_id"]
        if finding_id not in expected or finding_id in seen:
            raise CSFValidationError("unexpected or duplicate review")
        require_review_binding(expected[finding_id], review)
        seen.add(finding_id)
    if seen != expected.keys():
        raise CSFValidationError("incomplete batch review")
