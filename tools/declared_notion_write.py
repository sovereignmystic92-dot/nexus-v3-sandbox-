"""Opt-in declared-review handoff to the existing single-worker write boundary.

Trusted host supplies fresh context/reviews, exact enrollment and lossless read /
write callbacks. No connector, scheduler, credential or native-gate bypass.
"""
from copy import deepcopy
from uuid import UUID

from approval_gate import Hold
from declared_review_gate import authorize_declared
from nexus_sandbox.approved_writes import ApprovedWriteBoundary, WriteHold


def execute(journal, *, request_id, context, author_session, owner_decision,
            enrolled_destination, before_hash, payload, observe, read, write,
            custody=None):
    """Execute only this operation after rechecking host-observed bindings.

    observe() returns (current_context, current_review_records). Review digests
    must bind the full ApprovedWriteBoundary intent hash, including before/payload.
    Callbacks must target an already enrolled exact page and return complete JSON
    snapshots; truncated/normalized connector text is not a lossless snapshot.
    The host must separately establish current authority and native gates.
    """
    expected = deepcopy(context)
    destination = expected.get('destination')
    try:
        page_id = enrolled_destination.removeprefix('notion:')
        if (not enrolled_destination.startswith('notion:')
                or str(UUID(page_id)) != page_id
                or destination != enrolled_destination):
            raise ValueError()
    except (ValueError, AttributeError):
        raise Hold('One exact host-enrolled Notion page required') from None

    accepted = None

    def approve(intent, digest):
        nonlocal accepted
        current, records = observe()
        if (current != expected or digest != expected.get('request_sha256')
                or intent['revision'] != expected.get('head_sha')
                or intent['operation'] != expected.get('operation')
                or intent['destination'] != destination):
            raise WriteHold('Changed review context or misbound write intent')
        receipt = authorize_declared(records, context=current,
            author_session=author_session, owner_decision=owner_decision,
            enrolled_destination=enrolled_destination)
        if accepted is not None and receipt != accepted:
            raise WriteHold('Review observations changed before dispatch')
        accepted = receipt
        # Internal compatibility receipt; evidence class remains explicitly declared.
        return dict(intent, verdict='REVIEW_RECEIPTS_ACCEPTED',
                    request_sha256=digest, evidence_class=receipt['evidence_class'])

    def dispatch(target, value):
        if custody is not None:
            custody.save_verified(journal, request_id, expected)
        # Reobserve after the baseline read and immediately before the callback.
        approve(dict(revision=expected['head_sha'], operation=expected['operation'],
                     destination=destination), expected['request_sha256'])
        write(target, value)

    boundary = ApprovedWriteBoundary(journal, approve, read, dispatch)
    result = boundary.execute(request_id, expected['head_sha'], destination,
                              before_hash, payload)
    if custody is not None:
        try:
            result['journal_custody'] = custody.save_verified(journal, request_id, expected)
        except Exception:
            # Mutation may already be verified; saved DISPATCHING custody is the
            # reconciliation anchor. Never report overall durable completion.
            raise WriteHold('Result custody uncertain; reconcile saved intent without replay') from None
    result.update(evidence_class=accepted['evidence_class'],
                  identity_status=accepted['identity_status'],
                  review_digests=accepted['review_digests'])
    return result
