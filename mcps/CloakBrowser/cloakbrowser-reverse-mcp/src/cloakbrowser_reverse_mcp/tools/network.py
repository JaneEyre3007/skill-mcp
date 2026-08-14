from __future__ import annotations

from typing import Literal

from ..cdp_monitor import enable_network_monitor
from ..server import browser_manager, mcp
from ..utils.response_fmt import error_response


async def _ensure_cdp_network() -> None:
    page = await browser_manager.get_active_page()
    session = await browser_manager.new_cdp_session(page)
    await enable_network_monitor(browser_manager, session)


def _normalize_initiator(initiator: dict | None) -> dict:
    if not initiator:
        return {"type": "unknown", "stack": None, "url": None, "lineNumber": None, "columnNumber": None}
    stack = initiator.get("stack") or {}
    frames = []
    current = stack
    while current:
        for frame in current.get("callFrames") or []:
            frames.append({
                "functionName": frame.get("functionName"),
                "url": frame.get("url"),
                "lineNumber": frame.get("lineNumber"),
                "columnNumber": frame.get("columnNumber"),
            })
        current = current.get("parent")
    top = frames[0] if frames else {}
    return {
        "type": initiator.get("type") or "unknown",
        "url": initiator.get("url") or top.get("url"),
        "lineNumber": initiator.get("lineNumber") if initiator.get("lineNumber") is not None else top.get("lineNumber"),
        "columnNumber": initiator.get("columnNumber") if initiator.get("columnNumber") is not None else top.get("columnNumber"),
        "requestId": initiator.get("requestId"),
        "stack": {"callFrames": frames} if frames else None,
        "raw": initiator,
    }


def _find_cdp_request_for_playwright(playwright_entry: dict) -> dict | None:
    target_url = playwright_entry.get("url")
    target_method = playwright_entry.get("method")
    target_ts = int(playwright_entry.get("timestamp") or 0)
    candidates = []
    for request_id in browser_manager._cdp_network_order:
        entry = browser_manager._cdp_network_requests.get(request_id) or {}
        if entry.get("url") != target_url:
            continue
        if target_method and entry.get("method") and entry.get("method") != target_method:
            continue
        delta = abs(int(entry.get("timestamp") or target_ts) - target_ts)
        candidates.append((delta, entry))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


@mcp.tool()
async def network_capture(action: Literal["start", "stop", "clear", "status"], url_pattern: str = "**/*", capture_body: bool = False) -> dict:
    """Start/stop/clear/status network capture."""
    if action == "start":
        try:
            await _ensure_cdp_network()
        except Exception:
            pass
        browser_manager._capturing = True
        browser_manager._capture_pattern = url_pattern
        browser_manager._capture_body = capture_body
        return {"status": "capturing", "pattern": url_pattern, "capture_body": capture_body}
    if action == "stop":
        browser_manager._capturing = False
        return {"status": "stopped", "total_requests": len(browser_manager._network_requests)}
    if action == "clear":
        count = len(browser_manager._network_requests)
        browser_manager._network_requests.clear()
        browser_manager._request_id_counter = 0
        browser_manager._cdp_network_requests.clear()
        browser_manager._cdp_network_order.clear()
        return {"status": "cleared", "cleared_count": count}
    if action == "status":
        return {"active": browser_manager._capturing, "pattern": browser_manager._capture_pattern, "capture_body": browser_manager._capture_body, "buffer_size": len(browser_manager._network_requests)}
    return error_response("unknown action")


@mcp.tool()
async def list_network_requests(url_filter: str | None = None, url_contains_domain: str | None = None, method: str | None = None, resource_type: str | None = None, status_code: int | None = None) -> list[dict]:
    """List captured network requests."""
    reqs = list(browser_manager._network_requests)
    if url_filter:
        reqs = [r for r in reqs if url_filter in r.get("url", "")]
    if url_contains_domain:
        reqs = [r for r in reqs if url_contains_domain in r.get("url", "")]
    if method:
        reqs = [r for r in reqs if r.get("method", "").upper() == method.upper()]
    if resource_type:
        reqs = [r for r in reqs if r.get("resource_type") == resource_type]
    if status_code is not None:
        reqs = [r for r in reqs if r.get("status") == status_code]
    return [{"id": r["id"], "url": r["url"][:240], "method": r["method"], "status": r.get("status"), "type": r.get("resource_type"), "ms": r.get("duration"), "size": len(r.get("response_body") or ""), "has_body": bool(r.get("response_body"))} for r in reqs]


