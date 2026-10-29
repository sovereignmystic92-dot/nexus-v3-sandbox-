"""Owner-accepted declared attribution, sandbox-only; no provider identity claim."""
from approval_gate import Hold, load_json
import review_binding as binding

OWNER_DECISION = 'NXS-OWNER-DECLARED-ATTRIBUTION-20261029'
FIELDS = {'author_session','reviewer_agent','reviewer_session','verdict','findings',
          'initial_findings_recorded_independently','exposure_disclosure'}
ROW = {'wire','digest','source','agent','session','body','evidence'}


def authorize_declared(records, *, context, author_session, owner_decision):
    """Validate host-observed bound records, not their writer authentication.

    Host supplies current context and independently retained snapshots. No network,
    provider write, credential, automatic dispatch or self-enrollment occurs.
    """
    binding.context_ok(context)
    if (owner_decision != OWNER_DECISION or context['destination'] != 'github:main'
            or not binding.text(author_session,200)
            or type(records) is not list or len(records)!=2):
        raise Hold('Explicit bounded owner mode and two reviews required')
    sessions=set()
    sources=set()
    evidence=[]
    for row in records:
        if type(row) is not dict or set(row)!=ROW:
            raise Hold('Exact bound review record required')
        binding.verify(row['wire'],expected_context=context,expected_source=row['source'],
            expected_digest=row['digest'],expected_agent=row['agent'],
            expected_session=row['session'],review_body=row['body'],evidence=row['evidence'])
        body=load_json(row['body'])
        if (type(body) is not dict or set(body)!=FIELDS
                or body['author_session']!=author_session
                or body['reviewer_agent']!=row['agent']
                or body['reviewer_session']!=row['session']
                or body['verdict']!='PASS' or body['findings']!=[]
                or body['initial_findings_recorded_independently'] is not True
                or not binding.text(body['exposure_disclosure'],4096)
                or row['session']==author_session):
            raise Hold('Incomplete, unresolved or self-reviewed attribution')
        source=tuple(row['source'][k] for k in ('store','record_id'))
        if row['session'] in sessions or source in sources:
            raise Hold('Distinct review sessions and records required')
        sessions.add(row['session']);sources.add(source);evidence.append(row['digest'])
    return dict(verdict='OWNER_ACCEPTED_DECLARED_REVIEWS',evidence_class='OWNER_ACCEPTED_DECLARED_ATTRIBUTION',
        identity_status='SELF_DECLARED_NOT_PROVIDER_AUTHENTICATED',owner_decision=OWNER_DECISION,
        revision=context['head_sha'],base_revision=context['base_sha'],
        request_sha256=context['request_sha256'],operation=context['operation'],
        destination=context['destination'],review_digests=evidence,
        dispatch_authorized=False)
