from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_page_info_reports_actual_window_metrics():
    from camoufox_reverse_mcp.tools.navigation import get_page_info

    mock_page = AsyncMock()
    mock_page.url = "https://example.test/"
    mock_page.viewport_size = {"width": 1280, "height": 720}
    mock_page.title = AsyncMock(return_value="Example")
    mock_page.evaluate = AsyncMock(return_value={
        "inner_width": 1600,
        "inner_height": 900,
        "outer_width": 1680,
        "outer_height": 960,
        "device_pixel_ratio": 1,
        "visual_viewport_width": 1600,
        "visual_viewport_height": 900,
        "screen_width": 1920,
        "screen_height": 1080,
        "screen_avail_width": 1920,
        "screen_avail_height": 1032,
    })

    with patch("camoufox_reverse_mcp.tools.navigation.browser_manager") as mock_bm:
        mock_bm.get_active_page = AsyncMock(return_value=mock_page)
        result = await get_page_info()

    assert result["viewport_width"] == 1280
    assert result["window_inner_width"] == 1600
    assert result["screen_avail_height"] == 1032


@pytest.mark.asyncio
async def test_nonpersistent_hook_injects_current_page_only():
    from camoufox_reverse_mcp.tools.hooking import inject_hook_preset

    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=None)

    with patch("camoufox_reverse_mcp.tools.hooking.browser_manager") as mock_bm:
        mock_bm.get_active_page = AsyncMock(return_value=mock_page)
        result = await inject_hook_preset("fetch", persistent=False)

    assert result["status"] == "injected"
    assert result["persistent"] is False
    mock_page.evaluate.assert_awaited_once()
    assert not hasattr(mock_page, "add_init_script") or not mock_page.add_init_script.called


@pytest.mark.asyncio
async def test_remove_hooks_reports_generic_uninstallers():
    from camoufox_reverse_mcp.tools.hooking import remove_hooks

    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value={
        "uninstalled": [{"hook": "fetch", "restored": ["window.fetch"]}],
        "errors": [],
    })

    with patch("camoufox_reverse_mcp.tools.hooking.browser_manager") as mock_bm:
        mock_bm.get_active_page = AsyncMock(return_value=mock_page)
        mock_bm._init_scripts = []
        mock_bm._persistent_scripts = []
        result = await remove_hooks()

    assert result["status"] == "hooks_removed"
    assert "fetch:window.fetch" in result["restored_objects"]
    sent_js = mock_page.evaluate.await_args.args[0]
    assert "__mcp_hook_uninstallers" in sent_js


@pytest.mark.asyncio
async def test_cookie_delete_uses_and_for_name_and_domain():
    from camoufox_reverse_mcp.tools.storage import cookies

    class DummyContext:
        def __init__(self):
            self.original = [
                {"name": "sid", "domain": ".a.test", "value": "1", "path": "/"},
                {"name": "sid", "domain": ".b.test", "value": "2", "path": "/"},
                {"name": "other", "domain": ".a.test", "value": "3", "path": "/"},
            ]
            self.kept = None

        async def cookies(self):
            return list(self.original)

        async def clear_cookies(self):
            pass

        async def add_cookies(self, cookies_list):
            self.kept = cookies_list

    ctx = DummyContext()
    page = type("DummyPage", (), {"context": ctx})()

    with patch("camoufox_reverse_mcp.tools.storage.browser_manager") as mock_bm:
        mock_bm.get_active_page = AsyncMock(return_value=page)
        result = await cookies("delete", domain=".a.test", name="sid")

    assert result == {"status": "deleted", "count": 1}
    assert ctx.kept == [
        {"name": "sid", "domain": ".b.test", "value": "2", "path": "/"},
        {"name": "other", "domain": ".a.test", "value": "3", "path": "/"},
    ]


@pytest.mark.asyncio
async def test_save_script_supports_inline_sources(tmp_path):
    from camoufox_reverse_mcp.tools import script_analysis

    save_path = tmp_path / "inline.js"
    with patch.object(script_analysis, "_get_script_source", AsyncMock(return_value="console.log(1);")):
        result = await script_analysis._save_script("inline:0", str(save_path))

    assert result["status"] == "saved"
    assert save_path.read_text(encoding="utf-8") == "console.log(1);"


@pytest.mark.asyncio
async def test_external_script_url_is_passed_as_evaluate_arg():
    from camoufox_reverse_mcp.tools.script_analysis import _get_script_source

    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value="source")
    url = 'https://example.test/a"b.js'

    with patch("camoufox_reverse_mcp.tools.script_analysis.browser_manager") as mock_bm:
        mock_bm.get_active_page = AsyncMock(return_value=mock_page)
        source = await _get_script_source(url)

    assert source == "source"
    sent_js = mock_page.evaluate.await_args.args[0]
    sent_arg = mock_page.evaluate.await_args.args[1]
    assert "fetch(url)" in sent_js
    assert sent_arg == url


@pytest.mark.asyncio
async def test_check_environment_fails_when_dependency_missing():
    from camoufox_reverse_mcp.tools import environment

    real_import = environment.importlib.import_module

    def fake_import(name):
        if name == "esprima":
            raise ImportError("missing esprima")
        return real_import(name)

    with patch.object(environment.importlib, "import_module", side_effect=fake_import):
        result = await environment.check_environment()

    assert result["deps"]["esprima"]["ok"] is False
    assert result["overall_ok"] is False


def test_maximize_browser_window_reports_unsupported_off_windows():
    from camoufox_reverse_mcp import browser

    with patch.object(browser.platform, "system", return_value="Linux"):
        result = browser.maximize_browser_window()

    assert result["supported"] is False


def test_cleanup_traces_ignores_unlink_oserror(tmp_path):
    from camoufox_reverse_mcp import property_trace

    trace_file = tmp_path / "1_1.jsonl"
    trace_file.write_text("{}\n", encoding="utf-8")

    with patch.object(property_trace, "TRACES_DIR", tmp_path), \
         patch.object(type(trace_file), "unlink", side_effect=OSError("locked")):
        property_trace.cleanup_traces()


@pytest.mark.asyncio
async def test_import_state_handles_missing_browser_after_ensure():
    from camoufox_reverse_mcp.tools.storage import import_state

    with patch("camoufox_reverse_mcp.tools.storage.browser_manager") as mock_bm:
        mock_bm._ensure_browser = AsyncMock(return_value=None)
        mock_bm.browser = None
        result = await import_state("state.json")

    assert result == {"error": "No browser available after launch"}
