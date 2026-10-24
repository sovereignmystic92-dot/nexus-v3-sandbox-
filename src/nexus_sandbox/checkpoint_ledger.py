"""Append-only checkpoint manifest validation against an independently read base.

Does not authenticate the supplied base or perform provider readback. CI/host
must supply the actual protected branch base; local files are not authority.
"""
from datetime import datetime
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def manifest_hash(record):
    return hashlib.sha256(canonical(record)).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(ledger):
    require(type(ledger) is dict and set(ledger) == {'schema_version','records','latest'}, 'Invalid ledger shape')
    require(type(ledger['schema_version']) is int and ledger['schema_version'] == 1, 'Invalid ledger version')
    records = ledger['records']
    require(type(records) is list and len(records) <= 10000, 'Invalid manifest history')
    previous = None
    installation = None
    fields = {'workflow_version','installation_id','checkpoint_sequence','created_at_utc',
              'source_commit','packet_sha256','previous_manifest_sha256','copies'}
    for sequence, record in enumerate(records, 1):
        require(type(record) is dict and set(record) == fields, 'Invalid manifest fields')
        require(record['workflow_version'] == 'sandbox-recovery-v2', 'Unsupported recovery workflow')
        require(type(record['checkpoint_sequence']) is int and record['checkpoint_sequence'] == sequence, 'Checkpoint sequence gap/rollback')
        ident = record['installation_id']
        require(type(ident) is str and re.fullmatch('[0-9a-f]{32}', ident) is not None, 'Invalid installation identity')
        installation = installation or ident
        require(ident == installation, 'Installation changed inside ledger')
        require(record['previous_manifest_sha256'] == previous, 'Broken manifest hash chain')
        for field, length in (('source_commit',40),('packet_sha256',64)):
            require(type(record[field]) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}', record[field]) is not None, 'Invalid '+field)
        date = record['created_at_utc']
        require(type(date) is str and date.endswith('Z'), 'UTC checkpoint date required')
        try:
            datetime.fromisoformat(date[:-1]+'+00:00')
        except ValueError:
            raise ValueError('Invalid checkpoint date') from None
        copies = record['copies']
        require(type(copies) is dict and set(copies) == {'notion','cortex'}, 'Both copy bindings required')
        for provider, copy in copies.items():
            require(type(copy) is dict and set(copy) == {'record_id','packet_sha256'}, 'Invalid copy binding')
            require(type(copy['record_id']) is str and 0 < len(copy['record_id']) <= 256, 'Provider record identity required')
            require(copy['packet_sha256'] == record['packet_sha256'], 'Provider packet hashes differ')
        previous = manifest_hash(record)
    expected = None if not records else {'installation_id':installation,
        'checkpoint_sequence':len(records),'manifest_sha256':previous}
    require(ledger['latest'] == expected, 'Latest reference differs from complete history')
    return expected


def validate_transition(base, candidate):
    validate(base)
    latest = validate(candidate)
    require(len(candidate['records']) >= len(base['records']), 'Accepted history truncated')
    require(canonical(candidate['records'][:len(base['records'])]) == canonical(base['records']),
            'Accepted manifest history rewritten')
    return latest
