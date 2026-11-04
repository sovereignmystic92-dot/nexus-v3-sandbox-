"""Cortex read-only client contract tests; no real provider credentials."""
import pytest
from nexus_sandbox.cp05_cortex_reader import read_cortex_fixture

ID = "module_01m6kzebbfdk4ptbsg88gsf0ja"
RECORD = {"module_id": ID, "version": 1, "payload": "fixture"}
META = {"authenticated": True, "complete_inventory": True}


class Client:
    def __init__(self, record=RECORD, metadata=META):
        self.record, self.metadata = record, metadata
        self.calls = []
    def read_module(self, module_id):
        self.calls.append(module_id)
        return self.record, self.metadata


def test_authenticated_complete_readback():
    client = Client()
    record, meta = read_cortex_fixture(ID, client=client)
    assert record == RECORD
    assert meta == META
    assert client.calls == [ID]


@pytest.mark.parametrize("record,meta", [
    (dict(RECORD, module_id="module_wrong"), META),
    (RECORD, dict(META, authenticated=False)),
    (RECORD, dict(META, complete_inventory=False)),
    (RECORD, dict(META, authenticated="true")),
])
def test_untrusted_readback_rejected(record, meta):
    with pytest.raises(ValueError):
        read_cortex_fixture(ID, client=Client(record, meta))


def test_missing_client_fails_closed():
    with pytest.raises(ValueError):
        read_cortex_fixture(ID, client=None)
