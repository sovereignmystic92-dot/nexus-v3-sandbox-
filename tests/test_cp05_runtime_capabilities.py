from nexus_sandbox.cp05_runtime_capabilities import check_runtime_capabilities


CAPS = {
    "notion_authenticated_full_page_read": True,
    "notion_complete_pagination": True,
    "cortex_authenticated_module_read": True,
    "cortex_complete_output_read": True,
    "independent_provider_readback": True,
}
ENV = {"NEXUS_NOTION_TOKEN": "dummy-not-a-real-secret",
       "NEXUS_CORTEX_TOKEN": "dummy-not-a-real-secret"}


def test_default_fails_closed_without_manifest():
    result = check_runtime_capabilities(environ={})
    assert result.status == "BLOCKED"
    assert result.missing == ("capability_manifest",)


def test_missing_credentials_reports_names_only():
    result = check_runtime_capabilities(environ={}, capabilities=CAPS)
    assert result.status == "BLOCKED"
    assert result.missing == ("NEXUS_NOTION_TOKEN", "NEXUS_CORTEX_TOKEN")
    assert "dummy" not in str(result)


def test_each_missing_capability_blocks():
    for key in CAPS:
        flags = dict(CAPS, **{key: False})
        result = check_runtime_capabilities(environ=ENV, capabilities=flags)
        assert result.status == "BLOCKED"
        assert key in result.missing


def test_truthy_nonboolean_capability_blocks():
    result = check_runtime_capabilities(
        environ=ENV, capabilities=dict(CAPS, notion_complete_pagination="true"))
    assert result.status == "BLOCKED"


def test_complete_declarations_only_allow_probe():
    result = check_runtime_capabilities(environ=ENV, capabilities=CAPS)
    assert result.status == "READY_FOR_AUTHENTICATED_READ_PROBE"
    assert result.next_action == "VERIFY_EFFECTIVE_GRANTS_AND_PROVIDER_READBACK"
