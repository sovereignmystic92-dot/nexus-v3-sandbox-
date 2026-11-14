"""Reproducible offline Skill Forge tests: python -m unittest discover -s tests/unit -p 'test_skill_forge_wolfram.py' -v"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace

from nexus_sandbox.skill_forge_wolfram import (
    SkillLibrary, FactorRequest, SKILL_ID, VALIDATOR_ID, manifest, execute_composed,
    normalize_wolfram_output,
)


class SkillForgeWolframTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "skills.sqlite"
        self.db = SkillLibrary(self.path)
        self.a = manifest(SKILL_ID, upstream="WolframLanguageEvaluator", capability="Factor polynomial")
        self.b = manifest(VALIDATOR_ID, upstream="Nexus local validator", capability="Validate result",
                          dependencies=[SKILL_ID])
        self.db.register(self.a)
        self.db.register(self.b)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_restart_retrieval_and_composition(self):
        exported = self.db.export()
        self.db.close()
        self.db = SkillLibrary(self.path)
        self.assertEqual(self.db.export(), exported)
        self.assertEqual(self.db.get(VALIDATOR_ID)["dependencies"], [SKILL_ID])
        result = execute_composed(
            self.db, FactorRequest("Factor[x^4 - 1]"),
            approved=True)
        self.assertTrue(result["validated"])
        self.assertEqual(len(result["skills"]), 2)

    def test_fresh_process_retrieves_catalog_and_composes_second_fixture(self):
        exported = self.db.export()
        script = """
import json
import sys
from nexus_sandbox.skill_forge_wolfram import (
    FactorRequest, SkillLibrary, execute_composed,
)

library = SkillLibrary(sys.argv[1])
try:
    result = execute_composed(
        library, FactorRequest("Factor[x^2 - 1]"), approved=True,
    )
    print(json.dumps({"catalog": library.export(), "result": result}))
finally:
    library.close()
"""
        self.db.close()
        try:
            process = subprocess.run(
                [sys.executable, "-c", script, str(self.path)],
                check=True, capture_output=True, text=True, timeout=10,
            )
        finally:
            self.db = SkillLibrary(self.path)
        evidence = json.loads(process.stdout)
        self.assertEqual(evidence["catalog"], exported)
        self.assertEqual(evidence["result"]["result"], "(x - 1)*(x + 1)")
        self.assertEqual(evidence["result"]["skills"], [SKILL_ID, VALIDATOR_ID])
        self.assertTrue(evidence["result"]["validated"])

    def test_reject_valid_factors_for_a_different_request(self):
        with self.assertRaises(ValueError):
            execute_composed(
                self.db, FactorRequest("Factor[x^2 - 1]"),
                lambda _: "(x-1)*(x+1)*(x^2+1)", approved=True,
            )

    def test_modification_normalizes_output(self):
        self.assertEqual(normalize_wolfram_output(" Out[17]=   (x - 1) * (x + 1) "), "(x - 1) * (x + 1)")

    def test_no_implicit_execution(self):
        with self.assertRaises(PermissionError):
            execute_composed(self.db, FactorRequest("Factor[x^4 - 1]"), lambda _: "anything")

    def test_reject_unsafe_code(self):
        with self.assertRaises(ValueError):
            FactorRequest("Run[\"curl example.com\"]").wolfram_code()

    def test_unsupported_input_never_reaches_transport(self):
        transport = Mock()
        with self.assertRaises(ValueError):
            execute_composed(
                self.db, FactorRequest("Factor[x^3 - 1]"), transport, approved=True,
            )
        transport.assert_not_called()

    def test_incompatible_skill_version_never_reaches_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            library = SkillLibrary(Path(directory) / "skills.sqlite")
            try:
                library.register(self.a)
                library.register(dict(self.b, version="2.0.0"))
                transport = Mock()
                with self.assertRaisesRegex(ValueError, "incompatible skill version"):
                    execute_composed(
                        library, FactorRequest("Factor[x^2 - 1]"), transport, approved=True,
                    )
                transport.assert_not_called()
            finally:
                library.close()

    def test_invalid_approval_and_request_never_reach_transport(self):
        transport = Mock()
        with self.assertRaises(PermissionError):
            execute_composed(self.db, FactorRequest("Factor[x^2 - 1]"), transport, approved="false")
        with self.assertRaises(ValueError):
            execute_composed(self.db, SimpleNamespace(wolfram_code=lambda: "invalid"), transport, approved=True)
        transport.assert_not_called()

    def test_catalog_rejects_incomplete_manifest(self):
        for field in ("version", "contract", "input_schema", "output_schema",
                      "fixtures", "evidence_refs", "adapter_path", "dependency_versions"):
            with self.subTest(field=field):
                data = dict(self.a)
                del data[field]
                with self.assertRaises(ValueError):
                    self.db.register(data)

    def test_catalog_retains_unavailable_skill(self):
        data = dict(self.a, id="wolfram.factor-provider", readiness="unavailable")
        self.db.register(data)
        self.assertEqual(self.db.get(data["id"]), data)

    def test_validator_accepts_reordered_factors(self):
        result = execute_composed(
            self.db, FactorRequest("Factor[x^4 - 1]"),
            lambda _: "Out[1]= (1+x^2)*(x+1)*(-1+x)", approved=True,
        )
        self.assertTrue(result["validated"])

    def test_reject_conflicting_identity(self):
        changed = dict(self.a, capability="silently replaced")
        with self.assertRaises(ValueError):
            self.db.register(changed)

    def test_reject_missing_dependency(self):
        self.db.close()
        self.path.unlink()
        self.db = SkillLibrary(self.path)
        self.db.register(self.a)
        with self.assertRaises(KeyError):
            execute_composed(self.db, FactorRequest("Factor[x^4 - 1]"), lambda _: "", approved=True)

    def test_reject_bad_provider_result(self):
        with self.assertRaises(ValueError):
            execute_composed(self.db, FactorRequest("Factor[x^4 - 1]"), lambda _: "Out[1]= <script>", approved=True)

    def test_reject_wrong_math(self):
        with self.assertRaises(ValueError):
            execute_composed(self.db, FactorRequest("Factor[x^4 - 1]"), lambda _: "(x+1)", approved=True)

    def test_reject_live_permissions(self):
        with self.assertRaises(PermissionError):
            self.db.register(dict(self.a, id="another", provider_permissions=["write"]))


if __name__ == "__main__":
    unittest.main()
