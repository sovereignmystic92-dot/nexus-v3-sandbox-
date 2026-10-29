"""Bounded file-fixture executor and independent reader for sandbox missions.

NO external tool callbacks, network access, scheduler or live effect pathway.
Each advance handles at most one synthetic step. The journal, not this fixture,
owns the recorded continuation. A fixture receipt is not real-world proof.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from .mission_dispatcher import Mission, dispatch
from .mission_journal import MissionJournal


def _private_dir(folder):
    folder = Path(folder)
    info = folder.lstat()
    if (not folder.is_absolute() or folder.is_symlink()
            or not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077
            or info.st_uid != os.getuid()):
        raise ValueError("Private absolute fixture directory required")
    return folder


def _receipt_bytes(mission_id, contract_digest, step):
    return json.dumps(dict(schema="nexus.synthetic.step.v1", mission=mission_id,
                           contract=contract_digest, step=step),
                      sort_keys=True, separators=(",", ":")).encode()


def _receipt_path(folder, mission_id, contract_digest, step):
    identifier = hashlib.sha256(
        json.dumps([mission_id, contract_digest, step], separators=(",", ":")).encode()
    ).hexdigest()
    return _private_dir(folder) / (identifier + ".receipt")


def _check_receipt(path, expected):
    """Fresh independent local readback; failures never mean absence."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_mode & 0o077 or info.st_uid != os.getuid()):
        raise ValueError("Unsafe receipt")
    if path.read_bytes() != expected:
        raise ValueError("Receipt content mismatch")
    return True


def write_synthetic_receipt(folder, mission_id, contract_digest, step):
    """Idempotent local fixture effect; never overwrite a conflicting receipt."""
    expected = _receipt_bytes(mission_id, contract_digest, step)
    path = _receipt_path(folder, mission_id, contract_digest, step)
    if _check_receipt(path, expected):
        return path
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if _check_receipt(path, expected):
            return path
        raise ValueError("Receipt collision requires HOLD")
    with os.fdopen(fd, "wb") as f:
        f.write(expected)
        f.flush()
        os.fsync(f.fileno())
    # Directory fsync flushes the new name on supporting local filesystems.
    directory_fd = os.open(_private_dir(folder), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return path


def advance_synthetic(journal, mission, folder, *, observed_triggers=(),
                      satisfied_dependencies=(), authorized_active=False,
                      expected_revision=0, after_fixture_write=None):
    """One bounded step; after_fixture_write is test-only crash injection.

    The *caller* must establish authorization/trigger provenance separately.
    No step runs when prerequisites are unresolved. If interrupted after writing
    a fixture but before journaling, next invocation reads the existing receipt.
    """
    if type(journal) is not MissionJournal or type(mission) is not Mission:
        raise ValueError("Bounded mission journal and contract required")
    if mission.mode != "PASSIVE":
        raise ValueError("ACTIVE fixture execution unsupported")
    if authorized_active or after_fixture_write not in (None, "INTERRUPT"):
        raise ValueError("Unexpected execution control")
    _private_dir(folder)
    prior = journal.observe(mission.mission_id)
    if prior:
        if type(expected_revision) is not int or prior["revision"] != expected_revision:
            raise ValueError("Stale mission revision")
        evidence = prior["evidence"]
        verified = tuple(evidence["verified"])
        blocked = tuple(evidence["blocked"])
        if blocked:
            raise ValueError("Blocked mission requires separate reconciliation")
    else:
        verified, blocked = (), ()
    decision = dispatch(mission, observed_triggers=observed_triggers,
                        satisfied_dependencies=satisfied_dependencies,
                        verified_steps=verified, blocked_steps=blocked)
    if decision["state"] != "READY":
        return journal.record(mission, observed_triggers=observed_triggers,
                              satisfied_dependencies=satisfied_dependencies,
                              verified_steps=verified, blocked_steps=blocked,
                              expected_revision=expected_revision)
    step = next(step for step in mission.steps if step not in verified)
    path = write_synthetic_receipt(folder, mission.mission_id,
                                   decision["contract_digest"], step)
    if after_fixture_write == "INTERRUPT":
        raise InterruptedError("Synthetic crash after fixture effect, before journal")
    if not _check_receipt(path, _receipt_bytes(mission.mission_id,
                                              decision["contract_digest"], step)):
        raise ValueError("Missing independent fixture readback")
    # Record the independently observed proof; no direct promotion by executor.
    return journal.record(mission, observed_triggers=observed_triggers,
                          satisfied_dependencies=satisfied_dependencies,
                          verified_steps=verified + (step,),
                          blocked_steps=blocked, expected_revision=expected_revision)
