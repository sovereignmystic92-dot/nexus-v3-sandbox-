"""Offline review-content binding only; no authentication, approval or provider IO.

Expected context/source and saved digest must come from independent trusted custody.
A packet read alongside its own digest is not a trust anchor. No existing approval
gate accepts this packet; live identity mapping and integration remain unimplemented.
"""
import hashlib
import json
from approval_gate import Hold, exact_sha, load_json

REPOSITORY = 'sovereignmystic92-dot/nexus-v3-sandbox-'
CONTEXT = {'repository','pr_number','head_sha','base_sha','candidate_sha',
           'operation','destination','request_sha256','policy_revision'}
SOURCE = {'store','record_id','record_revision'}
FIELDS = {'schema_version','context','source','claimed_agent','session_id',
          'review_sha256','evidence'}
MAX_BYTES = 262144


def text(value, limit=4096):
    return type(value) is str and 0 < len(value) <= limit and value == value.strip()


def digest_ok(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def sha256(value):
    if type(value) is not str:
        raise Hold('Exact text required')
    try:
        return hashlib.sha256(value.encode('utf-8')).hexdigest()
    except UnicodeError:
        raise Hold('UTF-8 required') from None


def context_ok(c):
    if (type(c) is not dict or set(c)!=CONTEXT or c['repository']!=REPOSITORY
            or type(c['pr_number']) is not int or c['pr_number']<=0
            or c['operation']!='routine_write'
            or not text(c['destination']) or not text(c['policy_revision'])
            or not digest_ok(c['request_sha256'])):
        raise Hold('Complete bounded sandbox review context required')
    for name in ('head_sha','base_sha','candidate_sha'):
        exact_sha(c[name])
    return c


def source_ok(s):
    if (type(s) is not dict or set(s)!=SOURCE or s['store'] not in ('cortex','github')
            or not text(s['record_id']) or not text(s['record_revision'])):
        raise Hold('Exact source record and revision required')
    return s


def evidence_ok(e):
    if (type(e) is not dict or not 1<=len(e)<=100 or
            any(not text(k) or not digest_ok(v) for k,v in e.items())):
        raise Hold('Evidence references with exact observed digests required')
    return e


def canonical(packet):
    try:
        wire=json.dumps(packet,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
    except (ValueError,TypeError):
        raise Hold('Canonical JSON required') from None
    if len(wire.encode('utf-8'))>MAX_BYTES:
        raise Hold('Review binding exceeds size limit')
    return wire


def validate(packet):
    if (type(packet) is not dict or set(packet)!=FIELDS
            or type(packet['schema_version']) is not int or packet['schema_version']!=1
            or packet['claimed_agent'] not in ('ChatGPT','Gemini')
            or not text(packet['session_id'],200) or not digest_ok(packet['review_sha256'])):
        raise Hold('Malformed review binding')
    context_ok(packet['context'])
    source_ok(packet['source'])
    evidence_ok(packet['evidence'])
    return packet


def bind(context, source, claimed_agent, session_id, review_body, evidence):
    """Return wire text and content digest, never an authenticated receipt."""
    if type(review_body) is not str or not review_body.strip() or len(review_body.encode('utf-8'))>65536:
        raise Hold('Bounded nonempty review required')
    packet=dict(schema_version=1,context=context,source=source,
                claimed_agent=claimed_agent,session_id=session_id,
                review_sha256=sha256(review_body),evidence=evidence)
    wire=canonical(validate(packet))
    return wire,sha256(wire)


def verify(wire, *, expected_context, expected_source, expected_digest,
           expected_agent, expected_session, review_body, evidence):
    """Match independently retained context/snapshot only; grants no authority.

    Fresh metadata, review body, and evidence digests must be independently fetched
    by the host. This function does not fetch them, authenticate them or attest
    their relevance, completeness, truth, temporal freshness or independence.
    """
    context_ok(expected_context)
    source_ok(expected_source)
    evidence_ok(evidence)
    if type(wire) is not str or len(wire.encode('utf-8'))>MAX_BYTES or not digest_ok(expected_digest):
        raise Hold('Bounded wire and independently retained digest required')
    packet=validate(load_json(wire))
    canonical_wire=canonical(packet)
    if (wire!=canonical_wire or sha256(wire)!=expected_digest
            or packet['context']!=expected_context or packet['source']!=expected_source
            or packet['claimed_agent']!=expected_agent or packet['session_id']!=expected_session
            or packet['review_sha256']!=sha256(review_body)
            or packet['evidence']!=evidence):
        raise Hold('Changed or misbound review snapshot')
    return {'status':'BOUND_UNAUTHENTICATED','approval_granted':False,
            'identity_status':'UNVERIFIED','packet_sha256':expected_digest}
