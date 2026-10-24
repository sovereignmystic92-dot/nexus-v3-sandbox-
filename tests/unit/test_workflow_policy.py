import hashlib
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from verify_workflows import verify


class WorkflowPolicyTests(unittest.TestCase):
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
