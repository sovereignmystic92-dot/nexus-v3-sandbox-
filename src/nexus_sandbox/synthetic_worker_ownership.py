"""Single-host, advisory ownership for the *synthetic* mission executor.

POSIX flock prevents two cooperating local processes from advancing the same
mission concurrently. This is NOT a distributed lease, fencing token, or
authorization for live effects. The file must never be unlinked during use.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import stat


@contextmanager
def local_mission_ownership(folder, mission_id):
    if type(mission_id) is not str or not mission_id:
        raise ValueError("Explicit mission identity required")
    folder = Path(folder)
    directory = folder.lstat()
    if (not folder.is_absolute() or folder.is_symlink()
            or not stat.S_ISDIR(directory.st_mode)
            or directory.st_mode & 0o077 or directory.st_uid != os.getuid()):
        raise ValueError("Private owned absolute directory required")
    name = hashlib.sha256(mission_id.encode()).hexdigest() + ".owner.lock"
    path = folder / name
    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        location = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid() or info.st_mode & 0o077
                or (info.st_dev, info.st_ino) != (location.st_dev, location.st_ino)):
            raise ValueError("Unsafe or replaced ownership file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Mission already owned by another local worker: HOLD") from exc
        # Recheck the pathname after acquiring the lock to reject replacement.
        location = path.lstat()
        if (info.st_dev, info.st_ino) != (location.st_dev, location.st_ino):
            raise ValueError("Ownership pathname changed: HOLD")
        yield
    finally:
        # Close releases the OS lock on process death as well as normal exit.
        # Intentionally retain the lock file: unlink/recreate splits ownership.
        os.close(fd)


def locally_serialized_advance(fn):
    """Decorate a bounded synthetic executor, keeping every execution fenced
    by a local advisory lock from preflight through journal commit/readback."""
    from functools import wraps

    @wraps(fn)
    def owned(journal, mission, folder, **kwargs):
        with local_mission_ownership(folder, mission.mission_id):
            return fn(journal, mission, folder, **kwargs)

    return owned
