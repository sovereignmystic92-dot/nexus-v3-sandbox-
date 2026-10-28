"""Opt-in append-only checkpoint transport for one pre-enrolled audit job.

Injected fetch_page/append_text are host connector calls, not HTTP credentials.
Single trusted writer only; no CAS, event authentication or rollback guarantee.
"""
import hashlib
import json
import re
from uuid import UUID
from .checkpoint_json import decode, encode, unique_pairs
from .processing_pipeline import STAGES


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def transition(before,after):
    old,new=before['receipts'],after['receipts']
    if before['pending'] is None:
        allowed=(len(old)<len(STAGES) and new==old
                 and after['pending']==STAGES[len(old)])
    else:
        allowed=(len(new)==len(old)+1 and new[:-1]==old
                 and new[-1].stage==before['pending'] and after['pending'] is None)
    if not allowed:raise ValueError('Checkpoint transition regresses or skips intent/result')


class AuditCheckpointTransport:
    """No implicit enrollment. Host must bind current authority and callbacks.

    Fetch returns decoded Notion page export. Append receives exact page ID and
    one generated JSON block. Records are declarative checkpoint evidence only;
    body markers do not authenticate their author. Caller owns exclusive custody.
    """
    def __init__(self,page_id,binding,fetch_page,append_text):
        self.page_id=UUID(page_id).hex
        self.binding=dict(binding)
        # Validate supplied immutable binding via the adopted codec.
        encode(dict(binding=self.binding,receipts=(),pending=None),self.binding)
        if UUID(binding['destination_id']).hex!=self.page_id:
            raise ValueError('Destination not enrolled audit page')
        self.fetch_page,self.append_text=fetch_page,append_text
        self.last=None

    def _events(self):
        page=self.fetch_page(self.page_id)
        if (type(page) is not dict or UUID(page['id']).hex!=self.page_id
                or page.get('metadata',{}).get('type')!='page'
                or page.get('truncated') or page.get('unknown_block_count')
                or page.get('unknown_block_ids') or type(page.get('text')) is not str):
            raise ValueError('Complete bound page observation required')
        events=[]
        blocks=re.findall(r'^```json\n([\s\S]*?)\n```$',page['text'],re.MULTILINE)
        if len(blocks)!=len(re.findall(r'^```json$',page['text'],re.MULTILINE)):
            raise ValueError('Unterminated JSON block; inventory incomplete')
        for block in blocks:
            try: event=json.loads(block,object_pairs_hook=unique_pairs)
            except ValueError:
                # Even escaped event markers cannot make malformed records
                # disappear. Conservative failure includes unrelated JSON.
                raise ValueError('Malformed JSON; checkpoint inventory incomplete')
            if type(event) is not dict or event.get('event_type')!='NXS_CHECKPOINT_V1':
                continue
            if event.get('run_id')!=self.binding['run_id']:
                continue
            if (set(event)!={'event_type','run_id','page_id','sequence','previous','checkpoint'}
                    or event['page_id']!=self.page_id
                    or type(event['sequence']) is not int
                    or event['sequence']!=len(events)
                    or event['previous']!=(digest(events[-1]) if events else None)
                    or type(event['checkpoint']) is not str):
                raise ValueError('Conflicting checkpoint chain')
            checkpoint=decode(event['checkpoint'],self.binding)
            if not events and (checkpoint['receipts'] or checkpoint['pending'] is not None):
                raise ValueError('Enrollment must be initial empty state')
            if events:
                transition(decode(events[-1]['checkpoint'],self.binding),checkpoint)
            events.append(event)
        if not events: raise ValueError('Explicit enrollment missing; no write permitted')
        return events

    def read(self,key):
        if key!=self.binding['run_id']: raise ValueError('Wrong run')
        events=self._events()
        self.last=events[-1]
        return self.last['checkpoint']

    def save(self,key,text):
        if key!=self.binding['run_id']: raise ValueError('Wrong run')
        decode(text,self.binding)
        if self.last is None: raise ValueError('Read enrolled checkpoint before save')
        current=self._events()[-1]
        if current['checkpoint']==text:
            self.last=current
            return  # Lost acknowledgment reconciled; no repeated append.
        if current!=self.last:
            raise ValueError('Observed checkpoint changed; reconcile only')
        transition(decode(current['checkpoint'],self.binding),decode(text,self.binding))
        event=dict(event_type='NXS_CHECKPOINT_V1',run_id=key,page_id=self.page_id,
                   sequence=current['sequence']+1,previous=digest(current),checkpoint=text)
        # A failed/uncertain append forfeits this instance's write permission.
        self.last=None
        self.append_text(self.page_id,'\n```json\n'+canonical(event)+'\n```\n')
        observed=self._events()[-1]
        if observed!=event: raise ValueError('Append not independently observed')
        self.last=observed
