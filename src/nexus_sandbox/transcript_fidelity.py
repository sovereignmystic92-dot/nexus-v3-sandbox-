"""Exact UTF-8 transcript transfer receipts; offline, no external writes."""
import hashlib
import json


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def split_transcript(raw, chunk_bytes=12000):
    """Split on UTF-8 character boundaries without altering any character."""
    if not isinstance(raw, str) or not raw:
        raise ValueError("nonempty transcript required")
    if not isinstance(chunk_bytes, int) or not 256 <= chunk_bytes <= 20000:
        raise ValueError("invalid chunk size")
    chunks, part, size = [], [], 0
    for char in raw:
        encoded = char.encode("utf-8")
        if size + len(encoded) > chunk_bytes:
            chunks.append("".join(part))
            part, size = [], 0
        part.append(char)
        size += len(encoded)
    if part:
        chunks.append("".join(part))
    return chunks


def build_receipt(raw, chunk_bytes=12000):
    chunks = split_transcript(raw, chunk_bytes)
    return {"schema": "nexus.transcript-fidelity.v1",
            "encoding": "utf-8", "normalization": "none",
            "chunk_bytes": chunk_bytes,
            "byte_count": len(raw.encode("utf-8")),
            "sha256": sha256_bytes(raw.encode("utf-8")),
            "chunks": [{"index": i, "byte_count": len(s.encode("utf-8")),
                        "sha256": sha256_bytes(s.encode("utf-8"))}
                       for i, s in enumerate(chunks)]}


def verify_readback(original, readback_chunks, receipt):
    """Fail closed unless independently retrieved text matches exact bytes."""
    if not isinstance(readback_chunks, list) or not all(isinstance(s, str) for s in readback_chunks):
        return False
    if not isinstance(receipt, dict) or receipt.get("schema") != "nexus.transcript-fidelity.v1":
        return False
    try:
        chunk_bytes = receipt.get("chunk_bytes")
        if type(chunk_bytes) is not int or not 256 <= chunk_bytes <= 20000:
            return False
        expected = build_receipt(original, chunk_bytes)
        actual = build_receipt("".join(readback_chunks), chunk_bytes)
        if expected != receipt or actual["sha256"] != expected["sha256"]:
            return False
        return [sha256_bytes(s.encode("utf-8")) for s in readback_chunks] == [
            item["sha256"] for item in receipt["chunks"]]
    except (ValueError, TypeError):
        return False


def receipt_json(raw):
    return json.dumps(build_receipt(raw), sort_keys=True, ensure_ascii=False)
