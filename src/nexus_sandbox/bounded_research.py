"""Host-mediated research budget; no network, credentials, or scheduling."""
import time


class BudgetExhausted(RuntimeError):
    pass


class ResearchBudget:
    def __init__(self, max_calls, max_seconds, *, clock=time.monotonic):
        if type(max_calls) is not int or max_calls < 1 or type(max_seconds) not in (int, float) or not 0 < max_seconds <= 3600:
            raise ValueError('Invalid research budget')
        self.max_calls = max_calls
        self.deadline = clock() + max_seconds
        self.clock = clock
        self.calls = 0

    def invoke(self, operation, argument):
        if operation not in ('search', 'read') or not callable(argument):
            raise ValueError('Unrecognized operation')
        if self.calls >= self.max_calls or self.clock() >= self.deadline:
            raise BudgetExhausted('Research budget exhausted')
        self.calls += 1  # Count failed attempts too.
        result = argument()
        if self.clock() >= self.deadline:
            raise BudgetExhausted('Operation exceeded deadline; result unaccepted')
        return result


def validate_outcome(disposition, evidence, no_result_record=None):
    """Require traceable evidence or an explicit scoped negative search record."""
    if disposition not in ('RESOLVED', 'UNPRODUCTIVE', 'BLOCKED') or type(evidence) is not list:
        raise ValueError('Invalid outcome')
    for item in evidence:
        if type(item) is not dict or not all(type(item.get(k)) is str and item[k].strip() for k in ('source_ref', 'claim')):
            raise ValueError('Evidence requires source and claim')
    if disposition == 'RESOLVED' and not evidence:
        raise ValueError('Resolved requires evidence')
    if disposition == 'UNPRODUCTIVE' and not evidence:
        if type(no_result_record) is not dict or not all(type(no_result_record.get(k)) is str and no_result_record[k].strip() for k in ('query', 'source', 'scope')):
            raise ValueError('No-result requires search provenance')
