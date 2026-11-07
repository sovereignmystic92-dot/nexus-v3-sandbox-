import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("nexus_process", ROOT / "tools/nexus_process.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GatewayCliTests(unittest.TestCase):
    def job(self, mode):
        return dict(mode=mode, source_url="https://youtu.be/_p6lrFsVPzQ",
                    transcript="Full source.", notion_page_id="notion-1",
                    cortex_module_name="module-1", analysis="Analysis.",
                    grants=dict(process=True, notion_write=False, cortex_write=False))

    def test_all_modes_preflight_only(self):
        for mode in ("manual", "gemini", "scheduled"):
            with self.subTest(mode=mode):
                result = module.preflight(self.job(mode))
                self.assertEqual(result["status"], "PREFLIGHT_ONLY")
                self.assertFalse(result["readback_verified"])
                self.assertEqual(result["provider_writes"], 0)

    def test_denied_processing(self):
        job = self.job("manual")
        job["grants"]["process"] = False
        with self.assertRaises(ValueError):
            module.preflight(job)

    def test_noncanonical_url_rejected(self):
        job = self.job("gemini")
        job["source_url"] = "https://youtu.be/_p6lrFsVPzQ?extra=1"
        with self.assertRaises(ValueError):
            module.preflight(job)

    def test_extra_manifest_fields_rejected(self):
        job = self.job("scheduled")
        job["force_verified"] = True
        with self.assertRaises(ValueError):
            module.preflight(job)


if __name__ == "__main__":
    unittest.main()
