"""Reproducible offline Skill Forge tests: python -m unittest discover -s tests/unit -p 'test_skill_forge_wolfram.py' -v"""
import tempfile
import unittest
from pathlib import Path

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
            lambda expression: "Out[1]= (-1 + x)*(1 + x)*(1 + x^2)",
            approved=True)
        self.assertTrue(result["validated"])
        self.assertEqual(len(result["skills"]), 2)

    def test_modification_normalizes_output(self):
        self.assertEqual(normalize_wolfram_output(" Out[17]=   (x - 1) * (x + 1) "), "(x - 1) * (x + 1)")

    def test_no_implicit_execution(self):
        with self.assertRaises(PermissionError):
            execute_composed(self.db, FactorRequest("Factor[x^4 - 1]"), lambda _: "anything")

    def test_reject_unsafe_code(self):
        with self.assertRaises(ValueError):
            FactorRequest("Run[\"curl example.com\"]").wolfram_code()

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
