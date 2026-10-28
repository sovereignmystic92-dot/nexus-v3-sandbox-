"""Strict checkpoint wire format; caller supplies trusted custody/authority.

No transport, enrollment, provider write or automatic missing-state recovery.
Exact bindings must come from current authorized job metadata, not the input.
"""
import json
from hashlib import sha256
from .processing_pipeline import Receipt, STAGES

FIELDS = {'run_id','source_id','source_sha256','destination_id',
          'policy_revision','code_revision','schema_version'}


def binding_ok(value):
    return (type(value) is dict and set(value)==FIELDS
            and type(value['schema_version']) is int and value['schema_version']==1
            and all(type(value[k]) is str and 0<len(value[k])<=4096
                    for k in FIELDS-{'schema_version'})
            and len(value['source_sha256'])==64
            and all(c in '0123456789abcdef' for c in value['source_sha256']))


def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate JSON key')
        result[key]=value
    return result


def decode(text, expected_binding):
    if not binding_ok(expected_binding): raise ValueError('Trusted binding required')
    if type(text) is not str or len(text.encode('utf-8'))>1048576:
        raise ValueError('Bounded checkpoint text required')
    value=json.loads(text, object_pairs_hook=unique_pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if (type(value) is not dict or set(value)!={'binding','receipts','pending'}
            or not binding_ok(value['binding']) or value['binding']!=expected_binding
            or type(value['receipts']) is not list or len(value['receipts'])>len(STAGES)):
        raise ValueError('Malformed or misbound checkpoint')
    receipts=[]
    for index,r in enumerate(value['receipts']):
        if (type(r) is not dict or set(r)!={'run_id','stage','verified','evidence_refs'}
                or type(r['run_id']) is not str or r['run_id']!=expected_binding['run_id']
                or type(r['stage']) is not str or r['stage']!=STAGES[index]
                or r['verified'] is not True or type(r['evidence_refs']) is not list
                or not r['evidence_refs'] or len(r['evidence_refs'])>100
                or any(type(x) is not str or not x or len(x)>4096 for x in r['evidence_refs'])):
            raise ValueError('Malformed ordered receipt')
        receipts.append(Receipt(r['run_id'],r['stage'],True,tuple(r['evidence_refs'])))
    pending=value['pending']
    next_stage=STAGES[len(receipts)] if len(receipts)<len(STAGES) else None
    if pending is not None and (type(pending) is not str or pending!=next_stage):
        raise ValueError('Misordered intent')
    return dict(binding=value['binding'],receipts=tuple(receipts),pending=pending)


def encode(state, expected_binding):
    if type(state) is not dict or type(state.get('receipts')) is not tuple:
        raise ValueError('Typed checkpoint required')
    rows=[]
    for r in state['receipts']:
        if type(r) is not Receipt or type(r.evidence_refs) is not tuple:
            raise ValueError('Typed receipt required')
        rows.append(dict(run_id=r.run_id,stage=r.stage,verified=r.verified,
                         evidence_refs=list(r.evidence_refs)))
    wire=dict(state,receipts=rows)
    text=json.dumps(wire,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
    decode(text,expected_binding)
    return text


class CheckpointAdapter:
    """Bridge string transport to pipeline callbacks; no implicit initialize.

    write_text/read_text must address the same pre-enrolled job and independently
    observe storage. A write acknowledgment never constitutes readback.
    """
    def __init__(self,binding,read_text,write_text):
        if not binding_ok(binding): raise ValueError('Trusted binding required')
        self.binding=dict(binding)
        self.read_text,self.write_text=read_text,write_text
    def read(self,key):
        if key!=self.binding['run_id']: raise ValueError('Wrong job')
        return decode(self.read_text(key),self.binding)
    def save(self,key,state):
        if key!=self.binding['run_id']: raise ValueError('Wrong job')
        self.write_text(key,encode(state,self.binding))


def reconcile_report(records, *, complete, marker, destination, payload_sha256):
    """Classify a fully enumerated synthetic report inventory; never write.

    Records are trusted structured observations, not raw page/body text. A live
    parser must independently establish record boundaries and transport identity.
    Even zero matches never authorizes replay of an uncertain append.
    """
    if (complete is not True or type(records) is not list
            or type(marker) is not str or not marker
            or type(destination) is not str or not destination
            or type(payload_sha256) is not str or len(payload_sha256)!=64
            or any(c not in '0123456789abcdef' for c in payload_sha256)):
        return 'UNKNOWN'
    matches=[]
    for record in records:
        if (type(record) is not dict or set(record)!={'marker','destination','payload'}
                or any(type(v) is not str for v in record.values())):
            return 'UNKNOWN'
        if record['marker']==marker:
            matches.append(record)
    if len(matches)>1: return 'BLOCKED_DUPLICATE'
    if not matches: return 'UNKNOWN_ABSENT'
    record=matches[0]
    if record['destination']!=destination: return 'BLOCKED_MISMATCH'
    try: actual=sha256(record['payload'].encode('utf-8')).hexdigest()
    except UnicodeError: return 'UNKNOWN'
    return 'VERIFIED_OBSERVATION' if actual==payload_sha256 else 'BLOCKED_MISMATCH'
