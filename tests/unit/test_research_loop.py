import copy
import unittest
from nexus_sandbox.research_loop import initial_state, run_research


def question(name):
    return dict(id=name, question='Investigate '+name, scope_reason='Within synthetic mission')


def assessment(disposition='RESOLVED', **changes):
    data=dict(disposition=disposition, reason='Synthetic documented assessment',
              attempted_queries=['synthetic query'], evidence=[], followups=[], connections=[])
    data.update(changes)
    return data


class ResearchLoopTests(unittest.TestCase):
    def setUp(self):
        self.binding=dict(mission_id='synthetic:mission', source_revision='synthetic:v1',
                          policy_revision='synthetic:p1', code_revision='synthetic:c1')
        self.store=initial_state(self.binding, [question('one')])
        self.calls=[]

    def read(self, _):
        return copy.deepcopy(self.store)

    def save(self, _, state):
        self.store=copy.deepcopy(state)

    def run_loop(self, researcher=None, **kwargs):
        def default(q, state):
            self.calls.append(q['id'])
            return assessment()
        return run_research(self.binding, researcher or default, self.save, self.read, **kwargs)

    def test_followup_is_researched_in_same_mission(self):
        def researcher(q, state):
            self.calls.append(q['id'])
            return assessment(followups=[question('two')] if q['id']=='one' else [])
        result=self.run_loop(researcher)
        self.assertEqual(result['status'], 'FRONTIER_EXHAUSTED')
        self.assertEqual(self.calls, ['one','two'])

    def test_budget_pause_retains_frontier_and_resume_skips_confirmed(self):
        first=self.run_loop(lambda q,s:assessment(followups=[question('two')]), max_steps=1)
        self.assertEqual(first['status'], 'PAUSED_BUDGET')
        second=self.run_loop()
        self.assertEqual(second['status'], 'FRONTIER_EXHAUSTED')
        self.assertEqual(self.calls, ['two'])

    def test_blocked_question_does_not_prevent_other_research(self):
        self.store=initial_state(self.binding,[question('one'),question('two')])
        result=self.run_loop(lambda q,s:assessment('BLOCKED' if q['id']=='one' else 'RESOLVED'))
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(len(result['state']['history']),2)

    def test_interruption_retains_pending_and_does_not_replay(self):
        def interrupted(q,s):
            raise OSError('synthetic interruption')
        self.assertEqual(self.run_loop(interrupted)['status'], 'BLOCKED_CHECKPOINT_OR_RESEARCH')
        self.assertEqual(self.store['pending'],'one')
        self.assertEqual(self.run_loop()['status'], 'BLOCKED_RECONCILE')
        self.assertEqual(self.calls,[])

    def test_duplicate_evidence_and_question_do_not_inflate(self):
        evidence=dict(id='e1', source_ref='synthetic:source', claim='claim', classification='SOURCE_CLAIM')
        def researcher(q,s):
            return assessment(evidence=[evidence,evidence],followups=[question('two'),question('two')])
        result=self.run_loop(researcher)
        self.assertEqual(result['status'],'FRONTIER_EXHAUSTED')
        self.assertEqual(len(result['state']['evidence']),1)
        self.assertEqual(len(result['state']['questions']),2)

    def test_contradiction_and_evidenced_connection_preserved(self):
        evidence=dict(id='e1',source_ref='synthetic:source',claim='conflicting claim',classification='CONTRADICTION')
        connection=dict(statement='Possible relation',classification='HYPOTHESIS',evidence_ids=['e1'],
                        counterexamples=['Alternative explanation remains'])
        result=self.run_loop(lambda q,s:assessment(evidence=[evidence],connections=[connection]))
        self.assertEqual(result['state']['evidence']['e1']['classification'],'CONTRADICTION')
        self.assertEqual(result['state']['connections'],[connection])

    def test_connection_without_evidence_holds(self):
        connection=dict(statement='Unsupported',classification='HYPOTHESIS',evidence_ids=['missing'],counterexamples=[])
        result=self.run_loop(lambda q,s:assessment(connections=[connection]))
        self.assertEqual(result['status'],'BLOCKED_CHECKPOINT_OR_RESEARCH')
        self.assertEqual(self.store['pending'],'one')

    def test_evidence_or_question_identity_conflict_holds(self):
        bad=question('one');bad['question']='Different question'
        self.assertEqual(self.run_loop(lambda q,s:assessment(followups=[bad]))['status'],
                         'BLOCKED_CHECKPOINT_OR_RESEARCH')

    def test_empty_queries_or_unknown_disposition_do_not_exhaust(self):
        for changes in ({'attempted_queries':[]},{'disposition':'DONE'},{'reason':''}):
            self.store=initial_state(self.binding,[question('one')])
            self.assertEqual(self.run_loop(lambda q,s:assessment(**changes))['status'],
                             'BLOCKED_CHECKPOINT_OR_RESEARCH')

    def test_missing_or_misbound_state_holds_before_callback(self):
        for state in (None,dict(self.store,binding=dict(self.binding,source_revision='wrong'))):
            self.store=state
            self.assertEqual(self.run_loop()['status'],'BLOCKED_CHECKPOINT_OR_RESEARCH')
            self.assertEqual(self.calls,[])

    def test_failed_intent_readback_prevents_research(self):
        def bad_save(_,state):
            self.store=dict(state,pending=None)
        result=run_research(self.binding,lambda q,s:self.calls.append(q),bad_save,self.read)
        self.assertEqual(result['status'],'BLOCKED_CHECKPOINT_OR_RESEARCH')
        self.assertEqual(self.calls,[])

    def test_completed_frontier_noop_and_boolean_budget_rejected(self):
        self.run_loop()
        self.calls=[]
        self.assertEqual(self.run_loop()['status'],'FRONTIER_EXHAUSTED')
        self.assertEqual(self.calls,[])
        with self.assertRaises(ValueError):self.run_loop(max_steps=True)


if __name__=='__main__':unittest.main()
