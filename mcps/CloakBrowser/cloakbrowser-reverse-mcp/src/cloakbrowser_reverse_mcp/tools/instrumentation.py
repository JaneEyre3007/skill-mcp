from __future__ import annotations

from typing import Literal

from ..server import browser_manager, mcp
from ..utils.js_rewriter import regex_rewrite
from ..utils.response_fmt import error_response

_active_routes: dict[str, dict] = {}

_STRIP_HEADERS = {"content-length", "content-encoding", "transfer-encoding"}


@mcp.tool()
async def instrumentation(action: Literal["install", "log", "stop", "reload", "status"], url_pattern: str = "", mode: Literal["ast", "regex"] = "ast", tag: str = "vmp", rewrite_member_access: bool = True, rewrite_calls: bool = True, max_rewrites: int = 20000, fallback_on_error: bool = True, ignore_csp: bool = False, clear_log: bool = True, wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "load", tag_filter: str | None = None, type_filter: str | None = None, key_filter: str | None = None, limit: int = 500, clear: bool = False, filter_property_names: list[str] | None = None, filter_object_names: list[str] | None = None, max_file_size: int = 200_000, on_oversized: Literal["selective", "skip", "force"] = "selective") -> dict:
    """Source-level script instrumentation via route rewriting."""
    if action == "install":
        return await _install(url_pattern, tag, rewrite_member_access, rewrite_calls, max_rewrites, filter_property_names, filter_object_names, max_file_size, on_oversized)
    if action == "log":
        return await _get_log(tag_filter, type_filter, key_filter, limit, clear)
    if action == "stop":
        return await _stop(url_pattern or None)
    if action == "reload":
        page = await browser_manager.get_active_page()
        if clear_log:
            await page.evaluate("window.__mcp_instrument_log=[]")
        resp = await page.reload(wait_until=wait_until)
        return {"status": "reloaded", "url": page.url, "http_status": resp.status if resp else None}
    if action == "status":
        return {"total_patterns": len(_active_routes), "active_patterns": [{"pattern": p, **{k: v for k, v in info.items() if k != 'handler'}} for p, info in _active_routes.items()]}
    return error_response("unknown action")


async def _install(url_pattern: str, tag: str, rewrite_member_access: bool, rewrite_calls: bool, max_rewrites: int, filter_property_names: list[str] | None, filter_object_names: list[str] | None, max_file_size: int, on_oversized: str) -> dict:
    if not url_pattern:
        return error_response("url_pattern is required")
    ctx = browser_manager.contexts.get("default")
    if ctx is None:
        await browser_manager._ensure_browser()
        ctx = browser_manager.contexts.get("default")
    if ctx is None:
        return error_response("no browser context")
    stats = {"files_rewritten": 0, "total_edits": 0, "last_url": None}
    cache: dict[str, str] = {}

    async def handler(route):
        req_url = route.request.url
        if req_url in cache:
            await route.fulfill(status=200, headers={"content-type": "application/javascript; charset=utf-8"}, body=cache[req_url])
            return
        resp = await route.fetch()
        body = await resp.body()
        try:
            src = body.decode("utf-8")
        except UnicodeDecodeError:
            src = body.decode("latin-1")
        if len(src.encode("utf-8")) > max_file_size and on_oversized == "skip":
            await route.fulfill(status=resp.status, headers={k: v for k, v in resp.headers.items() if k.lower() not in _STRIP_HEADERS}, body=body)
            return
        rewritten, edits = regex_rewrite(src, tag, rewrite_member_access, rewrite_calls, max_rewrites, filter_property_names, filter_object_names)
        cache[req_url] = rewritten
        stats["files_rewritten"] += 1
        stats["total_edits"] += edits
        stats["last_url"] = req_url
        headers = {k: v for k, v in resp.headers.items() if k.lower() not in _STRIP_HEADERS}
        headers["content-type"] = "application/javascript; charset=utf-8"
        await route.fulfill(status=resp.status, headers=headers, body=rewritten)

    await ctx.route(url_pattern, handler)
    _active_routes[url_pattern] = {"tag": tag, "mode": "regex", "stats": stats, "cached_urls": 0, "handler": handler}
    return {"status": "installed", "pattern": url_pattern, "tag": tag, "mode": "regex"}


async def _get_log(tag_filter, type_filter, key_filter, limit, clear) -> dict:
    page = await browser_manager.get_active_page()
    logs = await page.evaluate("""() => window.__mcp_instrument_log || []""")
    if tag_filter:
        logs = [x for x in logs if x.get("tag") == tag_filter]
    if type_filter:
        logs = [x for x in logs if x.get("type") == type_filter]
    if key_filter:
        logs = [x for x in logs if key_filter in x.get("key", "")]
    out = logs[-limit:]
    if clear:
        await page.evaluate("window.__mcp_instrument_log=[]")
    return {"total": len(logs), "returned": len(out), "entries": out}


async def _stop(pattern: str | None) -> dict:
    ctx = browser_manager.contexts.get("default")
    if ctx is None:
        return error_response("no browser context")
    targets = [pattern] if pattern else list(_active_routes.keys())
    stopped = 0
    for pat in targets:
        if pat in _active_routes:
            await ctx.unroute(pat)
            _active_routes.pop(pat, None)
            stopped += 1
    return {"status": "stopped", "count": stopped}
