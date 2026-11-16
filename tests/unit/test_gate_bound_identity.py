"""Offline token -> Directory identity -> Cortex read composition."""
import json
import unittest
from nexus_sandbox.gate_bound_identity import (
    obtain_installed_principal_token, inspect_with_installed_principal)
from nexus_sandbox.gate_bound_adapter import GATE_IDS


class Response:
    status = 200
    headers = {"Content-Type": "application/json"}
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return json.dumps(self.payload).encode()[:limit]


class IdentityOpener:
    def __init__(self):
        self.calls = []
        self.directory = {"id": "user_abc", "type": "app", "role": "member"}
    def open(self, req, timeout):
        self.calls.append(req)
        if req.full_url.endswith("/oauth/token"):
            return Response({"access_token": "short-token", "token_type": "Bearer",
                             "expires_in": 600, "scope": ""})
        if req.full_url.endswith("/users/me"):
            return Response(self.directory)
        raise ValueError("Unexpected URL")


class CortexOpener:
    def __init__(self):
        self.calls = []
    def open(self, req, timeout):
        self.calls.append(req)
        if req.full_url.endswith("/access"):
            return Response({"permissions": ["module.view"], "is_owner": False})
        return Response({
            "id": "module_fixture", "name": "Nexus Sandbox CP02",
            "content": "TEST FIXTURE — SYNTHETIC — NOT CANONICAL.",
            "version": 1, "archived": False, "dependencies": [],
            "owner": "user_owner", "default_assignee": None, "parent": None,
            "inherit_permissions": False, "created_at": "2026-11-01T00:00:00Z",
            "updated_at": "2026-11-01T00:00:00Z"})


class AppIdentityTests(unittest.TestCase):
    def setUp(self):
        self.identity = IdentityOpener()
        self.cortex = CortexOpener()
        self.args = dict(client_id="client_app", client_secret="private-secret",
                         principal_id="raw-uuid", expected_directory_id="user_abc",
                         opener=self.identity)

    def test_token_and_directory_verified_on_one_token(self):
        token, proof = obtain_installed_principal_token(**self.args)
        self.assertEqual(token, "short-token")
        self.assertEqual(proof["principal"], "user_abc")
        self.assertEqual(len(self.identity.calls), 2)
        self.assertEqual(self.identity.calls[0].get_method(), "POST")
        self.assertEqual(self.identity.calls[1].get_method(), "POST")
        self.assertEqual(self.identity.calls[1].get_header("Authorization"),
                         "Bearer short-token")

    def test_identity_mismatch_fails(self):
        self.identity.directory["id"] = "user_other"
        with self.assertRaises(ValueError):
            obtain_installed_principal_token(**self.args)

    def test_owner_identity_fails(self):
        self.identity.directory["type"] = "human"
        with self.assertRaises(ValueError):
            obtain_installed_principal_token(**self.args)

    def test_admin_role_fails(self):
        self.identity.directory["role"] = "owner"
        with self.assertRaises(ValueError):
            obtain_installed_principal_token(**self.args)

    def test_missing_config_fails_before_network(self):
        with self.assertRaises(ValueError):
            obtain_installed_principal_token(**{**self.args, "client_secret": ""})
        self.assertEqual(self.identity.calls, [])

    def test_composed_read_attested_by_directory(self):
        result = inspect_with_installed_principal(
            client_id="client_app", client_secret="private-secret",
            principal_id="raw-uuid", expected_directory_id="user_abc",
            module_name="Nexus Sandbox CP02", module_id="module_fixture",
            checkpoint_statuses={g: "BLOCKED" for g in GATE_IDS},
            applicable_gates=("CP02",), other_boundary_evidence={},
            identity_opener=self.identity, cortex_opener=self.cortex)
        self.assertEqual(result.status, "READBACK_MATCHED_HOST_ASSERTION")
        self.assertEqual(result.provider_writes, 0)
        self.assertFalse(result.execution_authorized)
        self.assertEqual(len(self.cortex.calls), 2)
        self.assertTrue(all(req.get_header("Authorization") == "Bearer short-token"
                            for req in self.cortex.calls))

    def test_directory_denial_prevents_cortex_call(self):
        self.identity.directory["id"] = "user_wrong"
        with self.assertRaises(ValueError):
            inspect_with_installed_principal(
                client_id="client_app", client_secret="private-secret",
                principal_id="raw-uuid", expected_directory_id="user_abc",
                module_name="Nexus Sandbox CP02", module_id="module_fixture",
                checkpoint_statuses={g: "BLOCKED" for g in GATE_IDS},
                applicable_gates=("CP02",), other_boundary_evidence={},
                identity_opener=self.identity, cortex_opener=self.cortex)
        self.assertEqual(self.cortex.calls, [])


if __name__ == "__main__":
    unittest.main()
