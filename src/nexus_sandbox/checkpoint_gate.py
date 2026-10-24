"""Pure offline preflight for paired synthetic checkpoints.

The caller must independently authenticate the latest witness. This module
cannot prove that a supplied witness is current or trusted. No I/O or restore.
"""
import hashlib
import json
import re
from .recovery_guard import RecoveryHold, require


def packet_digest(packet):
    raw=json.dumps(packet,sort_keys=True,ensure_ascii=False,separators=(',',':'),
                   allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_checkpoint_copies(copies,latest_witness):
    """Require exact Cortex/Notion agreement with a caller-trusted witness.

    Returns a detached packet for subsequent validated restoration. Never pick
    the highest claimed sequence, timestamp, majority or first available copy.
    Missing evidence holds; this strict policy sacrifices availability.
    """
    try:
        require(type(latest_witness) is dict and set(latest_witness)=={
            'installation_id','last_sequence','packet_sha256'},
            'Latest trusted checkpoint witness missing or malformed')
        ident=latest_witness['installation_id'];seq=latest_witness['last_sequence']
        digest=latest_witness['packet_sha256']
        require(type(ident) is str and re.fullmatch('[0-9a-f]{32}',ident) is not None,
                'Malformed witness identity')
        require(type(seq) is int and seq>=0,'Malformed witness sequence')
        require(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest) is not None,
                'Malformed witness digest')
        require(type(copies) is dict and set(copies)=={'cortex','notion'},
                'Both designated checkpoint copies are required')
        for packet in copies.values():
            require(type(packet) is dict and packet.get('format')=='nexus-paired-recovery-v1'
                    and packet.get('synthetic') is True,'Unsupported synthetic checkpoint')
            inventory=packet.get('inventory')
            require(type(inventory) is dict,'Checkpoint inventory missing')
            require(inventory.get('state')=='ready' and inventory.get('pending_request') is None,
                    'Checkpoint contains uncertain operation state')
            require(inventory.get('installation_id')==ident,'Checkpoint installation mismatch')
            require(type(inventory.get('last_sequence')) is int and
                    inventory['last_sequence']==seq,'Checkpoint differs from latest trusted sequence')
            require(packet_digest(packet)==digest,'Checkpoint copies conflict or differ from trusted digest')
        return json.loads(json.dumps(copies['cortex'],allow_nan=False))
    except (ValueError,TypeError,OverflowError,RecursionError) as exc:
        raise RecoveryHold('Malformed checkpoint evidence; recovery held') from exc
