"""Source/output-bound structural analysis checks; no providers or authority.

Trusted hosts determine materially relevant domains and supply candidate evidence
before persistence and a fresh independently retrieved report after readback.
Nonempty prose and evidence references do not establish semantic or factual truth.
"""
import hashlib
import json
import re

_BINDING_FIELDS = {'run_id', 'source_id', 'source_sha256',
                   'output_id', 'output_sha256'}
_DOMAIN_FIELDS = {'name', 'relevance', 'contribution', 'knowledge_impact',
                  'full_potential', 'required_action', 'questions', 'verification'}
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')


def _require(condition):
    if not condition:
        raise ValueError('Analysis evidence incomplete or misbound')


def _text(value, limit=20000):
    return type(value) is str and 0 < len(value) <= limit and bool(value.strip())


def validate_analysis_plan(binding, required_domains):
    """Validate only structure; the host authenticates scope and identities."""
    _require(type(binding) is dict and set(binding) == _BINDING_FIELDS)
    _require(all(_text(v, 512) for v in binding.values()))
    _require(all(_DIGEST.fullmatch(binding[k]) is not None
                 for k in ('source_sha256', 'output_sha256')))
    _require(type(required_domains) is tuple and 0 < len(required_domains) <= 64)
    _require(all(_text(name, 160) for name in required_domains))
    _require(len(set(required_domains)) == len(required_domains))


def _refs(value):
    _require(type(value) is list and 0 < len(value) <= 100)
    _require(all(_text(ref, 512) for ref in value))
    _require(len(set(value)) == len(value))


def validate_analysis_evidence(binding, required_domains, report):
    """Return a digest of the exact structural evidence, not a quality verdict.

    Required actions must be VERIFIED or explicitly NOT_REQUIRED; pending actions
    cannot pass by being placed in the optional research/questions field. Fresh
    provider observations, evidence authenticity and domain relevance are external
    host obligations. No callbacks, writes, retries or audit promotion occur here.
    """
    validate_analysis_plan(binding, required_domains)
    _require(type(report) is dict and set(report) ==
             {'schema', 'binding', 'output_text', 'domains'})
    _require(report['schema'] == 'nexus.analysis-evidence.v1'
             and type(report['schema']) is str)
    _require(type(report['binding']) is dict)
    validate_analysis_plan(report['binding'], required_domains)
    _require(report['binding'] == binding)
    _require(_text(report['output_text'], 1_048_576))
    _require(hashlib.sha256(report['output_text'].encode('utf-8')).hexdigest()
             == binding['output_sha256'])
    _require(type(report['domains']) is list
             and len(report['domains']) == len(required_domains))
    names = []
    for domain in report['domains']:
        _require(type(domain) is dict and set(domain) == _DOMAIN_FIELDS)
        _require(_text(domain['name'], 160))
        names.append(domain['name'])
        for field in ('relevance', 'contribution', 'knowledge_impact',
                      'full_potential', 'questions'):
            _require(_text(domain[field]))
        action = domain['required_action']
        _require(type(action) is dict and set(action) ==
                 {'status', 'reason', 'evidence_refs'})
        _require(type(action['status']) is str
                 and action['status'] in ('VERIFIED', 'NOT_REQUIRED'))
        _require(_text(action['reason']))
        if action['status'] == 'VERIFIED':
            _refs(action['evidence_refs'])
        else:
            _require(type(action['evidence_refs']) is list
                     and len(action['evidence_refs']) <= 100)
            if action['evidence_refs']:
                _refs(action['evidence_refs'])
        verification = domain['verification']
        _require(type(verification) is dict and set(verification) ==
                 {'status', 'evidence_refs'})
        _require(type(verification['status']) is str
                 and verification['status'] == 'VERIFIED')
        _refs(verification['evidence_refs'])
    _require(len(set(names)) == len(names)
             and set(names) == set(required_domains))
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    _require(len(encoded) <= 1_048_576)
    return hashlib.sha256(encoded).hexdigest()
