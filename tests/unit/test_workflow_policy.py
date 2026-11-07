import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from verify_workflows import verify


class WorkflowPolicyTests(unittest.TestCase):
    def test_inventory_diagnostics_distinguish_all_differences(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / '.github/workflows'
            folder.mkdir(parents=True)
            (folder / 'changed.yml').write_text('private workflow body')
            (folder / 'new-z.yml').write_text('on: push\n')
            (folder / 'new-a.yml').write_text('on: push\n')
            policy = {'changed.yml': '0' * 64, 'removed.yml': '1' * 64}
            with self.assertRaises(ValueError) as caught:
                verify(temp, policy)
            message = str(caught.exception)
            details = json.loads(message.split(': ', 1)[1])
            self.assertEqual(details, {
                'unreviewed': ['new-a.yml', 'new-z.yml'],
                'missing': ['removed.yml'], 'changed': ['changed.yml'],
            })
            self.assertNotIn('private workflow body', message)
            self.assertEqual(policy, {'changed.yml': '0' * 64, 'removed.yml': '1' * 64})

    def test_new_trigger_or_extra_workflow_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'.github/workflows';folder.mkdir(parents=True)
            p=folder/'test.yml';p.write_text('on: pull_request\n')
            policy={p.name:hashlib.sha256(p.read_bytes()).hexdigest()}
            self.assertEqual(verify(temp,policy),['test.yml'])
            p.write_text('on: schedule\n')
            with self.assertRaises(ValueError):verify(temp,policy)
            policy[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
            (folder/'extra.yml').write_text('on: push\n')
            with self.assertRaises(ValueError):verify(temp,policy)

    def test_missing_or_symlinked_workflow_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'.github/workflows';folder.mkdir(parents=True)
            policy={'test.yml':'0'*64}
            with self.assertRaises(ValueError):verify(temp,policy)
            target=Path(temp)/'outside';target.write_text('on: push\n')
            (folder/'test.yml').symlink_to(target)
            with self.assertRaises(ValueError):verify(temp,policy)
