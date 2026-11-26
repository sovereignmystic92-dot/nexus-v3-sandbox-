"""Offline consistency checks for supervised receipts; not provider attestation."""
import math
import re

def validate(receipt):
    errors = []
    def require(ok, label):
        if not ok:
            errors.append(label)
    require(receipt.get("route") == "supervised_connector", "route")
    source = receipt.get("source", {})
    digest = source.get("sha256", "")
    require(isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", digest)), "digest")
    require(bool(source.get("page_id") and source.get("revision")), "source identity")
    require(source.get("readback_sha256") == digest, "archive readback")
    chunks = source.get("chunks", [])
    require(bool(chunks) and all(c.get("sha256") == c.get("readback_sha256") and bool(re.fullmatch(r"[0-9a-f]{64}", c.get("sha256", ""))) for c in chunks), "chunk digests")
    require([c.get("index") for c in chunks] == list(range(len(chunks))), "chunk order")
    require(all(type(c.get("bytes")) is int and c["bytes"] > 0 for c in chunks) and sum(c.get("bytes", 0) for c in chunks) == source.get("bytes"), "byte count")
    claims = receipt.get("claims", [])
    require(bool(claims), "claims")
    for c in claims:
        p, n, result = c.get("p"), c.get("trials"), c.get("percent")
        valid = type(p) in (int, float) and 0 < p < 1 and type(n) is int and n > 0 and type(result) in (int, float)
        require(valid and math.isclose(result, -100 * math.expm1(n * math.log1p(-p)), abs_tol=1e-8), "calculation")
    output = receipt.get("output", {})
    require(bool(output.get("module_id")) and output.get("module_id") == output.get("readback_module_id"), "output identity")
    require(output.get("source_sha256") == digest and output.get("readback_source_sha256") == digest, "output source binding")
    require(bool(output.get("dependencies")) and output.get("dependencies") == output.get("readback_dependencies"), "dependencies")
    return {"status": "RECEIPT_CONSISTENT" if not errors else "FUNCTIONALLY_INCOMPLETE", "errors": errors, "provider_attestation": False, "automation_ready": False, "audit_promotion": False}
