"""Single-host assignment guard for an owner-invoked transcript publication."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat


@contextmanager
def hold_supervised_assignment(*, lock_dir, owner, output_name, read_assignment):
    """Hold the destination lock while verifying an authoritative assignment.

    The trusted host supplies a private, shared local lock directory and a
    fresh reader of its owner-assignment record. All writers for this
    destination must be confined to the same host and honor this lock.
    """
    if any(type(value) is not str or not value.strip() for value in (owner, output_name)):
        raise ValueError("Exact destination owner and output name required")
    if not callable(read_assignment):
        raise ValueError("Authoritative assignment reader required")

    binding = {"owner": owner, "output_name": output_name}
    key = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(Path(lock_dir), flags)
    try:
        metadata = os.fstat(directory)
        if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            raise PermissionError("Private host lock directory required")
        fd = os.open(key + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        try:
            metadata = os.fstat(fd)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
                    or metadata.st_mode & 0o077 or metadata.st_nlink != 1):
                raise PermissionError("Private regular destination lock required")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            active = True

            def verify_assignment(expected):
                if not active:
                    raise PermissionError("Destination lock is no longer held")
                fields = {"mode", "transaction_id", "assignment_id", "actor"}
                if (type(expected) is not dict or set(expected) != fields
                        or expected["mode"] != "OWNER_INVOKED_SUPERVISED"
                        or any(type(value) is not str or not value.strip()
                               for value in expected.values())):
                    raise PermissionError("Exact owner-invoked assignment required")
                observed = read_assignment()
                if observed != {**binding, **expected}:
                    raise PermissionError("Current owner assignment does not match the destination")
                return {key: observed[key] for key in expected}

            try:
                yield verify_assignment
            finally:
                active = False
        finally:
            os.close(fd)
    finally:
        os.close(directory)
