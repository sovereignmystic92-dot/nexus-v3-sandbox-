import copy
import json
import unittest
from nexus_sandbox.supervised_receipt import validate

RECEIPT = json.loads("{\"route\":\"supervised_connector\",\"source\":{\"page_id\":\"4228c067-daa4-81e1-ba44-c22bd5d11d47\",\"revision\":\"2026-11-24T08:19:08.017Z\",\"sha256\":\"cf0a40c6ef9ee4ffbf5428ef352c1fe09d719337784b7d931c708150bf194657\",\"readback_sha256\":\"cf0a40c6ef9ee4ffbf5428ef352c1fe09d719337784b7d931c708150bf194657\",\"bytes\":28824,\"chunks\":[{\"index\":0,\"bytes\":10728,\"sha256\":\"ab5693cf77cb6a673ee03a375f1203c715964e283caefe3a5dcb3a2cc67e4bbb\",\"readback_sha256\":\"ab5693cf77cb6a673ee03a375f1203c715964e283caefe3a5dcb3a2cc67e4bbb\"},{\"index\":1,\"bytes\":9940,\"sha256\":\"3c98aadcae88ee0b1360e1f6e57ee93749cb5b840f270e1fd423e7ef48f52b00\",\"readback_sha256\":\"3c98aadcae88ee0b1360e1f6e57ee93749cb5b840f270e1fd423e7ef48f52b00\"},{\"index\":2,\"bytes\":8156,\"sha256\":\"795df375ec01c7ac67f338e21ee6f1f644d3560a7cd2ae78564217ff49896d42\",\"readback_sha256\":\"795df375ec01c7ac67f338e21ee6f1f644d3560a7cd2ae78564217ff49896d42\"}]},\"claims\":[{\"p\":0.01,\"trials\":150,\"percent\":77.85482127611391},{\"p\":0.0001,\"trials\":15000,\"percent\":77.68865751016574}],\"output\":{\"module_id\":\"module_01m8an8hdqq3rp8ydajgekzmey\",\"readback_module_id\":\"module_01m8an8hdqq3rp8ydajgekzmey\",\"source_sha256\":\"cf0a40c6ef9ee4ffbf5428ef352c1fe09d719337784b7d931c708150bf194657\",\"readback_source_sha256\":\"cf0a40c6ef9ee4ffbf5428ef352c1fe09d719337784b7d931c708150bf194657\",\"dependencies\":[\"Nexus Research — Why Generation Ships Can't Work — Cumulative Risk\",\"Nexus Research — Generation Ships — Multiple-Hazard Probability\"],\"readback_dependencies\":[\"Nexus Research — Why Generation Ships Can't Work — Cumulative Risk\",\"Nexus Research — Generation Ships — Multiple-Hazard Probability\"]}}")

class SupervisedReceiptTests(unittest.TestCase):
    def test_actual_receipt(self):
        result = validate(RECEIPT)
        self.assertEqual(result["status"], "RECEIPT_CONSISTENT")
        for key in ("provider_attestation", "automation_ready", "audit_promotion"):
            self.assertFalse(result[key])

    def test_corrupted_evidence(self):
        for section, key, value in [
            ("source", "readback_sha256", "0"*64),
            ("source", "bytes", 1),
            ("output", "readback_module_id", "wrong"),
            ("output", "readback_dependencies", []),
            ("output", "readback_source_sha256", "wrong"),
        ]:
            with self.subTest(key=key):
                r = copy.deepcopy(RECEIPT)
                r[section][key] = value
                self.assertEqual(validate(r)["status"], "FUNCTIONALLY_INCOMPLETE")

    def test_wrong_math(self):
        r = copy.deepcopy(RECEIPT)
        r["claims"][0]["percent"] = 99
        self.assertEqual(validate(r)["status"], "FUNCTIONALLY_INCOMPLETE")

    def test_reordered_chunks(self):
        r = copy.deepcopy(RECEIPT)
        r["source"]["chunks"].reverse()
        self.assertEqual(validate(r)["status"], "FUNCTIONALLY_INCOMPLETE")
