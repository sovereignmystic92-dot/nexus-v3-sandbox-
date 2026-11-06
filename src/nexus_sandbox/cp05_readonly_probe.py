"""CP05 read-only host probe boundary; transport injection only, no network/secrets.

A PASS is a *read-only match*, never proof of write authority or delivery.
The caller must supply a separately reviewed authenticated host transport.
"""
from dataclasses import dataclass
from typing import Protocol
from nexus_sandbox.cp05_notion_identity import notion_page_matches

SOURCE_ID = "40b8c067daa481a3bc7ee289c8f7f050"
VIDEO_ID = "kokDVXUGdes"
MODULE_ID = "module_01m6b6fdsz1s0ma4rqhvbdpe10"
SOURCE_URL = "https://app.notion.com/p/" + SOURCE_ID
VIDEO_URL = "https://youtu.be/" + VIDEO_ID


class ReadOnlyTransport(Protocol):
    def read_notion_page(self, page_id: str) -> dict: ...
    def read_cortex_module(self, module_id: str) -> dict: ...


@dataclass(frozen=True)
class ProbeReceipt:
    status: str
    principal_ref: str
    reads: int
    writes: int = 0
    completion_verified: bool = False


def probe(transport: ReadOnlyTransport, *, principal_ref: str,
          host_auth_verified: bool, independent_receipt_readback: bool) -> ProbeReceipt:
    """No writes, discovery, retries, or implicit credential fallback.

    A passed-in bool is only an assertion from the caller, not proof that
    authentication or independent readback occurred. Production use requires
    a separately verified trusted host wrapper.
    """
    reads = 0
    def receipt(status):
        return ProbeReceipt(status, principal_ref if type(principal_ref) is str else "", reads)
    if (type(principal_ref) is not str or not principal_ref.strip()
            or type(host_auth_verified) is not bool or not host_auth_verified):
        return receipt("BLOCKED_HOST_AUTH")
    if type(independent_receipt_readback) is not bool or not independent_receipt_readback:
        return receipt("BLOCKED_RECEIPT_READBACK")
    try:
        source = transport.read_notion_page(SOURCE_ID)
        reads += 1
    except Exception:
        return receipt("BLOCKED_NOTION_UNAVAILABLE")
    if type(source) is not dict or source.get("id") != SOURCE_ID or source.get("video_id") != VIDEO_ID:
        return receipt("BLOCKED_SOURCE_IDENTITY")
    if not notion_page_matches(source.get("url"), SOURCE_ID):
        return receipt("BLOCKED_NOTION_URL_IDENTITY")
    if source.get("verbatim") is not False:
        return receipt("BLOCKED_FIDELITY_UNVERIFIED")
    try:
        module = transport.read_cortex_module(MODULE_ID)
        reads += 1
    except Exception:
        return receipt("BLOCKED_CORTEX_UNAVAILABLE")
    if type(module) is not dict or module.get("id") != MODULE_ID or module.get("version") != 1:
        return receipt("BLOCKED_MODULE_REVISION")
    if type(module.get("content")) is not str or SOURCE_URL not in module["content"] or VIDEO_URL not in module["content"]:
        return receipt("BLOCKED_PROVENANCE")
    # An exact-ID read cannot prove basin-wide uniqueness; do not claim it.
    return receipt("MATCHED_EXACT_IDS_UNIQUENESS_UNVERIFIED")
