"""Verify an exported canonical Notion page before source-ready packet creation.

This is an offline verifier. The caller must fetch the page independently and
supply its complete, untruncated Markdown; it never asserts provider access.
"""
import hashlib
import re

SOURCE_ID = "4168c067-daa4-8111-bda6-ef07325583ed"
SOURCE_SHA256 = "a74abe591255afcd03af59eb34d525e997486a0118542679b77edd766380c867"
CHUNK_BYTES = (12000, 12000, 12000, 1274)
CHUNK_SHA256 = (
    "0e6b87bdbc48d428fe7b928c12bc74d9c69f2e01ed97fe34a15637763e3c28cf",
    "ff61d2ea56ce52915fbe06b22d5fa7608adc28ad4231c0e77324bf1425a7257c",
    "fd7be76991962a265d7b21c73165dc673efee4afc74df5edbcd15d49c2cbea1f",
    "8bb7727baaf087b20a9a3b34d2442c7b862d52f245be8f30b96d82dd963663ec",
)


def verify_notion_export(markdown, *, source_id, source_revision, truncated=False,
                         unknown_block_count=0):
    """Fail closed on missing or mismatched raw chunks; return evidence metadata."""
    if truncated or unknown_block_count or source_id != SOURCE_ID:
        raise ValueError("incomplete or incorrect Notion source")
    if not isinstance(source_revision, str) or not source_revision.strip():
        raise ValueError("missing source revision")
    if not isinstance(markdown, str) or "Pending Cortex Processing" not in markdown:
        raise ValueError("source not marked pending")
    matches = re.findall(
        r"(?m)^## Raw chunk ([0-9]+)\s*\n\s*```txt\n(.*?)\n```",
        markdown, re.DOTALL,
    )
    if [int(i) for i, _ in matches] != list(range(len(CHUNK_BYTES))):
        raise ValueError("missing, repeated, or out-of-order raw chunks")
    chunks = [raw.encode("utf-8") for _, raw in matches]
    for i, chunk in enumerate(chunks):
        if len(chunk) != CHUNK_BYTES[i] or hashlib.sha256(chunk).hexdigest() != CHUNK_SHA256[i]:
            raise ValueError("raw chunk integrity mismatch")
    assembled = b"".join(chunks)
    digest = hashlib.sha256(assembled).hexdigest()
    if len(assembled) != 37274 or digest != SOURCE_SHA256:
        raise ValueError("assembled source integrity mismatch")
    return {
        "notion_source_id": SOURCE_ID,
        "readback_sha256": digest,
        "pending_cortex_processing": True,
        "readback_verified": True,
        "source_revision": source_revision,
        "byte_count": len(assembled),
        "chunk_count": len(chunks),
    }
