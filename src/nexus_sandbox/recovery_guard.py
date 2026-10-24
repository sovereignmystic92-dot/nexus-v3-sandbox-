"""Opt-in local wrapper requiring an operator-trusted recovery inventory.

Not authentication, remote fencing, device-loss protection or an unbypassable
security boundary. Single cooperating worker only. Original adapter unchanged.
"""
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
import os
import re
import stat
from pathlib import Path
import sqlite3
from urllib.parse import quote
import uuid

from .cortex_adapter import CortexAdapter, JournalIntegrityError

def read_json(path):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('Duplicate inventory key')
            result[k]=v
        return result
    with Path(path).open('rb') as stream:raw=stream.read(1_000_001)
    if len(raw)>1_000_000:raise ValueError('Inventory too large')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite inventory number')))


class RecoveryHold(JournalIntegrityError):
    pass


def require(condition,message):
    if not condition:raise RecoveryHold(message)


def paths(journal,inventory):
    j,i=Path(journal).absolute(),Path(inventory).absolute()
    require(not j.is_symlink() and not i.is_symlink(),'Symlink journal/inventory refused')
    require(j.parent.resolve()!=i.parent.resolve(),'Use a separate inventory directory; same-disk loss remains unprotected')
    return j,i


def atomic_inventory(path,data):
    temp=path.with_name(path.name+'.pending-'+uuid.uuid4().hex)
    try:
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:
            json.dump(data,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
        # File fsync alone does not flush the directory entry changed by replace.
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


def read_inventory(journal,inventory):
    j,i=paths(journal,inventory)
    require(i.is_file(),'Trusted inventory missing; explicit initialization/recovery required')
    try:data=read_json(i)
    except (OSError,ValueError) as exc:raise RecoveryHold('Trusted inventory unreadable; hold') from exc
    fields={'schema_version','state','installation_id','journal_path','last_sequence','anchors','backups','pending_request'}
    require(type(data) is dict and set(data)==fields,'Malformed recovery inventory')
    require(type(data['schema_version']) is int and data['schema_version']==2 and data['state'] in ('ready','operation_pending'),'Inventory is not ready or uses an unsupported schema')
    pending=data['pending_request']
    require((data['state']=='ready' and pending is None) or
            (data['state']=='operation_pending' and type(pending) is str and len(pending)==64),
            'Invalid pending-operation binding')
    require(type(data['installation_id']) is str and len(data['installation_id'])==32,'Invalid installation identity')
    require(data['journal_path']==str(j),'Inventory belongs to another journal path')
    require(type(data['last_sequence']) is int and data['last_sequence']>=0,'Invalid sequence witness')
    require(type(data['anchors']) is dict and all(type(k) is str and type(v) is str and v for k,v in data['anchors'].items()),'Invalid identity witnesses')
    require(type(data['backups']) is list and len(data['backups'])<=1000,'Invalid backup catalog')
    for b in data['backups']:
        require(type(b) is dict and set(b)=={'sha256','sequence'} and type(b['sha256']) is str and len(b['sha256'])==64
                and type(b['sequence']) is int and b['sequence']>=0,'Invalid backup entry')
    return data


def open_existing(path):
    require(path.is_file() and not path.is_symlink(),'Expected journal missing; automatic initialization forbidden')
    return sqlite3.connect('file:'+quote(str(path),safe='/')+'?mode=rw',uri=True)


def witness(db):
    row=db.execute('SELECT installation_id FROM recovery_installation WHERE singleton=1').fetchone()
    require(row is not None,'Journal installation identity missing')
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'cortex_events' not in tables:
        require(not ({'cortex_receipts','cortex_identity_anchors'} & tables),'Incomplete adapter schema')
        return row[0],0,{}
    sequence=db.execute('SELECT COALESCE(MAX(sequence),0) FROM cortex_events').fetchone()[0]
    anchors=dict(db.execute('SELECT key,module_id FROM cortex_identity_anchors'))
    return row[0],sequence,anchors


def check(journal,inventory):
    data=read_inventory(journal,inventory)
    with closing(open_existing(Path(journal).absolute())) as db:
        require(db.execute('PRAGMA quick_check').fetchone()[0]=='ok','Journal integrity check failed')
        ident,seq,anchors=witness(db)
    require(ident==data['installation_id'],'Journal installation identity mismatch')
    require(seq>=data['last_sequence'],'Journal predates the retained sequence witness')
    require(all(anchors.get(k)==v for k,v in data['anchors'].items()),'Retained identity witness missing or changed')
    return data


def cleanup_staged_inventory(journal,inventory):
    """Explicit offline maintenance after the sole worker has stopped.

    Validate committed state first. Never adopt staged inventory or repair an
    incomplete initialization. This function requires the same single-worker
    exclusion contract as backup/restore; it is not a concurrency boundary.
    """
    check(journal,inventory)
    _,i=paths(journal,inventory)
    candidates=[]
    for p in sorted(i.parent.glob(i.name+'.pending-*')):
        require(re.fullmatch(re.escape(i.name)+r'\.pending-[0-9a-f]{32}',p.name),
                'Unexpected staging filename; preserve for operator review')
        info=p.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,
                'Non-regular or linked staging file; preserve for operator review')
        candidates.append(p)
    # Preflight every candidate before deleting any. Committed inventory and
    # journal remain untouched, even when pending work still needs reconciliation.
    for p in candidates:p.unlink()
    # A previous call may have removed every entry and then failed to sync.
    # An empty retry must retry the directory sync before reporting completion.
    fd=os.open(i.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return [p.name for p in candidates]


def initialize(journal,inventory):
    """Explicit initial creation only; never called by startup or ensure."""
    j,i=paths(journal,inventory)
    require(not j.exists() and not i.exists(),'Initialization refuses existing journal or inventory')
    require(j.parent.is_dir() and i.parent.is_dir(),'Create designated parent directories explicitly')
    data={'schema_version':2,'state':'initializing','installation_id':uuid.uuid4().hex,
          'journal_path':str(j),'last_sequence':0,'anchors':{},'backups':[],'pending_request':None}
    # Reserve inventory first. Any interruption leaves a hold rather than an
    # implicitly new installation. This is not a two-file atomic transaction.
    fd=os.open(i,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
    fd=os.open(j,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    with closing(open_existing(j)) as db,db:
        db.execute('CREATE TABLE recovery_installation(singleton INTEGER PRIMARY KEY CHECK(singleton=1),installation_id TEXT NOT NULL)')
        db.execute('INSERT INTO recovery_installation VALUES(1,?)',(data['installation_id'],))
    data['state']='ready';atomic_inventory(i,data)
    return check(j,i)


class GuardedCortexAdapter(CortexAdapter):
    def __init__(self,journal,inventory,allowed_names,transport):
        self.inventory=Path(inventory).absolute()
        self.journal=Path(journal).absolute()
        check(self.journal,self.inventory)
        super().__init__(self.journal,allowed_names,transport)

    def _db(self):
        # Recheck for later removal/replacement before each original DB access.
        check(self.journal,self.inventory)
        return open_existing(self.journal)

    def ensure(self,request):
        data=check(self.journal,self.inventory)
        self._validate(request)
        binding=hashlib.sha256(json.dumps(asdict(request),sort_keys=True).encode()).hexdigest()
        require(data['state']=='ready' or data['pending_request']==binding,
                'Another uncertain request is pending; reconcile the exact original request first')
        if data['state']=='ready':
            data['state']='operation_pending';data['pending_request']=binding
        # Recommit even a visible matching pending marker: an earlier attempt
        # may have failed after replacement but before directory sync completed.
        # This must finish before entering the original adapter or transport.
        atomic_inventory(self.inventory,data)
        result=super().ensure(request)
        data=check(self.journal,self.inventory)
        with closing(open_existing(self.journal)) as db:
            _,seq,anchors=witness(db)
        data['last_sequence']=seq;data['anchors']=anchors
        data['state']='ready';data['pending_request']=None
        atomic_inventory(self.inventory,data)
        return result


def create_backup(journal,inventory,destination):
    """Single-worker quiescent backup. Register only a completed, checked file."""
    data=check(journal,inventory);j=Path(journal).absolute();dest=Path(destination).absolute()
    require(data['state']=='ready','Uncertain operation pending; reconcile before registering a backup')
    require(not dest.exists() and not dest.is_symlink(),'Backup destination already exists')
    fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    with closing(open_existing(j)) as src,closing(sqlite3.connect(dest)) as target:
        src.backup(target)
        require(target.execute('PRAGMA integrity_check').fetchone()[0]=='ok','Backup failed integrity check')
        ident,seq,anchors=witness(target)
    require(ident==data['installation_id'] and seq>=data['last_sequence'] and
            all(anchors.get(k)==v for k,v in data['anchors'].items()),'Backup fails retained identity/freshness witness')
    # Publish the catalog entry only after flushing the completed backup and
    # the directory entry through which recovery will locate it.
    fd=os.open(dest,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    fd=os.open(dest.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    entry={'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'sequence':seq}
    data['backups'].append(entry)
    atomic_inventory(Path(inventory).absolute(),data)
    return entry


def restore_backup(journal,inventory,backup):
    """Restore a cataloged backup to an absent path; never overwrite evidence."""
    data=read_inventory(journal,inventory);j=Path(journal).absolute();b=Path(backup).absolute()
    require(data['state']=='ready','Uncertain operation pending; backup restore requires manual trusted recovery')
    require(not j.exists() and not j.is_symlink(),'Preserve/quarantine the existing journal explicitly before restoration')
    require(b.is_file() and not b.is_symlink(),'Backup missing or symlinked')
    raw=b.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    entries=[x for x in data['backups'] if x['sha256']==sha]
    require(entries,'Backup not in the operator-trusted catalog or bytes changed')
    require(entries[-1]['sequence']>=data['last_sequence'],'Backup predates known journal activity')
    with closing(sqlite3.connect('file:'+quote(str(b),safe='/')+'?mode=ro',uri=True)) as db:
        require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','Backup storage corruption')
        ident,seq,anchors=witness(db)
    require(ident==data['installation_id'] and seq>=data['last_sequence'] and
            all(anchors.get(k)==v for k,v in data['anchors'].items()),'Backup installation or retained identities mismatch')
    fd=os.open(j,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(j.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return check(j,inventory)
