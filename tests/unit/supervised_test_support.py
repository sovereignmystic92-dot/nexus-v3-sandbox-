"""Synthetic test fixtures, never provider authorization or live evidence."""
import copy
import hashlib
import json
import sqlite3


def make_gate(source_page, source_sha256, output_name, analysis):
    text = ('NEXUS_SOURCE_PAGE=' + source_page + '\nNEXUS_SOURCE_SHA256='
            + source_sha256 + '\n' + analysis)
    binding = dict(run_id='synthetic-test', source_id=source_page,
        source_sha256=source_sha256, output_id=output_name,
        output_sha256=hashlib.sha256(text.encode()).hexdigest())
    domain = dict(name='Technology', relevance='Synthetic relevant scope.',
        contribution='Bounded test finding.', knowledge_impact='No promotion.',
        full_potential='Test the boundary.', questions='What remains unknown?',
        required_action=dict(status='NOT_REQUIRED', reason='No extra action.',
                             evidence_refs=[]),
        verification=dict(status='VERIFIED', evidence_refs=['synthetic:assessment']))
    return dict(binding=binding, required_domains=('Technology',),
        report=dict(schema='nexus.analysis-evidence.v1', binding=copy.deepcopy(binding),
                    output_text=text, domains=[domain]))


def seed_legacy(path, *, prepared, source_page, source_sha256, output_name,
                analysis, expected_owner, state='INTENT', module_id=None):
    text = ('NEXUS_SOURCE_PAGE=' + source_page + '\nNEXUS_SOURCE_SHA256='
            + source_sha256 + '\n' + analysis)
    binding = json.dumps(dict(prepared=prepared, source_page=source_page,
        source_sha256=source_sha256, output_name=output_name,
        output_sha256=hashlib.sha256(text.encode()).hexdigest(),
        expected_owner=expected_owner), sort_keys=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE execution (singleton INTEGER PRIMARY KEY '
                   'CHECK(singleton=1),binding TEXT NOT NULL,state TEXT NOT NULL,module_id TEXT)')
        db.execute('INSERT INTO execution VALUES (1,?,?,?)', (binding,state,module_id))
