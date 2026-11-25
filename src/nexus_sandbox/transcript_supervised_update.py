"""Append-only supervised update; host-authenticated ports, no provider transport.

Invoked through execute_supervised. Single cooperating writer only: local flock
and fresh baseline checks are not server CAS, remote fencing or authorization.
"""
import fcntl
import hashlib
import json
import re
import sqlite3
from uuid import UUID

from .analysis_evidence import validate_analysis_evidence
from .transcript_ingestion_gate import plan_archive_resume


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _snapshot(value):
    fields = {'id', 'name', 'owner', 'version', 'content', 'dependencies', 'parent'}
    if (type(value) is not dict or set(value) != fields
            or any(type(value[k]) is not str or not value[k].strip()
                   for k in ('id', 'name', 'owner', 'content'))
            or type(value['version']) is not int or value['version'] < 1
            or type(value['dependencies']) is not list
            or any(type(x) is not str or not x.strip() for x in value['dependencies'])
            or len(set(value['dependencies'])) != len(value['dependencies'])
            or (value['parent'] is not None and
                (type(value['parent']) is not str or not value['parent'].strip()))):
        raise ValueError('Exact native Cortex snapshot required')


def _execute_update(*, journal_path, prepared, source_page, source_sha256,
                    output_name, appendix, expected_owner, request,
                    analysis_gate, update_plan, allow_update):
    """Persist intent before one update; uncertain outcomes reconcile read-only.

    update_plan has before (full pinned snapshot), stable enrichment_id and exclusive_writer_evidence
    (a reference to host-verified exclusive mutation custody, not a grant).
    The host must enforce that custody and actual provider access. It must not
    interpret the reference, owner field or allow_update as proof of authority.
    """
    if (type(allow_update) is not bool or type(update_plan) is not dict
            or set(update_plan) != {'before', 'enrichment_id', 'exclusive_writer_evidence'}
            or type(update_plan['enrichment_id']) is not str
            or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}',
                            update_plan['enrichment_id']) is None
            or type(update_plan['exclusive_writer_evidence']) is not str
            or not update_plan['exclusive_writer_evidence'].strip()
            or len(update_plan['exclusive_writer_evidence']) > 512
            or type(appendix) is not str or not appendix.startswith('\n\n')
            or not appendix.strip() or str(UUID(source_page)) != source_page):
        raise ValueError('Bound append-only update plan required')
    # Copy before invoking any host code. Never rebind an existing journal.
    prepared = json.loads(json.dumps(prepared, allow_nan=False))
    plan = json.loads(json.dumps(update_plan, allow_nan=False))
    before = plan['before']
    _snapshot(before)
    if before['name'] != output_name or before['owner'] != expected_owner:
        raise ValueError('Update destination/owner mismatch')
    # Source binding belongs in the appended evidence, leaving all base bytes.
    enrichment_marker = 'NEXUS_ENRICHMENT_ID=' + plan['enrichment_id']
    if enrichment_marker in before['content'] or appendix in before['content']:
        raise ValueError('Enrichment already present; reconcile existing operation')
    markers = ('NEXUS_SOURCE_PAGE=' + source_page,
               'NEXUS_SOURCE_SHA256=' + source_sha256, enrichment_marker)
    lines = appendix.splitlines()
    source_lines = [line for line in lines if line.startswith(
        ('NEXUS_SOURCE_PAGE=', 'NEXUS_SOURCE_SHA256=', 'NEXUS_ENRICHMENT_ID='))]
    if len(source_lines) != 3 or any(lines.count(marker) != 1 for marker in markers):
        raise ValueError('Exact source markers required in appendix')
    desired = before['content'] + appendix
    if (type(analysis_gate) is not dict or set(analysis_gate) !=
            {'binding', 'required_domains', 'report'}):
        raise ValueError('Complete analysis gate required')
    domains = analysis_gate['required_domains']
    gate = json.loads(json.dumps({k: analysis_gate[k] for k in ('binding', 'report')},
                                allow_nan=False))
    fingerprint = validate_analysis_evidence(gate['binding'], domains, gate['report'])
    if (gate['binding']['source_id'] != source_page
            or gate['binding']['source_sha256'] != source_sha256
            or gate['binding']['output_id'] != output_name
            or gate['report']['output_text'] != desired):
        raise ValueError('Analysis gate does not bind appended output')
    plan_archive_resume(prepared, source_page, None,
                        expected_source_sha256=source_sha256)
    binding = json.dumps(dict(operation='append-existing-v1', prepared=prepared,
        source_page=source_page, source_sha256=source_sha256, update_plan=plan,
        output_sha256=_sha(desired), analysis_evidence_sha256=fingerprint), sort_keys=True)
    after = dict(before, content=desired, version=before['version'] + 1)
    # Use the existing journal table and binding-conflict rule. Neither a legacy
    # create journal nor another update's intent can be silently replaced.
    with open(str(journal_path) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = sqlite3.connect(journal_path)
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS execution '
                       '(singleton INTEGER PRIMARY KEY CHECK(singleton=1), '
                       'binding TEXT NOT NULL,state TEXT NOT NULL,module_id TEXT)')
            prior = db.execute('SELECT binding,state,module_id FROM execution').fetchone()
            if prior and (prior[0] != binding or prior[1] not in
                    ('PREPARED', 'INTENT', 'VERIFIED') or
                    (prior[1] == 'VERIFIED' and prior[2] != before['id']) or
                    (prior[1] != 'VERIFIED' and prior[2] is not None)):
                raise ValueError('Journal binding/state conflict; reconcile custody')
            if not prior:
                db.execute('INSERT INTO execution VALUES (1,?,?,NULL)', (binding, 'PREPARED'))
                db.commit()
            state = prior[1] if prior else 'PREPARED'
            writes = 0

            def source_read():
                observation = request('archive_read', dict(page_id=source_page,
                                                          source_sha256=source_sha256))
                if plan_archive_resume(prepared, source_page, observation,
                        expected_source_sha256=source_sha256)['state'] != 'ARCHIVE_VERIFIED':
                    raise ValueError('Complete exact source readback required')

            def output_read():
                value = request('cortex_get', dict(name=output_name))
                _snapshot(value)
                return value

            def receipt(status, next_action):
                return dict(handoff=dict(status=status, next_action=next_action,
                    source_sha256=source_sha256, notion_id=source_page, cortex_id=output_name),
                    update_requests=writes, create_requests=0, module_id=before['id'],
                    module_version=after['version'] if status == 'READBACK_MATCHED' else None,
                    before_sha256=_sha(before['content']), output_sha256=_sha(desired),
                    analysis_evidence_sha256=fingerprint,
                    analysis_evidence_status=('STRUCTURAL_READBACK_MATCHED'
                        if status == 'READBACK_MATCHED' else 'PRECHECK_ONLY'),
                    execution_mode='GATED_APPEND_EXISTING', remote_fencing=False,
                    audit_promotion=False, unattended_readiness=False)

            source_read()
            target = output_read()
            if target != after:
                if target != before or state == 'VERIFIED':
                    raise ValueError('Target identity/version/content/relationships changed')
                if state == 'INTENT':
                    return receipt('BLOCKED', 'RECONCILE_UNCERTAIN_UPDATE_NO_RETRY')
                if not allow_update:
                    return receipt('BLOCKED', 'EXACT_UPDATE_AUTHORIZATION_REQUIRED')
                source_read()
                if output_read() != before:
                    raise ValueError('Target changed immediately before update')
                db.execute("UPDATE execution SET state='INTENT'")
                db.commit()
                state = 'INTENT'
                writes = 1
                try:
                    request('cortex_update', dict(name=output_name, module_id=before['id'],
                        expected_owner=expected_owner, expected_version=before['version'],
                        before_sha256=_sha(before['content']), content=desired,
                        exclusive_writer_evidence=plan['exclusive_writer_evidence']))
                except Exception:
                    return receipt('BLOCKED', 'RECONCILE_UNCERTAIN_UPDATE_NO_RETRY')
                target = output_read()
            elif state == 'PREPARED':
                # A matching object in a replacement/lost journal is not proof
                # this operation owns the effect. Require retained prior intent.
                return receipt('BLOCKED', 'RECONCILE_EXISTING_EFFECT_WITH_RETAINED_INTENT')
            if target != after:
                raise ValueError('Updated output readback mismatch')
            fresh = dict(gate['report'], output_text=target['content'])
            if validate_analysis_evidence(gate['binding'], domains, fresh) != fingerprint:
                raise ValueError('Saved analysis evidence mismatch')
            source_read()
            db.execute("UPDATE execution SET state='VERIFIED',module_id=?", (before['id'],))
            db.commit()
            return receipt('READBACK_MATCHED', 'RECORD_DURABLE_EXECUTION_RECEIPT')
        finally:
            db.close()
