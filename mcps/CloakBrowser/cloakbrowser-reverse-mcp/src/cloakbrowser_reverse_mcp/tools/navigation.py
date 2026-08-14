from __future__ import annotations

import base64
from typing import Literal

from ..server import browser_manager, mcp
from ..human import human_click_selector, human_scroll as human_scroll_page, human_type_text
from ..utils.response_fmt import error_response


@mcp.tool()
async def launch_browser(
    headless: bool = True,
    locale: str = "auto",
    timezone: str | None = None,
    proxy: str | None = None,
    humanize: bool = False,
    human_preset: str = "default",
    human_config: dict | None = None,
    geoip: bool = False,
    block_images: bool = False,
    block_webrtc: bool = False,
    fingerprint_seed: str | None = None,
    window_width: int = 1920,
    window_height: int = 1080,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    persistent_profile: bool = True,
    remote_debugging_port: int | None = None,
    auto_update: bool = False,
    args: list[str] | None = None,
) -> dict:
    """Launch local CloakBrowser with stealth fingerprint flags and CDP enabled."""
    try:
        return await browser_manager.launch({
            "headless": headless,
            "locale": locale,
            "timezone": timezone,
            "proxy": proxy,
            "humanize": humanize,
            "human_preset": human_preset,
            "human_config": human_config,
            "geoip": geoip,
            "block_images": block_images,
            "block_webrtc": block_webrtc,
            "fingerprint_seed": fingerprint_seed,
            "window_width": window_width,
            "window_height": window_height,
            "viewport_width": viewport_width or window_width,
            "viewport_height": viewport_height or max(1, window_height - 133),
            "persistent_profile": persistent_profile,
            "remote_debugging_port": remote_debugging_port,
            "auto_update": auto_update,
            "args": args,
        })
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def close_browser() -> dict:
    """Close CloakBrowser and release resources."""
    try:
        return await browser_manager.close()
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_page_info() -> dict:
    """Get current page URL, title, viewport, and CDP endpoint."""
    try:
        page = await browser_manager.get_active_page()
        return {
            "url": page.url,
            "title": await page.title(),
            "viewport": page.viewport_size,
            "cdp_url": browser_manager.cdp_endpoint(),
        }
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_cdp_endpoint() -> dict:
    """Return the local Chrome DevTools Protocol endpoint."""
    await browser_manager._ensure_browser()
    return {"cdp_url": browser_manager.cdp_endpoint()}


