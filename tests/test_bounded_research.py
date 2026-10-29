import unittest
from nexus_sandbox.bounded_research import ResearchBudget, BudgetExhausted, validate_outcome


class Tests(unittest.TestCase):
    def test_failed_attempt_counts(self):
        budget = ResearchBudget(1, 10)
        def fail(): raise RuntimeError('failure')
        with self.assertRaises(RuntimeError): budget.invoke('search', fail)
        with self.assertRaises(BudgetExhausted): budget.invoke('read', lambda: None)

    def test_expired_or_late(self):
        now = [0]
        budget = ResearchBudget(2, 1, clock=lambda: now[0])
        def late(): now[0] = 2; return 'result'
        with self.assertRaises(BudgetExhausted): budget.invoke('search', late)
        with self.assertRaises(BudgetExhausted): budget.invoke('read', lambda: None)

    def test_evidence_and_no_result(self):
        with self.assertRaises(ValueError): validate_outcome('RESOLVED', [])
        with self.assertRaises(ValueError): validate_outcome('UNPRODUCTIVE', [])
        validate_outcome('UNPRODUCTIVE', [], {'query':'q','source':'s','scope':'bounded'})
        validate_outcome('RESOLVED', [{'source_ref':'url', 'claim':'c'}])
        validate_outcome('BLOCKED', [])

if __name__ == '__main__': unittest.main()
