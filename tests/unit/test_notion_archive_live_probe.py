import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('archive_probe',
    Path(__file__).resolve().parents[2] / 'tools/notion_archive_live_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class LiveProbeTests(unittest.TestCase):
    dest = '12345678-1234-1234-1234-123456789abc'

    def test_fixed_source_write_budget(self):
        prepared = probe.prepare_transcript(probe.RAW, 256)
        self.assertEqual(len(prepared['chunks']), 3)
        self.assertEqual(''.join(prepared['chunks']), probe.RAW)

    def test_configuration_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(probe.main(), 2)

    def test_readonly_rejects_append(self):
        c = probe.BoundClient(self.dest, 'synthetic-token', False)
        with self.assertRaises(ValueError):
            c.append(block_id=self.dest, children=[{}], position={'type':'start'})
        self.assertEqual(c.writes, 0)

    def test_foreign_paths_rejected_before_network(self):
        c = probe.BoundClient(self.dest, 'synthetic-token', True)
        for method, path in [('GET','/v1/users/me'), ('PATCH','/v1/pages/other'),
                             ('POST','/v1/pages')]:
            with self.subTest(method=method), self.assertRaises(ValueError):
                c.request(method,path)

    def test_failed_request_consumes_budget_and_sanitizes(self):
        c = probe.BoundClient(self.dest, 'synthetic-token', True)
        with patch.object(c.opener, 'open', side_effect=RuntimeError('private-body')):
            with self.assertRaisesRegex(RuntimeError, '^provider request unavailable; reconcile before retry$'):
                c.append(block_id=self.dest, children=[{}], position={'type':'start'})
        self.assertEqual(c.writes, 1)
        with self.assertRaises(ValueError):
            c.append(block_id=self.dest, children=[{}], position={'type':'start'})

    def test_redirect_refused(self):
        with self.assertRaises(ValueError):
            probe.NoRedirect().redirect_request(None,None,None,None,None,None)


if __name__ == '__main__':
    unittest.main()
