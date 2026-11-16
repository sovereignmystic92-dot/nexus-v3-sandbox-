"""Bounded read-only callback integration: no false authorization or writes."""
import unittest
from nexus_sandbox.gate_bound_adapter import GATE_IDS
from nexus_sandbox.gate_bound_readonly import scoped_provider_read


class GateBoundReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.operation = {"id": "cp02:read:1", "principal": "viewer:synthetic",
                          "provider": "CORTEX", "target": "synthetic:module",
                          "action": "read", "synthetic": True}
        self.register = {g: "BLOCKED" for g in GATE_IDS}
        self.calls = 0

    def read(self, provider, target):
        self.calls += 1
        return {"provider": provider, "target": target,
                "principal": "viewer:synthetic", "revision": "r1",
                "complete": True, "truncated": False}

    def run_case(self, evidence=None, operation=None, read=None):
        return scoped_provider_read(
            operation=self.operation if operation is None else operation,
            checkpoint_statuses=self.register, applicable_gates=("CP02",),
            boundary_evidence={} if evidence is None else evidence,
            read_exact=self.read if read is None else read)

    def test_missing_evidence_does_not_invoke_provider(self):
        x = self.run_case()
        self.assertEqual(x.status, "HELD")
        self.assertEqual(self.calls, 0)
        self.assertEqual(x.outstanding, ("CP02",))

    def test_completed_read_remains_host_assertion_not_authorization(self):
        x = self.run_case({"CP02": True})
        self.assertEqual(x.status, "READBACK_MATCHED_HOST_ASSERTION")
        self.assertFalse(x.execution_authorized)
        self.assertEqual(x.provider_writes, 0)
        self.assertEqual(x.resource_revision, "r1")
        self.assertEqual(self.calls, 1)

    def test_denied_write_does_not_invoke_provider(self):
        x = self.run_case({"CP02": True},
                          operation=dict(self.operation, action="update"))
        self.assertEqual(x.status, "HELD")
        self.assertEqual(self.calls, 0)

    def test_wrong_provider_target_or_principal_holds(self):
        for key, value in (("provider", "NOTION"), ("target", "wrong"),
                           ("principal", "owner")):
            def wrong(provider, target, k=key, v=value):
                x = self.read(provider, target)
                x[k] = v
                return x
            x = self.run_case({"CP02": True}, read=wrong)
            self.assertEqual(x.status, "HELD")

    def test_incomplete_truncated_and_string_boolean_hold(self):
        for key, value in (("complete", False), ("truncated", True),
                           ("complete", "true")):
            def incorrect(provider, target, k=key, v=value):
                x = self.read(provider, target)
                x[k] = v
                return x
            self.assertEqual(self.run_case({"CP02": True}, read=incorrect).status, "HELD")

    def test_bad_revision_or_missing_fields_holds(self):
        for bad in ("", None):
            def invalid(provider, target, value=bad):
                x = self.read(provider, target)
                x["revision"] = value
                return x
            self.assertEqual(self.run_case({"CP02": True}, read=invalid).status, "HELD")
        def missing(provider, target):
            x = self.read(provider, target)
            del x["target"]
            return x
        self.assertEqual(self.run_case({"CP02": True}, read=missing).status, "HELD")

    def test_provider_exception_fails_closed(self):
        def fail(provider, target):
            raise RuntimeError("sensitive host error")
        x = self.run_case({"CP02": True}, read=fail)
        self.assertEqual(x.status, "HELD")
        self.assertEqual(x.next_action, "PROVIDER_READ_FAILED")

    def test_no_callback_holds(self):
        x = self.run_case({"CP02": True}, read=False)
        self.assertEqual(x.status, "HELD")
        self.assertEqual(self.calls, 0)


if __name__ == "__main__":
    unittest.main()
