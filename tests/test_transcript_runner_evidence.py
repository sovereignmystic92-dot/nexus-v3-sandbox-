import unittest
from nexus_sandbox.transcript_live_handoff import Handoff
from nexus_sandbox.transcript_runner_evidence import RunnerEvidence, classify_execution

MATCHED=Handoff("READBACK_MATCHED","RECORD_DURABLE_EXECUTION_RECEIPT","a"*64,"notion-1","cortex-1")
BLOCKED=Handoff("BLOCKED","NOTION_FULL_FIDELITY_READBACK_REQUIRED","a"*64)

def evidence(**overrides):
    d=dict(authenticated_trigger=True,authenticated_notion=True,
           authenticated_cortex=True,durable_receipt_id="receipt-1",
           receipt_readback_matches=True)
    d.update(overrides)
    return RunnerEvidence(**d)

class RunnerEvidenceTests(unittest.TestCase):
    def test_full_evidence(self):
        self.assertEqual(classify_execution(MATCHED,evidence()),"VERIFIED")
    def test_blocked_handoff(self):
        self.assertEqual(classify_execution(BLOCKED,evidence()),"BLOCKED")
    def test_missing_trigger_auth(self):
        self.assertEqual(classify_execution(MATCHED,evidence(authenticated_trigger=False)),"INCOMPLETE")
    def test_missing_notion_auth(self):
        self.assertEqual(classify_execution(MATCHED,evidence(authenticated_notion=False)),"INCOMPLETE")
    def test_missing_cortex_auth(self):
        self.assertEqual(classify_execution(MATCHED,evidence(authenticated_cortex=False)),"INCOMPLETE")
    def test_missing_receipt(self):
        self.assertEqual(classify_execution(MATCHED,evidence(durable_receipt_id="")),"INCOMPLETE")
    def test_receipt_readback_mismatch(self):
        self.assertEqual(classify_execution(MATCHED,evidence(receipt_readback_matches=False)),"INCOMPLETE")
    def test_boolean_impersonation_rejected(self):
        with self.assertRaises(ValueError):
            classify_execution(MATCHED,evidence(authenticated_trigger=1))