@mcp.tool()
async def get_network_request(request_id: int, include_body: bool = False, include_headers: bool = True, max_body_size: int = 5000) -> dict:
    """Get details of one captured request."""
    for req in browser_manager._network_requests:
        if req["id"] == request_id:
            result = dict(req)
            if not include_headers:
                result.pop("request_headers", None)
                result.pop("response_headers", None)
            if not include_body:
                body = result.pop("response_body", None)
                result["response_body_available"] = body is not None
                if body:
                    result["response_body_size"] = len(body)
            else:
                body = result.get("response_body")
                if isinstance(body, str) and max_body_size >= 0 and len(body) > max_body_size:
                    result["response_body"] = body[:max_body_size]
                    result["response_body_truncated"] = True
            return result
    return error_response(f"Request ID {request_id} not found")


@mcp.tool()
async def get_request_initiator(request_id: int) -> dict:
    """Find request initiator, preferring Chromium CDP's Puppeteer-style initiator."""
    target = next((r for r in browser_manager._network_requests if r["id"] == request_id), None)
    if not target:
        return error_response(f"Request ID {request_id} not found")
    try:
        await _ensure_cdp_network()
    except Exception:
        pass
    cdp_req = _find_cdp_request_for_playwright(target)
    if cdp_req and cdp_req.get("initiator"):
        normalized = _normalize_initiator(cdp_req.get("initiator"))
        return {
            "url": cdp_req.get("url") or target.get("url"),
            "method": cdp_req.get("method") or target.get("method"),
            "initiator_type": normalized.get("type"),
            "initiator_stack": normalized.get("stack"),
            "initiator_url": normalized.get("url"),
            "lineNumber": normalized.get("lineNumber"),
            "columnNumber": normalized.get("columnNumber"),
            "source": "cdp",
            "cdp_request_id": cdp_req.get("cdp_request_id"),
            "raw_initiator": normalized.get("raw"),
        }
    page = await browser_manager.get_active_page()
    result = await page.evaluate("""(reqUrl) => {
      function scan(logs, type) {
        for (let i=(logs||[]).length-1; i>=0; i--) {
          const x = logs[i], u = x.url || '';
          if (reqUrl === u || reqUrl.includes(u) || u.includes(reqUrl)) return {...x, type};
          try { const a = new URL(reqUrl, location.origin), b = new URL(u, location.origin); if (a.host === b.host && a.pathname === b.pathname) return {...x, type}; } catch(e) {}
        }
        return null;
      }
      return scan(window.__mcp_xhr_log, 'xhr') || scan(window.__mcp_fetch_log, 'fetch') || {url:reqUrl, type:'unknown', stack:null, diagnostics:{xhr_hook_active:!!window.__mcp_xhr_hooked, fetch_hook_active:!!window.__mcp_fetch_hooked}};
    }""", target["url"])
    return {"url": result.get("url"), "initiator_stack": result.get("stack"), "initiator_type": result.get("type"), "method": result.get("method"), "request_headers": result.get("headers"), "request_body": result.get("body"), "diagnostics": result.get("diagnostics"), "source": "page_hook"}


