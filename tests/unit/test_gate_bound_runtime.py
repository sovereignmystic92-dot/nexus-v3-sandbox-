"""Host-to-HTTPS composition tests: identity before any provider GET."""
import json
import unittest

from nexus_sandbox.gate_bound_adapter import GATE_IDS
from nexus_sandbox.gate_bound_runtime import inspect_with_cortex_oauth


class Response:
    status = 200
    headers = {"Content-Type": "application/json"}
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def read(self, maximum):
        return json.dumps(self.data).encode()[:maximum]


class Opener:
    def __init__(self):
        self.paths = []
    def open(self, req, timeout):
        self.paths.append(req.full_url)
        if req.full_url.endswith("/access"):
            return Response({"permissions": ["module.view"], "is_owner": False})
        return Response({
            "id": "module_demo", "name": "Nexus Sandbox CP02",
            "content": "TEST FIXTURE — SYNTHETIC — NOT CANONICAL.",
            "version": 3, "archived": False, "dependencies": [],
            "owner": "test_owner", "default_assignee": None, "parent": None,
            "inherit_permissions": False, "created_at": "2026-11-01T00:00:00Z",
            "updated_at": "2026-11-01T00:00:00Z"})


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.opener = Opener()
        self.op = {"id": "cp02:runtime", "principal": "viewer:one",
                   "provider": "CORTEX", "target": "synthetic:cp02",
                   "action": "read", "synthetic": True}
        self.register = {gate: "BLOCKED" for gate in GATE_IDS}
        self.identity = lambda: {"provider": "CORTEX", "principal": "viewer:one",
                                 "authenticated": True}
    def run_case(self, **kwargs):
        args = dict(token="test-token", authenticated_identity_exact=self.identity,
                    module_name="Nexus Sandbox CP02", module_id="module_demo",
                    operation=self.op, checkpoint_statuses=self.register,
                    applicable_gates=("CP02",), other_boundary_evidence={},
                    opener=self.opener)
        args.update(kwargs)
        return inspect_with_cortex_oauth(**args)

    def test_end_to_end_read_only_provider_path(self):
        r = self.run_case()
        self.assertEqual(r.status, "READBACK_MATCHED_HOST_ASSERTION")
        self.assertEqual(r.resource_revision, "3")
        self.assertFalse(r.execution_authorized)
        self.assertEqual(r.provider_writes, 0)
        self.assertEqual(len(self.opener.paths), 2)
        self.assertTrue(self.opener.paths[0].endswith("/access"))

    def test_absent_identity_holds_before_http(self):
        def absent():
            raise ValueError("No provider identity")
        self.assertEqual(self.run_case(authenticated_identity_exact=absent).status, "HELD")
        self.assertEqual(self.opener.paths, [])

    def test_owner_identity_cannot_stand_in_for_viewer(self):
        wrong = lambda: {"provider": "CORTEX", "principal": "owner",
                         "authenticated": True}
        self.assertEqual(self.run_case(authenticated_identity_exact=wrong).status, "HELD")
        self.assertEqual(self.opener.paths, [])

    def test_write_operation_never_invokes_transport(self):
        self.assertEqual(self.run_case(operation={**self.op, "action": "update"}).status,
                         "HELD")
        self.assertEqual(self.opener.paths, [])

    def test_wrong_module_id_holds_after_read(self):
        self.assertEqual(self.run_case(module_id="module_other").status, "HELD")
        self.assertEqual(len(self.opener.paths), 2)

    def test_missing_other_gate_stops_module_read(self):
        x = self.run_case(applicable_gates=("CP02", "CP04"))
        self.assertEqual(x.status, "HELD")
        self.assertEqual(x.outstanding, ("CP04",))
        self.assertEqual(len(self.opener.paths), 1)


if __name__ == "__main__":
    unittest.main()
