"""Opt-in offline paired restore; retains an existing trusted inventory.

Single stopped worker only. The caller authenticates the latest witness.
No remote calls; no automatic replacement or bootstrap of lost inventory.
"""
import base64
import binascii
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
import zlib
from .checkpoint_gate import verify_checkpoint_copies
from .recovery_guard import read_inventory, restore_backup, require, RecoveryHold


def private_staging_root(staging_root):
    root=Path(staging_root).absolute()
    info=root.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and
            stat.S_IMODE(info.st_mode)==0o700,'Use an existing private owner-only staging directory')
    return root


def cleanup_restore_staging(journal,inventory,copies,latest_witness,staging_root):
    """Stopped sole worker only; preflight all candidates before deletion.

    The root must be dedicated to this installation. Unknown/mismatched content
    is retained and causes a hold. Journal/quarantine files are never removed.
    """
    packet=verify_checkpoint_copies(copies,latest_witness)
    retained=read_inventory(journal,inventory)
    require(packet['inventory']==retained,'Packet differs from retained trusted inventory')
    digest=packet.get('journal_sha256');size=packet.get('journal_size_bytes')
    require(type(size) is int and 0<size<=1_000_000,'Invalid checkpoint size')
    require(any(b['sha256']==digest for b in retained['backups']),
            'Cleanup checksum is not in the retained backup catalog')
    root=private_staging_root(staging_root);candidates=[]
    resolved_root=root.resolve()
    require(not Path(journal).resolve().is_relative_to(resolved_root) and
            not Path(inventory).resolve().is_relative_to(resolved_root),
            'Staging root contains journal or inventory; cleanup refused')
    for folder in sorted(root.iterdir()):
        require(re.fullmatch(r'nexus-checkpoint-[a-z0-9_]{8}',folder.name) is not None,
                'Unknown staging directory entry; preserve for review')
        info=folder.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and
                stat.S_IMODE(info.st_mode)==0o700,'Unexpected staging directory type or permissions')
        children=list(folder.iterdir())
        require(len(children)<=1,'Unexpected staging contents; preserve for review')
        if children:
            p=children[0];info=p.lstat()
            require(p.name=='checkpoint.sqlite' and stat.S_ISREG(info.st_mode) and
                    info.st_nlink==1 and info.st_uid==os.getuid() and info.st_size==size,
                    'Unexpected staging file; preserve for review')
            require(hashlib.sha256(p.read_bytes()).hexdigest()==digest,
                    'Staging bytes differ from verified checkpoint; preserve for review')
        candidates.append((folder,children))
    removed=[]
    for folder,children in candidates:
        for p in children:p.unlink()
        folder.rmdir();removed.append(folder.name)
    # An earlier removal may have succeeded before fsync failed or the process
    # stopped. Retry the sync even when no candidate remains to remove.
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return removed


def restore_paired_checkpoint(journal,inventory,copies,latest_witness,*,staging_root=None):
    packet=verify_checkpoint_copies(copies,latest_witness)
    retained=read_inventory(journal,inventory)
    require(packet['inventory']==retained,'Packet differs from retained trusted inventory')
    j=Path(journal).absolute()
    require(not j.exists() and not j.is_symlink(),'Existing journal must be preserved; refusing overwrite')
    require(packet.get('journal_encoding')=='zlib+base64','Unsupported checkpoint encoding')
    size=packet.get('journal_size_bytes');encoded=packet.get('journal_data')
    require(type(size) is int and 0<size<=1_000_000,'Checkpoint size outside bounded restore scope')
    require(type(encoded) is str and len(encoded)<=1_400_000,'Checkpoint encoded data invalid or too large')
    try:
        compressed=base64.b64decode(encoded,validate=True)
        decoder=zlib.decompressobj();raw=decoder.decompress(compressed,1_000_001)
    except (ValueError,binascii.Error,zlib.error) as exc:
        raise RecoveryHold('Checkpoint decoding failed') from exc
    require(len(raw)==size and decoder.eof and not decoder.unused_data and
            not decoder.unconsumed_tail,'Checkpoint stream incomplete, oversized or trailing data')
    require(hashlib.sha256(raw).hexdigest()==packet.get('journal_sha256'),
            'Checkpoint journal bytes differ from declared checksum')
    root=None
    if staging_root is not None:
        root=private_staging_root(staging_root)
        cleanup_restore_staging(journal,inventory,copies,latest_witness,root)
    # The existing restore checks catalog membership, SQLite integrity,
    # installation and retained identity witnesses before creating the journal.
    with tempfile.TemporaryDirectory(prefix='nexus-checkpoint-',dir=root) as folder:
        backup=Path(folder)/'checkpoint.sqlite';backup.write_bytes(raw)
        return restore_backup(journal,inventory,backup)
