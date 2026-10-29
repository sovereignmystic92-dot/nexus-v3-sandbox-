"""Read-only custody preflight for an existing, private Nexus SQLite journal.

A successful preflight establishes local file/schema observations only.
It is NOT cross-host fencing, backup validation, or power-loss durability.
"""
import os
from pathlib import Path
import sqlite3
import stat


def inspect_journal(path, expected_identity):
    """Fail closed without initializing, replacing, or repairing the journal."""
    if type(path) not in (str, Path) or type(expected_identity) is not str or not expected_identity:
        raise ValueError("Explicit journal and identity required")
    path = Path(path)
    if not path.is_absolute() or path.name in (".", "..") or path.parent == path:
        raise ValueError("Absolute existing journal path required")
    parent = path.parent
    folder = parent.lstat()
    if not stat.S_ISDIR(folder.st_mode) or folder.st_mode & 0o077:
        raise ValueError("Private real journal directory required")
    journal = path.lstat()   # Missing journals must not be recreated.
    if (not stat.S_ISREG(journal.st_mode) or journal.st_mode & 0o077
            or journal.st_nlink != 1 or journal.st_uid != os.getuid()):
        raise ValueError("Private single-link owned journal required")
    lock = Path(str(path) + ".lock")
    if lock.exists() or lock.is_symlink():
        ls = lock.lstat()
        if (not stat.S_ISREG(ls.st_mode) or ls.st_mode & 0o077
                or ls.st_nlink != 1 or ls.st_uid != os.getuid()):
            raise ValueError("Unsafe journal lock")
    # mode=ro prevents SQLite from creating a missing file or journal.
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ValueError("Journal integrity check failed")
        rows = db.execute("SELECT identity, config FROM runner_identity").fetchall()
        if len(rows) != 1 or rows[0][0] != expected_identity or not rows[0][1]:
            raise ValueError("Journal identity mismatch")
        inbox = db.execute("SELECT state, COUNT(*) FROM runner_inbox GROUP BY state").fetchall()
        if any(state not in ("PENDING", "HOLD", "VERIFIED") for state, _ in inbox):
            raise ValueError("Unknown journal inbox state")
    return {
        "status": "OBSERVED_EXISTING",
        "identity_match": True,
        "integrity": "ok",
        "pending_or_held": sum(count for state, count in inbox if state != "VERIFIED"),
        "verified": sum(count for state, count in inbox if state == "VERIFIED"),
        "limitations": "single-host-local-preflight-only",
    }
