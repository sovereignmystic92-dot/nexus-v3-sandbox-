import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import declared_notion_write as adapter
import declared_review_gate as gate
import review_binding as binding
from nexus_sandbox.approved_writes import content_hash, WriteHold


class NotionDeclaredTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = str(Path(self.temp.name) / 'intent.sqlite')
        self.dest = 'notion:4018c067-daa4-8122-b82e-c2ae8067d021'
        self.value = {'blocks': ['synthetic existing']}
        self.target = {'blocks': ['synthetic existing', 'synthetic receipt']}
        self.before = content_hash(self.value)
        intent = dict(revision='a'*40, operation='routine_write', destination=self.dest,
                      before_sha256=self.before, payload_sha256=content_hash(self.target))
        self.context = dict(repository=binding.REPOSITORY, pr_number=57, head_sha='a'*40,
            base_sha='b'*40, candidate_sha='c'*40, operation='routine_write',
            destination=self.dest, request_sha256=content_hash(intent), policy_revision='synthetic')
        self.rows = []
        self.calls = []
        for i, agent in enumerate(('ChatGPT', 'Gemini')):
            source = dict(store='github', record_id='synthetic-review:'+str(i), record_revision='1')
            session = 'review-'+str(i)
            body = json.dumps(dict(author_session='author', reviewer_agent=agent,
                reviewer_session=session, verdict='PASS', findings=[],
                initial_findings_recorded_independently=True,
                exposure_disclosure='Synthetic isolated session'))
            evidence = {'synthetic:tests': 'e'*64}
            wire, digest = binding.bind(self.context, source, agent, session, body, evidence)
            self.rows.append(dict(wire=wire, digest=digest, source=source, agent=agent,
                                  session=session, body=body, evidence=evidence))

    def observe(self):
        return copy.deepcopy(self.context), copy.deepcopy(self.rows)

    def read(self, destination):
        self.assertEqual(destination, self.dest)
        return copy.deepcopy(self.value)

    def write(self, destination, payload):
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute('SELECT state FROM approved_writes').fetchone()[0],
                             'DISPATCHING')
        self.calls.append(destination)
        self.value = copy.deepcopy(payload)

    def run_adapter(self, **overrides):
        kwargs = dict(request_id='synthetic:one', context=copy.deepcopy(self.context),
            author_session='author', owner_decision=gate.OWNER_DECISION,
            enrolled_destination=self.dest, before_hash=self.before, payload=self.target,
            observe=self.observe, read=self.read, write=self.write)
        kwargs.update(overrides)
        return adapter.execute(self.journal, **kwargs)

    def test_declared_chat_gemini_dispatch_and_readback_then_resume(self):
        result = self.run_adapter()
        self.assertTrue(result['write_attempted'])
        self.assertEqual(result['identity_status'], 'SELF_DECLARED_NOT_PROVIDER_AUTHENTICATED')
        self.assertFalse(self.run_adapter()['write_attempted'])
        self.assertEqual(self.calls, [self.dest])

    def test_unenrolled_or_noncanonical_destination_has_no_effect(self):
        for dest in ('github:main', self.dest.upper(), 'notion:other', None):
            with self.subTest(dest=dest), self.assertRaises(gate.Hold):
                self.run_adapter(enrolled_destination=dest)
        self.assertEqual(self.calls, [])

    def test_review_for_other_payload_baseline_or_context_holds(self):
        for kw in (dict(payload={'blocks': ['changed']}), dict(before_hash='f'*64),
                   dict(context=dict(self.context, base_sha='f'*40))):
            with self.subTest(kw=kw), self.assertRaises(WriteHold):
                self.run_adapter(**kw)
        self.assertEqual(self.calls, [])

    def test_context_change_during_baseline_read_blocks_dispatch(self):
        def changed(target):
            result = self.read(target)
            self.context['head_sha'] = 'f'*40
            return result
        with self.assertRaises(WriteHold):
            self.run_adapter(read=changed)
        self.assertEqual(self.calls, [])

    def test_changed_review_snapshot_before_dispatch_holds(self):
        def changed(target):
            result = self.read(target)
            self.rows[0]['body'] += ' '
            return result
        with self.assertRaises(WriteHold):
            self.run_adapter(read=changed)
        self.assertEqual(self.calls, [])

    def test_lost_ack_reconciles_without_second_mutation(self):
        def lost(target, payload):
            self.write(target, payload)
            raise TimeoutError()
        with self.assertRaises(WriteHold):
            self.run_adapter(write=lost)
        self.assertFalse(self.run_adapter()['write_attempted'])
        self.assertEqual(len(self.calls), 1)

    def test_unknown_unapplied_outcome_is_not_replayed(self):
        def lost(target, payload):
            self.calls.append(target)
            raise TimeoutError()
        with self.assertRaises(WriteHold):
            self.run_adapter(write=lost)
        with self.assertRaises(WriteHold):
            self.run_adapter()
        self.assertEqual(len(self.calls), 1)

    def test_missing_reviews_or_owner_decision_never_write(self):
        with self.assertRaises(gate.Hold):
            self.run_adapter(owner_decision='not-authorized')
        self.rows = self.rows[:1]
        with self.assertRaises(gate.Hold):
            self.run_adapter()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
