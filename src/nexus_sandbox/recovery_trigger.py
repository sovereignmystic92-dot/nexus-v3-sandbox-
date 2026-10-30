"""Event gate for the opt-in, read-only Nexus recovery checkpoint adapter.

An event is a wake-up signal, not authority. In particular, event-supplied
claims of permissions or inventory completeness are NEVER consumed as proof.
No scheduler, API listener, service connection, retry or provider write.
"""
import hashlib
import re

from .checkpoint_json import binding_ok
from .resume_decision import decide_resume

EVENT_FIELDS = frozenset({'event_type', 'event_id', 'run_id',
                          'checkpoint_sha256', 'source_sha256'})
EVENT_TYPE = 'NXS_CHECKPOINT_OBSERVED_V1'


def _blocked(action, reason):
    return dict(status='BLOCKED', next_action=action, reason=reason,
                completed=[], pending=None, event_accepted=False,
                automatic_execution=False, provider_writes=0,
                cp09='NOT_PROVEN')


def assess_checkpoint_event(event, checkpoint_text, trusted_binding, *,
                            expected_event_id, inventory_complete,
                            authority_verified):
    """Return a read-only resume assessment after strict event binding.

    The caller must obtain current authority, full inventory and a checkpoint
    from independently trusted channels. No event payload is allowed to set
    inventory_complete or authority_verified. Repeated events are safe because
    this function produces no effects, not because it owns a dedupe ledger.
    """
    if (type(inventory_complete) is not bool or
            type(authority_verified) is not bool):
        raise ValueError('Strict Boolean host assertions required')
    if not inventory_complete:
        return _blocked('OBTAIN_COMPLETE_INVENTORY',
                        'Independent complete checkpoint inventory required')
    if not authority_verified:
        return _blocked('VERIFY_CURRENT_AUTHORITY',
                        'Current operator/agent authority not established')
    if not binding_ok(trusted_binding):
        return _blocked('VERIFY_TRUSTED_BINDING', 'Trusted binding unavailable')
    if (type(expected_event_id) is not str or
            re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}', expected_event_id) is None):
        return _blocked('VERIFY_EVENT_ID', 'Host event identity unavailable')
    if (type(event) is not dict or set(event) != EVENT_FIELDS or
            any(type(v) is not str for v in event.values()) or
            event['event_type'] != EVENT_TYPE or
            event['event_id'] != expected_event_id or
            event['run_id'] != trusted_binding['run_id'] or
            event['source_sha256'] != trusted_binding['source_sha256'] or
            re.fullmatch(r'[0-9a-f]{64}', event['checkpoint_sha256']) is None):
        return _blocked('REJECT_EVENT', 'Event absent, unknown or misbound')
    if (type(checkpoint_text) is not str or
            len(checkpoint_text.encode('utf-8')) > 1048576 or
            hashlib.sha256(checkpoint_text.encode('utf-8')).hexdigest()
            != event['checkpoint_sha256']):
        return _blocked('RECONCILE_EVENT_AND_OBSERVATION',
                        'Event checkpoint digest does not match observation')
    decision = decide_resume(checkpoint_text, trusted_binding,
                             inventory_complete=True, authority_verified=True)
    return dict(status=decision.status, completed=list(decision.completed),
                pending=decision.pending, next_action=decision.next_action,
                reason=decision.reason, event_accepted=decision.status != 'BLOCKED',
                automatic_execution=False, provider_writes=0,
                cp09='NOT_PROVEN')
