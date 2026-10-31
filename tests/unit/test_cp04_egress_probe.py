"""Pure synthetic checks for CP04 observation logic; no outbound network."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "tools" / "cp04_egress_probe.py"
spec = importlib.util.spec_from_file_location("cp04_egress_probe", SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Cp04ProbeTests(unittest.TestCase):
    def test_never_claims_policy_enforcement(self):
        for allow in (True, False):
            for deny in (True, False):
                for direct in (True, False):
                    with self.subTest(allow=allow, deny=deny, direct=direct):
                        result = probe.evaluate(
                            {"reachable": allow},
                            {"reachable": deny},
                            {"reachable": direct},
                        )
                        self.assertFalse(result["network_enforcement_proven"])
                        self.assertFalse(result["policy_log_verified"])
                        self.assertEqual(
                            result["verdict"],
                            "OBSERVATION_ONLY_REQUIRES_INDEPENDENT_POLICY_EVIDENCE",
                        )

    def test_endpoint_selection_is_fixed_public_non_provider(self):
        self.assertEqual(probe.APPROVED, "https://example.com/")
        self.assertEqual(probe.DENIED, "https://example.org/")

    def test_redirects_are_rejected(self):
        handler = probe._NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "", {}, "https://example.net/"))


if __name__ == "__main__":
    unittest.main()
