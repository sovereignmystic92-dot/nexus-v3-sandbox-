from dataclasses import replace
import unittest
from nexus_sandbox.record_readback import Binding, Observation, digest, verify

ID = '00000000-0000-0000-0000-000000000001'
PARENT = '00000000-0000-0000-0000-000000000002'
OTHER = '00000000-0000-0000-0000-000000000003'


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.binding = Binding(ID, PARENT, digest('unchanged source'))
        self.observation = Observation(ID, PARENT, 'unchanged source', True)

    def test_exact_read_and_repeat_invoke_reader_each_time(self):
        calls = []
        def reader(identifier):
            calls.append(identifier)
            return self.observation
        for _ in range(2):
            self.assertEqual(verify(self.binding, reader).status, 'VERIFIED_OBSERVATION')
        self.assertEqual(calls, [ID, ID])

    def test_wrong_identity_and_moved_parent_rejected(self):
        for change in ({'record_id': OTHER}, {'parent_id': OTHER}):
            self.assertEqual(verify(self.binding, lambda _: replace(
                self.observation, **change)).status, 'MISMATCH')

    def test_one_character_corruption_rejected(self):
        self.assertEqual(verify(self.binding, lambda _: replace(
            self.observation, payload='unchanged sources')).status, 'MISMATCH')

    def test_unknown_completeness_is_not_success(self):
        for complete in (False, None, 1, 'true'):
            self.assertEqual(verify(self.binding, lambda _: replace(
                self.observation, complete=complete)).status, 'UNKNOWN')

    def test_read_failure_does_not_leak_exception(self):
        def reader(_):
            raise RuntimeError('private-provider-detail')
        verdict = verify(self.binding, reader)
        self.assertEqual(verdict.status, 'UNKNOWN')
        self.assertNotIn('private-provider-detail', repr(verdict))

    def test_malformed_fields_hold(self):
        for value in (None, {}, replace(self.observation, record_id='bad'),
                      replace(self.observation, payload=None)):
            self.assertEqual(verify(self.binding, lambda _: value).status, 'UNKNOWN')

    def test_invalid_binding_rejected_before_read(self):
        with self.assertRaises(ValueError):
            verify(replace(self.binding, payload_sha256='bad'),
                   lambda _: self.fail('reader must not execute'))

    def test_uuid_format_differences_are_same_identity(self):
        value = replace(self.observation, record_id=ID.replace('-', ''))
        self.assertEqual(verify(self.binding, lambda _: value).status,
                         'VERIFIED_OBSERVATION')