@mcp.tool()
async def list_cdp_network_requests(url_filter: str | None = None, method: str | None = None, resource_type: str | None = None, has_initiator: bool | None = None, limit: int = 100) -> list[dict]:
    """List Chromium CDP Network requests with native initiator metadata."""
    try:
        await _ensure_cdp_network()
    except Exception as exc:
        return [error_response(exc)]
    rows = []
    for request_id in reversed(browser_manager._cdp_network_order):
        r = browser_manager._cdp_network_requests.get(request_id) or {}
        if url_filter and url_filter not in (r.get("url") or ""):
            continue
        if method and method.upper() != str(r.get("method") or "").upper():
            continue
        if resource_type and resource_type != r.get("type"):
            continue
        if has_initiator is not None and bool(r.get("initiator")) != has_initiator:
            continue
        initiator = _normalize_initiator(r.get("initiator")) if r.get("initiator") else None
        rows.append({
            "cdp_request_id": r.get("cdp_request_id"),
            "url": (r.get("url") or "")[:240],
            "method": r.get("method"),
            "status": r.get("status"),
            "type": r.get("type"),
            "mime_type": r.get("mime_type"),
            "ms": r.get("duration"),
            "encoded_data_length": r.get("encoded_data_length"),
            "initiator_type": initiator.get("type") if initiator else None,
            "initiator_url": initiator.get("url") if initiator else None,
            "lineNumber": initiator.get("lineNumber") if initiator else None,
            "columnNumber": initiator.get("columnNumber") if initiator else None,
        })
        if len(rows) >= limit:
            break
    return rows


@mcp.tool()
async def get_cdp_network_request(cdp_request_id: str, include_body: bool = False, max_body_size: int = 5000) -> dict:
    """Get one Chromium CDP Network request, including native initiator and optional response body."""
    try:
        await _ensure_cdp_network()
        r = dict(browser_manager._cdp_network_requests.get(cdp_request_id) or {})
        if not r:
            return error_response(f"CDP request ID {cdp_request_id} not found")
        r["normalized_initiator"] = _normalize_initiator(r.get("initiator")) if r.get("initiator") else None
        if include_body:
            page = await browser_manager.get_active_page()
            session = await browser_manager.new_cdp_session(page)
            try:
                body = await session.send("Network.getResponseBody", {"requestId": cdp_request_id})
                text = body.get("body", "")
                if max_body_size >= 0 and len(text) > max_body_size:
                    r["response_body"] = text[:max_body_size]
                    r["response_body_truncated"] = True
                    r["response_body_size"] = len(text)
                else:
                    r["response_body"] = text
                r["response_body_base64_encoded"] = body.get("base64Encoded")
            except Exception as exc:
                r["response_body_error"] = str(exc)
        return r
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_cdp_request_initiator(cdp_request_id: str) -> dict:
    """Return Puppeteer-style CDP Network.Initiator for one CDP request ID."""
    try:
        await _ensure_cdp_network()
        r = browser_manager._cdp_network_requests.get(cdp_request_id)
        if not r:
            return error_response(f"CDP request ID {cdp_request_id} not found")
        normalized = _normalize_initiator(r.get("initiator"))
        return {
            "cdp_request_id": cdp_request_id,
            "url": r.get("url"),
            "method": r.get("method"),
            "initiator_type": normalized.get("type"),
            "initiator_url": normalized.get("url"),
            "lineNumber": normalized.get("lineNumber"),
            "columnNumber": normalized.get("columnNumber"),
            "initiator_stack": normalized.get("stack"),
            "raw_initiator": normalized.get("raw"),
            "source": "cdp",
        }
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def intercept_request(url_pattern: str, action: Literal["log", "block", "modify", "mock", "stop"] = "log", modify_headers: dict | None = None, modify_body: str | None = None, mock_response: dict | None = None) -> dict:
    """Intercept network requests matching a pattern."""
    ctx = browser_manager.contexts.get("default")
    if ctx is None:
        await browser_manager._ensure_browser()
        ctx = browser_manager.contexts.get("default")
    if ctx is None:
        return error_response("no browser context")
    if action == "stop":
        await ctx.unroute(url_pattern)
        browser_manager._route_handlers.pop(url_pattern, None)
        return {"status": "stopped", "pattern": url_pattern}

    async def handler(route):
        if action == "block":
            await route.abort()
        elif action == "mock":
            resp = mock_response or {"status": 200, "body": ""}
            await route.fulfill(status=resp.get("status", 200), headers=resp.get("headers"), body=resp.get("body", ""))
        elif action == "modify":
            headers = dict(route.request.headers)
            headers.update(modify_headers or {})
            await route.continue_(headers=headers, post_data=modify_body)
        else:
            await route.continue_()

    await ctx.route(url_pattern, handler)
    browser_manager._route_handlers[url_pattern] = handler
    return {"status": "installed", "pattern": url_pattern, "action": action}
