"""Sanitized public commitments; full manifests and routing stay private.

The caller must fetch the current protected GitHub reference independently.
An internally valid local ledger is never proof of its own currentness.
"""
from datetime import datetime
import re
from .checkpoint_ledger import canonical, manifest_hash, require
from .checkpoint_gate import verify_checkpoint_copies


def validate_public(ledger):
    require(type(ledger) is dict and set(ledger)=={'schema_version','records','latest'},'Invalid public ledger shape')
    require(type(ledger['schema_version']) is int and ledger['schema_version']==2,'Public schema version required')
    records=ledger['records']
    require(type(records) is list and len(records)<=10000,'Invalid public history')
    previous=None
    fields={'checkpoint_sequence','created_at_utc','source_commit','private_manifest_sha256','previous_entry_sha256'}
    for seq,entry in enumerate(records,1):
        require(type(entry) is dict and set(entry)==fields,'Only sanitized reference fields permitted')
        require(type(entry['checkpoint_sequence']) is int and entry['checkpoint_sequence']==seq,'Public sequence gap or rollback')
        require(entry['previous_entry_sha256']==previous,'Broken public commitment chain')
        for field,length in (('source_commit',40),('private_manifest_sha256',64)):
            require(type(entry[field]) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',entry[field]) is not None,'Invalid public commitment')
        date=entry['created_at_utc']
        require(type(date) is str and date.endswith('Z'),'UTC date required')
        try:datetime.fromisoformat(date[:-1]+'+00:00')
        except ValueError:raise ValueError('Invalid public date') from None
        previous=manifest_hash(entry)
    expected=None if not records else {'checkpoint_sequence':len(records),'entry_sha256':previous,
                                      'private_manifest_sha256':records[-1]['private_manifest_sha256']}
    require(ledger['latest']==expected,'Latest public reference differs from history')
    return expected


def validate_public_transition(base,candidate):
    # Explicit migration from the previously published UNINITIALIZED v1 only.
    if base=={'schema_version':1,'records':[],'latest':None}:
        base={'schema_version':2,'records':[],'latest':None}
    validate_public(base)
    latest=validate_public(candidate)
    require(len(candidate['records'])>=len(base['records']),'Public accepted history truncated')
    require(canonical(candidate['records'][:len(base['records'])])==canonical(base['records']),
            'Public accepted history rewritten')
    return latest


def bind_private_checkpoint(current_public_ledger,private_manifest,copies,observed_ids):
    latest=validate_public(current_public_ledger)
    require(latest is not None,'Current reference is uninitialized')
    require(type(private_manifest) is dict and manifest_hash(private_manifest)==latest['private_manifest_sha256'],
            'Private manifest does not match current public commitment')
    require(private_manifest.get('checkpoint_sequence')==latest['checkpoint_sequence'],
            'Private/public checkpoint sequence mismatch')
    require(type(observed_ids) is dict and set(observed_ids)=={'notion','cortex'},'Both observed provider identities required')
    for provider in ('notion','cortex'):
        binding=private_manifest['copies'][provider]
        require(binding['record_id']==observed_ids[provider],'Provider record identity mismatch')
        require(binding['packet_sha256']==private_manifest['packet_sha256'],'Private copy hash mismatch')
    require(type(copies) is dict and set(copies)=={'notion','cortex'},'Both provider copies required')
    packet=copies['notion']
    witness={'installation_id':private_manifest['installation_id'],
             'last_sequence':packet['inventory']['last_sequence'],
             'packet_sha256':private_manifest['packet_sha256']}
    return verify_checkpoint_copies(copies,witness),witness
