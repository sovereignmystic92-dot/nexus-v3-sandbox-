"""Explicit recovery after loss of both local journal and inventory.

The host must supply an independently authenticated CURRENT external witness.
This module does not establish that trust, select a witness or call a provider.
One stopped worker; no automatic bootstrap, overwrite or remote mutation.
"""
import base64
import binascii
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import quote
import zlib

from .checkpoint_gate import verify_checkpoint_copies
from .recovery_guard import (RecoveryHold, atomic_inventory, check, paths,
                             read_inventory, require, restore_backup, witness)


def restore_lost_local_state(journal, inventory, copies, current_witness):
    """Opt-in restore of absent local state, never a normal startup fallback.

    Validate the complete detached packet and SQLite backup before publishing
    inventory. If interrupted after inventory publication, an exact matching
    retained inventory can resume; conflicting state is preserved and held.
    """
    packet = verify_checkpoint_copies(copies, current_witness)
    j, i = paths(journal, inventory)
    require(not j.exists() and not j.is_symlink(), 'Existing journal must be preserved')
    require(j.parent.is_dir() and i.parent.is_dir(), 'Designated recovery directories must already exist')
    require(not i.is_symlink(), 'Symlink inventory refused')
    data = packet['inventory']
    require(data.get('journal_path') == str(j), 'Checkpoint belongs to a different journal path')
    require(packet.get('journal_encoding') == 'zlib+base64', 'Unsupported checkpoint encoding')
    size, encoded = packet.get('journal_size_bytes'), packet.get('journal_data')
    require(type(size) is int and 0 < size <= 1_000_000, 'Checkpoint size outside bounded recovery scope')
    require(type(encoded) is str and len(encoded) <= 1_400_000, 'Checkpoint encoded data invalid')
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(base64.b64decode(encoded, validate=True), 1_000_001)
    except (ValueError, binascii.Error, zlib.error) as exc:
        raise RecoveryHold('Checkpoint decoding failed') from exc
    require(len(raw) == size and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
            'Checkpoint stream incomplete, oversized or trailing data')
    digest = hashlib.sha256(raw).hexdigest()
    require(digest == packet.get('journal_sha256'), 'Checkpoint journal checksum mismatch')

    # Reuse strict inventory validation without publishing anything in the lost
    # installation. The temporary inventory still binds the original journal.
    with tempfile.TemporaryDirectory(prefix='nexus-loss-preflight-') as folder:
        candidate_inventory = Path(folder) / 'inventory.json'
        candidate_inventory.write_text(json.dumps(data))
        validated = read_inventory(j, candidate_inventory)
        require(validated['state'] == 'ready', 'Pending operation cannot be bootstrapped')
        require(any(b['sha256'] == digest and b['sequence'] == data['last_sequence']
                    for b in validated['backups']), 'Checkpoint backup is absent from exact latest inventory')
        backup = Path(folder) / 'checkpoint.sqlite'
        backup.write_bytes(raw)
        try:
            with closing(sqlite3.connect('file:' + quote(str(backup), safe='/') + '?mode=ro', uri=True)) as db:
                require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Backup storage corruption')
                ident, seq, anchors = witness(db)
        except sqlite3.Error as exc:
            raise RecoveryHold('Backup is not a valid recovery database') from exc
        require((ident, seq, anchors) == (validated['installation_id'], validated['last_sequence'], validated['anchors']),
                'Backup differs from exact latest installation, sequence or anchors')
        if i.exists():
            require(read_inventory(j, i) == validated, 'Retained inventory conflicts; preserve for investigation')
        else:
            # Sole stopped worker and operator-owned directories are required.
            # No missing-inventory fallback calls initialize().
            atomic_inventory(i, validated)
        result = restore_backup(j, i, backup)
    return check(j, i)
