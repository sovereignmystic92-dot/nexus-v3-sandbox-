"""Durable cleanup handoff for one owned sandbox run on a surviving host.

Journal custody must outlive its targets. This is not host-loss recovery, remote
storage, concurrent-worker fencing, or authority to delete arbitrary paths.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
from contextlib import closing


class CleanupHold(RuntimeError):
    pass


STEPS = ('REMOVE_CONTAINER', 'REMOVE_STAGING', 'REMOVE_NAMESPACE')


def identity(path):
    p = Path(path)
    if not p.is_absolute() or p.resolve() != p:
        raise CleanupHold('Absolute non-symlink resource path required')
    s = p.lstat()
    if not stat.S_ISDIR(s.st_mode):
        raise CleanupHold('Owned directory required')
    return [s.st_dev, s.st_ino]


class CleanupJournal:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink() or not self.path.is_file():
            raise CleanupHold('Existing regular cleanup journal required')
        with closing(self.connect()) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise CleanupHold('Cleanup journal storage integrity failure')
            self.binding = json.loads(db.execute('SELECT data FROM binding').fetchone()[0])
        self._validate_binding()
        self.snapshot()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        return db

    @classmethod
    def create(cls, path, *, run_id, source_sha, container_name, container_id,
               namespace, staging):
        path, namespace, staging = Path(path), Path(namespace), Path(staging)
        if (not isinstance(run_id, str) or not run_id or len(run_id) > 200 or
                not re.fullmatch('[0-9a-f]{40}', source_sha) or
                not re.fullmatch('nexus-acceptance-[0-9a-f]{32}', container_name) or
                not re.fullmatch('[0-9a-f]{64}', container_id) or
                namespace.name.startswith('nexus-supervisor-') is False or
                staging.parent != namespace or not staging.name.startswith('nexus-isolated-')):
            raise CleanupHold('Exact owned-run bindings required')
        ns_id, stage_id = identity(namespace), identity(staging)
        if not path.is_absolute() or path.parent.resolve() != path.parent:
            raise CleanupHold('Explicit journal custody directory required')
        if path == namespace or namespace in path.parents:
            raise CleanupHold('Journal cannot be inside disposable resources')
        binding = {'schema_version': 1, 'run_id': run_id, 'source_sha': source_sha,
                   'container_name': container_name, 'container_id': container_id,
                   'namespace': str(namespace), 'namespace_identity': ns_id,
                   'staging': str(staging), 'staging_identity': stage_id}
        # Exclusive creation refuses accidental reuse or resetting lost state.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE binding (data TEXT NOT NULL)')
            db.execute('CREATE TABLE events (sequence INTEGER PRIMARY KEY, '
                       'step TEXT NOT NULL, status TEXT NOT NULL)')
            db.execute('INSERT INTO binding VALUES (?)', (json.dumps(binding, sort_keys=True),))
            db.execute('INSERT INTO events VALUES (1,?,?)', (STEPS[0], 'PENDING'))
            db.commit()
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return cls(path)

    def _validate_binding(self):
        b = self.binding
        fields = {'schema_version', 'run_id', 'source_sha', 'container_name', 'container_id',
                  'namespace', 'namespace_identity', 'staging', 'staging_identity'}
        if set(b) != fields or b['schema_version'] != 1:
            raise CleanupHold('Unsupported cleanup binding')
        ns, staging = Path(b['namespace']), Path(b['staging'])
        if (not ns.is_absolute() or not staging.is_absolute() or staging.parent != ns
                or not ns.name.startswith('nexus-supervisor-')
                or not staging.name.startswith('nexus-isolated-')
                or ns in self.path.parents
                or not re.fullmatch('[0-9a-f]{40}', b['source_sha'])
                or not re.fullmatch('[0-9a-f]{64}', b['container_id'])
                or not re.fullmatch('nexus-acceptance-[0-9a-f]{32}', b['container_name'])
                or any(type(b[k]) is not list or len(b[k]) != 2 or
                       any(type(v) is not int or v < 0 for v in b[k])
                       for k in ('namespace_identity', 'staging_identity'))):
            raise CleanupHold('Cleanup binding mismatch')

    def snapshot(self):
        with closing(self.connect()) as db:
            rows = db.execute('SELECT sequence,step,status FROM events ORDER BY sequence').fetchall()
        step_index = 0
        last_verified = None
        previous_status = None
        for expected, (sequence, step, status) in enumerate(rows, 1):
            if (sequence != expected or step_index >= len(STEPS) or step != STEPS[step_index]
                    or status not in {'PENDING', 'INTENT', 'UNCERTAIN', 'VERIFIED'}):
                raise CleanupHold('Invalid cleanup event chain')
            if previous_status is None and status != 'PENDING':
                raise CleanupHold('Initial cleanup checkpoint missing')
            if status == 'VERIFIED':
                step_index += 1
                last_verified = step
            previous_status = status
        if not rows:
            raise CleanupHold('Cleanup history missing; do not recreate')
        return {'run_id': self.binding['run_id'], 'source_sha': self.binding['source_sha'],
                'sequence': len(rows), 'last_verified': last_verified,
                'next_step': STEPS[step_index] if step_index < len(STEPS) else 'COMPLETE',
                'status': 'COMPLETE' if step_index == len(STEPS) else rows[-1][2],
                'binding': dict(self.binding)}

    def record(self, step, status):
        current = self.snapshot()
        if current['next_step'] != step or status not in {'INTENT', 'UNCERTAIN', 'VERIFIED'}:
            raise CleanupHold('Unsupported cleanup transition')
        with closing(self.connect()) as db:
            db.execute('INSERT INTO events VALUES (?,?,?)',
                       (current['sequence'] + 1, step, status))
            db.commit()

    def _directory_present(self, field):
        p = Path(self.binding[field])
        # A missing parent is absence; a replaced/symlink parent is uncertainty.
        ns = Path(self.binding['namespace'])
        if ns.exists() or ns.is_symlink():
            if identity(ns) != self.binding['namespace_identity']:
                raise CleanupHold('Namespace identity changed')
        elif field == 'staging':
            return False
        if not p.exists() and not p.is_symlink():
            return False
        if identity(p) != self.binding[field + '_identity']:
            raise CleanupHold('Disposable directory identity changed')
        return True

    def advance(self, observe_container, remove_container, after_action=None):
        """Perform at most one step; inspect first, including after uncertain results.

        observe_container returns None only for confirmed absence, or the exact
        immutable container ID. Exceptions mean unknown and prohibit removal.
        after_action is an interruption-test hook, not a persistence callback.
        """
        current = self.snapshot()
        step = current['next_step']
        if step == 'COMPLETE':
            return current
        self.record(step, 'INTENT')
        try:
            if step == 'REMOVE_CONTAINER':
                observed = observe_container(dict(self.binding))
                if observed is not None:
                    if observed != self.binding['container_id']:
                        raise CleanupHold('Container identity changed')
                    remove_container(dict(self.binding))
                    if after_action: after_action()
                    if observe_container(dict(self.binding)) is not None:
                        raise CleanupHold('Container absence not verified')
            elif step == 'REMOVE_STAGING':
                # Never remove storage while the bound container may still exist.
                if observe_container(dict(self.binding)) is not None:
                    raise CleanupHold('Container absence must be reconfirmed')
                if self._directory_present('staging'):
                    shutil.rmtree(self.binding['staging'])
                    if after_action: after_action()
                if self._directory_present('staging'):
                    raise CleanupHold('Staging absence not verified')
            else:
                if observe_container(dict(self.binding)) is not None:
                    raise CleanupHold('Container absence must be reconfirmed')
                if self._directory_present('namespace'):
                    # Empty-only removal preserves unexpected remaining data.
                    Path(self.binding['namespace']).rmdir()
                    if after_action: after_action()
                if self._directory_present('namespace'):
                    raise CleanupHold('Namespace absence not verified')
        except Exception:
            self.record(step, 'UNCERTAIN')
            raise CleanupHold('Cleanup outcome uncertain; inspect checkpoint before resuming') from None
        self.record(step, 'VERIFIED')
        return self.snapshot()


def docker(*args):
    return subprocess.run(['docker', *args], check=True, capture_output=True,
                          text=True, timeout=15).stdout.strip()


def observe_container(binding):
    ident = binding['container_id']
    ids = docker('ps', '--all', '--quiet', '--no-trunc', '--filter', 'id=' + ident).splitlines()
    if not ids:
        return None
    if ids != [ident]:
        raise CleanupHold('Docker inventory identity mismatch')
    info = json.loads(docker('inspect', ident))[0]
    if (info['Id'] != ident or info['Name'] != '/' + binding['container_name'] or
            not any(m.get('Source') == str(Path(binding['staging']) / 'source')
                    and m.get('Destination') == '/sandbox' for m in info['Mounts'])):
        raise CleanupHold('Docker ownership/mount evidence changed')
    return ident


def remove_container(binding):
    docker('rm', '--force', binding['container_id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--advance', action='store_true',
                        help='Perform at most one verified cleanup step, otherwise inspect only')
    args = parser.parse_args()
    journal = CleanupJournal(args.journal)
    result = journal.advance(observe_container, remove_container) if args.advance else journal.snapshot()
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
