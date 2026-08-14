from __future__ import annotations

from ..binary_manager import binary_info as _binary_info, check_for_update, download_or_update
from ..server import browser_manager, mcp
from ..utils.response_fmt import error_response


@mcp.tool()
async def browser_binary_info() -> dict:
    """Show local CloakBrowser binary info and in-place update target."""
    return _binary_info()


@mcp.tool()
async def check_browser_update() -> dict:
    """Check GitHub releases for a newer CloakBrowser Chromium binary."""
    try:
        return check_for_update()
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def update_browser_binary(version: str | None = None, force: bool = False, close_running_browser: bool = False) -> dict:
    """Download/update CloakBrowser in-place next to the active chrome.exe.

    No global C: cache is used. If a browser is running, set close_running_browser=True.
    """
    try:
        if browser_manager.browser is not None:
            if not close_running_browser:
                return error_response("browser is running; close it or set close_running_browser=True before updating chrome.exe")
            await browser_manager.close()
        return download_or_update(version=version, force=force)
    except Exception as exc:
        return error_response(exc)