@mcp.tool()
async def navigate(
    url: str,
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "load",
    pre_inject_hooks: list[str] | None = None,
    collect_response_chain: bool = True,
    clear_network_capture: bool = True,
) -> dict:
    """Navigate to a URL with optional pre-injected hook presets."""
    try:
        if clear_network_capture:
            browser_manager._network_requests.clear()
            browser_manager._request_id_counter = 0
        if collect_response_chain:
            browser_manager.reset_nav_responses()
        if pre_inject_hooks:
            from .hooking import inject_hook_preset
            for preset in pre_inject_hooks:
                await inject_hook_preset(preset, persistent=True)
        page = await browser_manager.get_active_page()
        resp = await page.goto(url, wait_until=wait_until, timeout=30000)
        chain = list(browser_manager._nav_responses) if collect_response_chain else None
        final_status = resp.status if resp else None
        if chain:
            for item in reversed(chain):
                if item.get("resource_type") == "document" or item.get("url") == page.url:
                    final_status = item.get("status")
                    break
        return {
            "url": page.url,
            "title": await page.title(),
            "initial_status": resp.status if resp else None,
            "final_status": final_status,
            "redirect_chain": chain,
            "hooks_injected": pre_inject_hooks or [],
        }
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def reload(wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "load") -> dict:
    """Reload current page."""
    try:
        page = await browser_manager.get_active_page()
        resp = await page.reload(wait_until=wait_until)
        return {"url": page.url, "title": await page.title(), "status": resp.status if resp else None}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def take_screenshot(full_page: bool = False, selector: str | None = None) -> dict:
    """Take a screenshot and return base64 PNG."""
    try:
        page = await browser_manager.get_active_page()
        if selector:
            loc = page.locator(selector).first
            data = await loc.screenshot()
        else:
            data = await page.screenshot(full_page=full_page)
        return {"image_base64": base64.b64encode(data).decode("ascii"), "format": "png"}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def click(selector: str) -> dict:
    """Click a page element by selector."""
    try:
        page = await browser_manager.get_active_page()
        if browser_manager._humanize:
            await human_click_selector(page, browser_manager._cursor_state, selector, browser_manager._human_config)
        else:
            await page.click(selector)
        return {"status": "clicked", "selector": selector}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def type_text(selector: str, text: str, delay: int = 50) -> dict:
    """Type text into an input field."""
    try:
        page = await browser_manager.get_active_page()
        if browser_manager._humanize:
            await human_click_selector(page, browser_manager._cursor_state, selector, browser_manager._human_config)
            cdp = await browser_manager.new_cdp_session(page)
            await human_type_text(page, text, browser_manager._human_config, cdp)
        else:
            await page.type(selector, text, delay=delay)
        return {"status": "typed", "selector": selector, "length": len(text)}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def human_scroll(delta_y: int = 600) -> dict:
    """Scroll with human-like wheel bursts when humanize is enabled."""
    try:
        page = await browser_manager.get_active_page()
        if browser_manager._humanize:
            await human_scroll_page(page, browser_manager._cursor_state, delta_y, browser_manager._human_config)
        else:
            await page.mouse.wheel(0, delta_y)
        return {"status": "scrolled", "delta_y": delta_y, "humanize": browser_manager._humanize}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def wait_for(selector: str | None = None, url_pattern: str | None = None, timeout: int = 30000) -> dict:
    """Wait for an element or URL substring."""
    try:
        page = await browser_manager.get_active_page()
        if selector:
            await page.wait_for_selector(selector, timeout=timeout)
            return {"status": "found", "selector": selector}
        if url_pattern:
            await page.wait_for_url(f"**{url_pattern}**", timeout=timeout)
            return {"status": "matched", "url": page.url}
        return error_response("selector or url_pattern is required")
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_console_logs(level: str | None = None, keyword: str | None = None, clear: bool = False) -> list[dict]:
    """Get collected console logs."""
    logs = list(browser_manager._console_logs)
    if level:
        logs = [x for x in logs if x.get("level") == level]
    if keyword:
        logs = [x for x in logs if keyword in x.get("text", "")]
    if clear:
        browser_manager._console_logs.clear()
    return logs


@mcp.tool()
async def reset_browser_state(
    clear_persistent_hooks: bool = True,
    clear_network_capture: bool = True,
    clear_active_routes: bool = True,
    clear_cookies: bool = False,
    clear_storage: bool = False,
) -> dict:
    """Reset MCP-side residual state without closing the browser."""
    cleared: dict[str, int | bool] = {}
    if clear_persistent_hooks:
        cleared["persistent_hooks"] = len(browser_manager._persistent_scripts)
        browser_manager._persistent_scripts.clear()
    if clear_network_capture:
        cleared["network_requests"] = len(browser_manager._network_requests)
        cleared["cdp_network_requests"] = len(browser_manager._cdp_network_requests)
        cleared["websocket_messages"] = len(browser_manager._websocket_messages)
        browser_manager._network_requests.clear()
        browser_manager._request_id_counter = 0
        browser_manager._cdp_network_requests.clear()
        browser_manager._cdp_network_order.clear()
        browser_manager._websockets.clear()
        browser_manager._websocket_messages.clear()
        browser_manager._websocket_id_counter = 0
        browser_manager._websocket_frame_counter = 0
        browser_manager._capturing = False
    if clear_active_routes:
        try:
            from .instrumentation import _active_routes
            ctx = browser_manager.contexts.get("default")
            if ctx:
                for pat in list(_active_routes.keys()):
                    await ctx.unroute(pat)
            cleared["active_routes"] = len(_active_routes)
            _active_routes.clear()
        except Exception:
            cleared["active_routes_error"] = True
    if clear_cookies or clear_storage:
        page = await browser_manager.get_active_page()
        if clear_cookies:
            await page.context.clear_cookies()
        if clear_storage:
            await page.evaluate("localStorage.clear(); sessionStorage.clear();")
    return {"status": "reset", "cleared": cleared}
