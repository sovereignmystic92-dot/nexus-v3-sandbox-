"""Opt-in Chat host composition. No credentials, network, scheduler or retries.

request(operation, payload) must make a fresh authenticated connector call.
The host owns account selection, effective grants and durable journal storage.
Only a create of the pinned destination is exposed; source writes do not exist.
"""
from dataclasses import asdict
import fcntl
import hashlib
import json
import sqlite3

from .transcript_archived_handoff import run_archived_handoff
from .transcript_live_handoff import Observed


def execute_supervised(*, journal_path, prepared, source_page, source_sha256,
                       output_name, analysis, expected_owner, request,
                       allow_create=False, analysis_gate=None):
    """One locally serialized attempt; unknown create outcomes never retry.

    Ports: archive_read -> indexed observation; cortex_get -> module or None;
    cortex_create -> ignored acknowledgement. Reads must be complete/fresh.
    A None from cortex_get must mean confirmed exact-name absence in the
    host-selected account, never a search miss or an inaccessible module.
    """
    if type(allow_create) is not bool or not expected_owner:
        raise ValueError('explicit grant and expected owner required')
    # Freeze caller inputs before any callback. Bind journal to output bytes.
    prepared = json.loads(json.dumps(prepared))
    desired = ('NEXUS_SOURCE_PAGE=' + source_page + '\nNEXUS_SOURCE_SHA256='
               + source_sha256 + '\n' + analysis)
    gate_fingerprint = None
    gate_binding = None
    gate_domains = None
    gate_report = None
    if analysis_gate is not None:
        from .analysis_evidence import validate_analysis_evidence
        if (type(analysis_gate) is not dict or set(analysis_gate) !=
                {'binding', 'required_domains', 'report'}
                or type(analysis_gate['required_domains']) is not tuple):
            raise ValueError('Exact structural analysis gate required')
        gate_binding = json.loads(json.dumps(analysis_gate['binding'], allow_nan=False))
        gate_domains = analysis_gate['required_domains']
        gate_report = json.loads(json.dumps(analysis_gate['report'], allow_nan=False))
        gate_fingerprint = validate_analysis_evidence(
            gate_binding, gate_domains, gate_report)
        if (gate_binding['source_id'] != source_page
                or gate_binding['source_sha256'] != source_sha256
                or gate_binding['output_id'] != output_name
                or gate_report['output_text'] != desired):
            raise ValueError('Analysis gate does not bind this source and output')
    binding_data = dict(prepared=prepared, source_page=source_page,
        source_sha256=source_sha256, output_name=output_name,
        output_sha256=hashlib.sha256(desired.encode('utf-8')).hexdigest(),
        expected_owner=expected_owner)
    if gate_fingerprint is not None:
        binding_data['analysis_evidence_sha256'] = gate_fingerprint
    binding = json.dumps(binding_data, sort_keys=True)
    with open(str(journal_path) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = sqlite3.connect(journal_path)
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS execution '
                       '(singleton INTEGER PRIMARY KEY CHECK(singleton=1), '
                       'binding TEXT NOT NULL, state TEXT NOT NULL, module_id TEXT)')
            prior = db.execute('SELECT binding,state,module_id FROM execution').fetchone()
            if prior and prior[0] != binding:
                raise ValueError('journal binding changed')
            if not prior:
                db.execute('INSERT INTO execution VALUES (1,?,?,NULL)',
                           (binding, 'PREPARED'))
                db.commit()
            state = prior[1] if prior else 'PREPARED'
            pinned_id = prior[2] if prior else None
            writes = 0
            observed_id = None

            def archive_read(key, sha):
                return request('archive_read', dict(page_id=key, source_sha256=sha))

            def cortex_read(key):
                nonlocal observed_id
                value = request('cortex_get', dict(name=key))
                if value is None:
                    if pinned_id:
                        raise ValueError('pinned output missing; reconcile')
                    return None
                if (not isinstance(value, dict) or value.get('name') != key
                        or value.get('owner') != expected_owner
                        or not isinstance(value.get('id'), str) or not value['id']
                        or type(value.get('version')) is not int
                        or value['version'] < 1
                        or not isinstance(value.get('content'), str)
                        or (pinned_id and value['id'] != pinned_id)):
                    raise ValueError('Cortex identity/owner mismatch')
                if gate_fingerprint is not None:
                    # Pin the assessment in the journal and bind it to the actual
                    # fresh provider text; metadata authenticity stays host-owned.
                    fresh_report = json.loads(json.dumps(gate_report))
                    fresh_report['output_text'] = value['content']
                    if validate_analysis_evidence(
                            gate_binding, gate_domains, fresh_report) != gate_fingerprint:
                        raise ValueError('Saved analysis evidence mismatch')
                observed_id = value['id']
                return Observed(key, value['content'])

            def cortex_write(key, content):
                nonlocal writes, state
                if (allow_create is not True or state != 'PREPARED' or writes
                        or key != output_name or content != desired):
                    raise PermissionError('create blocked; reconcile prior intent')
                # Commit intent before crossing the provider boundary. A timeout
                # or process death leaves INTENT; absence cannot release it.
                db.execute("UPDATE execution SET state='INTENT'")
                db.commit()
                state = 'INTENT'
                writes += 1
                request('cortex_create', dict(name=key, content=content,
                    expected_owner=expected_owner))

            result = run_archived_handoff(prepared=prepared,
                notion_page_id=source_page, expected_source_sha256=source_sha256,
                read_archive=archive_read, cortex_module_name=output_name,
                analysis=analysis, cortex_read=cortex_read,
                cortex_write=cortex_write, allow_cortex_write=allow_create)
            if result.status == 'READBACK_MATCHED':
                if not observed_id:
                    raise ValueError('missing readback identity')
                db.execute("UPDATE execution SET state='VERIFIED',module_id=?",
                           (observed_id,))
                db.commit()
            # VERIFIED is accepted only after another fresh full source/output
            # read on replay. No journal status alone establishes completion.
            receipt = dict(handoff=asdict(result), create_requests=writes,
                        module_id=observed_id, output_sha256=json.loads(binding)['output_sha256'],
                        audit_promotion=False, unattended_readiness=False)
            if gate_fingerprint is not None:
                receipt['analysis_evidence_sha256'] = gate_fingerprint
                receipt['analysis_evidence_status'] = (
                    'STRUCTURAL_READBACK_MATCHED'
                    if result.status == 'READBACK_MATCHED' else 'PRECHECK_ONLY')
            return receipt
        finally:
            db.close()
