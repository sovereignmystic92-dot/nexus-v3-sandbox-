"""Read-only Cortex provider bridge must never manufacture identity or version."""
import unittest
from nexus_sandbox.gate_bound_connector import CortexConnectorReadHost


class CortexConnectorBridgeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.identity = {"provider": "CORTEX", "principal": "viewer",
                         "authenticated": True}
        self.response = {
            "context_access": {"permissions": ["module.view"], "is_owner": False},
            "context_get": {"name": "Nexus Sandbox CP02", "revision": "r1",
                            "complete": True, "truncated": False},
        }
        def invoke(method, args):
            self.calls.append((method, dict(args)))
            return {"structuredContent": dict(self.response[method])}
        self.invoke = invoke
        self.host = CortexConnectorReadHost(
            invoke=self.invoke, identity_exact=lambda: dict(self.identity),
            module_names={"synthetic:cp02": "Nexus Sandbox CP02"})

    def test_complete_host_supplied_observation(self):
        self.assertEqual(self.host.permissions_exact("synthetic:cp02")["permissions"],
                         ["module.view"])
        self.assertEqual(self.host.read_exact("synthetic:cp02")["revision"], "r1")
        self.assertEqual([m for m, _ in self.calls],
                         ["context_access", "context_get"])

    def test_missing_identity_blocks_before_transport(self):
        self.host._identity_exact = lambda: None
        with self.assertRaises(ValueError):
            self.host.permissions_exact("synthetic:cp02")
        self.assertEqual(self.calls, [])

    def test_forged_unauthenticated_identity_blocks(self):
        self.identity["authenticated"] = "true"
        with self.assertRaises(ValueError):
            self.host.read_exact("synthetic:cp02")
        self.assertEqual(self.calls, [])

    def test_wrong_scope_does_not_call_provider(self):
        with self.assertRaises(ValueError):
            self.host.permissions_exact("synthetic:other")
        self.assertEqual(self.calls, [])

    def test_missing_revision_holds_instead_of_inventing(self):
        del self.response["context_get"]["revision"]
        with self.assertRaises(ValueError):
            self.host.read_exact("synthetic:cp02")

    def test_incomplete_metadata_never_promoted(self):
        for key, value in (("complete", "true"), ("truncated", None)):
            original = self.response["context_get"][key]
            self.response["context_get"][key] = value
            with self.assertRaises(ValueError):
                self.host.read_exact("synthetic:cp02")
            self.response["context_get"][key] = original

    def test_wrong_module_holds(self):
        self.response["context_get"]["name"] = "Nexus Sandbox Other"
        with self.assertRaises(ValueError):
            self.host.read_exact("synthetic:cp02")

    def test_access_report_wrong_shape_holds(self):
        del self.response["context_access"]["is_owner"]
        with self.assertRaises(ValueError):
            self.host.permissions_exact("synthetic:cp02")

    def test_invoke_cannot_dispatch_write(self):
        with self.assertRaises(ValueError):
            self.host._call("context_update", "synthetic:cp02")
        self.assertEqual(self.calls, [])

    def test_tool_error_holds(self):
        self.host._invoke = lambda method, args: {"isError": True}
        with self.assertRaises(ValueError):
            self.host.read_exact("synthetic:cp02")


if __name__ == "__main__":
    unittest.main()
