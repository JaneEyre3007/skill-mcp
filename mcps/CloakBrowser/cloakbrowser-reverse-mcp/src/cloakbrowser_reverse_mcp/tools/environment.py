from __future__ import annotations

import importlib

from ..binary_manager import binary_info as _binary_info
from ..browser import _default_binary_path
from ..server import browser_manager, mcp


@mcp.tool()
async def check_environment() -> dict:
    """Check MCP dependencies and local CloakBrowser state."""
    deps = {}
    for dep in ("mcp", "playwright", "esprima"):
        try:
            mod = importlib.import_module(dep)
            deps[dep] = {"installed": True, "version": getattr(mod, "__version__", "unknown"), "ok": True}
        except Exception as exc:
            deps[dep] = {"installed": False, "ok": False, "error": str(exc)}
    binary = _default_binary_path()
    info = _binary_info()
    browser = {"running": browser_manager.browser is not None, "cdp_url": browser_manager.cdp_endpoint(), "captured_requests_count": len(browser_manager._network_requests), "persistent_scripts_count": len(browser_manager._persistent_scripts)}
    return {"mcp": {"name": "cloakbrowser-reverse-mcp"}, "deps": deps, "binary": {**info, "path": str(binary), "exists": binary.exists()}, "browser": browser, "overall_ok": binary.exists() and all(d["ok"] for d in deps.values()), "trace": {"engine_trace": False, "reason": "CloakBrowser has no Camoufox-style trace control files"}}
