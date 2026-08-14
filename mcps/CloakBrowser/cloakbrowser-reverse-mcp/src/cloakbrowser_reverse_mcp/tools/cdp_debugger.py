from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from ..cdp_monitor import enable_debugger_monitor, enable_network_monitor
from ..server import browser_manager, mcp
from ..utils.response_fmt import error_response


async def _session():
    page = await browser_manager.get_active_page()
    session = await browser_manager.new_cdp_session(page)
    return page, session


def _location(loc: dict | None) -> dict | None:
    if not loc:
        return None
    script_id = str(loc.get("scriptId") or "")
    script = browser_manager._cdp_scripts.get(script_id, {})
    return {
        "scriptId": script_id,
        "url": script.get("url"),
        "lineNumber": loc.get("lineNumber"),
        "columnNumber": loc.get("columnNumber"),
    }


async def _enable_debugger(session) -> None:
    await enable_debugger_monitor(browser_manager, session)


async def _enable_network(session) -> None:
    await enable_network_monitor(browser_manager, session)


def _is_probably_minified(source: str) -> bool:
    if not source:
        return False
    lines = source.splitlines() or [source]
    return max(len(line) for line in lines[:200]) > 600 or (len(lines) <= 3 and len(source) > 2000)


def _line_col(source: str, offset: int) -> tuple[int, int]:
    line = source.count("\n", 0, offset)
    col = offset - (source.rfind("\n", 0, offset) + 1)
    return line, col


def _line_context(source: str, line_number: int, context_lines: int) -> str:
    lines = source.splitlines()
    start = max(0, line_number - context_lines)
    end = min(len(lines), line_number + context_lines + 1)
    return "\n".join(f"{i + 1}: {lines[i]}" for i in range(start, end))


def _script_matches(meta: dict, script_id: str | None = None, url: str | None = None, url_filter: str | None = None) -> bool:
    script_url = meta.get("url") or ""
    if script_id and str(meta.get("scriptId")) != str(script_id):
        return False
    if url and url not in (str(meta.get("scriptId")), script_url):
        return False
    if url_filter and url_filter.lower() not in script_url.lower():
        return False
    return True


async def _script_source(session: Any, script_id: str) -> str:
    if script_id not in browser_manager._cdp_source_cache:
        src = await session.send("Debugger.getScriptSource", {"scriptId": script_id})
        browser_manager._cdp_source_cache[script_id] = src.get("scriptSource", "")
    return browser_manager._cdp_source_cache[script_id]


async def _find_script(session: Any, script_id: str | None = None, url: str | None = None) -> tuple[str, dict] | None:
    await _enable_debugger(session)
    if script_id and script_id in browser_manager._cdp_scripts:
        return script_id, browser_manager._cdp_scripts[script_id]
    if url:
        for sid, meta in browser_manager._cdp_scripts.items():
            script_url = meta.get("url") or ""
            if url == sid or url == script_url or url.lower() in script_url.lower():
                return sid, meta
    return None


def _decode_data_url(data_url: str) -> str | None:
    if not data_url.startswith("data:") or "," not in data_url:
        return None
    _meta, payload = data_url.split(",", 1)
    try:
        if ";base64" in _meta:
            return base64.b64decode(payload).decode("utf-8", errors="replace")
        from urllib.parse import unquote
        return unquote(payload)
    except Exception:
        return None


async def _fetch_text_from_page(url: str) -> str:
    page = await browser_manager.get_active_page()
    return await page.evaluate("""async url => {
      const r = await fetch(url, {credentials:'include'});
      if (!r.ok) throw new Error(`fetch ${r.status} ${url}`);
      return await r.text();
    }""", url)


def _load_source_map_from_text(text: str) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("source map is not a JSON object")
    return data


async def _load_source_map(meta: dict) -> dict:
    script_id = str(meta.get("scriptId") or "")
    if script_id in browser_manager._source_maps:
        return browser_manager._source_maps[script_id]
    sm_url = meta.get("sourceMapURL") or ""
    if not sm_url:
        raise ValueError("script has no sourceMapURL")
    script_url = meta.get("url") or ""
    resolved = sm_url if sm_url.startswith(("http://", "https://", "data:")) else urljoin(script_url, sm_url)
    if resolved.startswith("data:"):
        text = _decode_data_url(resolved)
        if text is None:
            raise ValueError("unable to decode data URL source map")
    else:
        text = await _fetch_text_from_page(resolved)
    data = _load_source_map_from_text(text)
    browser_manager._source_maps[script_id] = {"url": resolved, "map": data}
    return browser_manager._source_maps[script_id]


@mcp.tool()
async def cdp_status() -> dict:
    """Show CDP endpoint, script count, and paused status."""
    await browser_manager._ensure_browser()
    return {
        "cdp_url": browser_manager.cdp_endpoint(),
        "scripts": len(browser_manager._cdp_scripts),
        "source_cache": len(browser_manager._cdp_source_cache),
        "breakpoints": len(browser_manager._cdp_breakpoints),
        "cdp_network_requests": len(browser_manager._cdp_network_requests),
        "websockets": len(browser_manager._websockets),
        "websocket_messages": len(browser_manager._websocket_messages),
        "paused": browser_manager._paused_info is not None,
        "pause_reason": (browser_manager._paused_info or {}).get("reason"),
    }


@mcp.tool()
async def cdp_enable_debugger(skip_all_pauses: bool = True) -> dict:
    """Enable Chromium Runtime/Debugger domains for the active page."""
    try:
        _page, session = await _session()
        await _enable_debugger(session)
        if skip_all_pauses:
            await session.send("Debugger.setSkipAllPauses", {"skip": True})
            try:
                await session.send("Debugger.resume")
                browser_manager._paused_info = None
            except Exception:
                pass
        await _enable_network(session)
        return {"status": "enabled", "cdp_url": browser_manager.cdp_endpoint(), "skip_all_pauses": skip_all_pauses}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def set_cdp_skip_all_pauses(skip: bool = True, resume_if_paused: bool = True) -> dict:
    """Tell Chromium Debugger to ignore debugger statements and breakpoints for this session."""
    try:
        _page, session = await _session()
        await _enable_debugger(session)
        await session.send("Debugger.setSkipAllPauses", {"skip": skip})
        resumed = False
        if skip and resume_if_paused:
            try:
                await session.send("Debugger.resume")
                browser_manager._paused_info = None
                resumed = True
            except Exception:
                pass
        return {"status": "set", "skip_all_pauses": skip, "resumed": resumed}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def break_on_xhr(url: str) -> dict:
    """Set an XHR/fetch breakpoint for URLs containing the given string."""
    try:
        _page, session = await _session()
        await _enable_debugger(session)
        await session.send("DOMDebugger.setXHRBreakpoint", {"url": url})
        return {"status": "breakpoint_set", "url": url}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def remove_xhr_breakpoint(url: str) -> dict:
    """Remove an XHR/fetch URL breakpoint."""
    try:
        _page, session = await _session()
        await session.send("DOMDebugger.removeXHRBreakpoint", {"url": url})
        return {"status": "removed", "url": url}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def list_cdp_scripts(url_filter: str | None = None) -> list[dict]:
    """List scripts known to the CDP Debugger domain."""
    try:
        _page, session = await _session()
        await _enable_debugger(session)
        scripts = list(browser_manager._cdp_scripts.values())
        if url_filter:
            scripts = [s for s in scripts if url_filter.lower() in (s.get("url") or "").lower()]
        return scripts
    except Exception as exc:
        return [error_response(exc)]


@mcp.tool()
async def get_cdp_script_source(script_id: str) -> dict:
    """Get full source for a CDP scriptId."""
    try:
        _page, session = await _session()
        await _enable_debugger(session)
        source = await _script_source(session, script_id)
        return {"scriptId": script_id, "url": browser_manager._cdp_scripts.get(script_id, {}).get("url"), "source": source}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_cdp_source(script_id: str | None = None, url: str | None = None, start_line: int | None = None, end_line: int | None = None, offset: int | None = None, length: int = 1000) -> dict:
    """Get a CDP script source by scriptId or URL, optionally sliced by lines or character offset."""
    try:
        _page, session = await _session()
        found = await _find_script(session, script_id=script_id, url=url)
        if not found:
            return error_response("script not found")
        sid, meta = found
        source = await _script_source(session, sid)
        if offset is not None:
            snippet = source[offset:offset + max(0, length)]
            return {"scriptId": sid, "url": meta.get("url"), "mode": "offset", "offset": offset, "length": len(snippet), "source": snippet}
        if start_line is not None or end_line is not None:
            lines = source.splitlines()
            start = max(1, start_line or 1)
            end = min(len(lines), end_line or start)
            snippet = "\n".join(lines[start - 1:end])
            return {"scriptId": sid, "url": meta.get("url"), "mode": "lines", "start_line": start, "end_line": end, "source": snippet}
        return {"scriptId": sid, "url": meta.get("url"), "mode": "full", "length": len(source), "source": source}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def save_cdp_script_source(script_id: str | None = None, url: str | None = None, save_path: str = "") -> dict:
    """Save a full CDP script source to disk."""
    try:
        if not save_path:
            return error_response("save_path is required")
        _page, session = await _session()
        found = await _find_script(session, script_id=script_id, url=url)
        if not found:
            return error_response("script not found")
        sid, meta = found
        source = await _script_source(session, sid)
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return {"status": "saved", "scriptId": sid, "url": meta.get("url"), "path": str(path), "size": len(source)}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def search_cdp_sources(query: str, url_filter: str = "", is_regex: bool = False, case_sensitive: bool = False, exclude_minified: bool = False, max_results: int = 50, context_chars: int = 160) -> dict:
    """Search all loaded CDP script sources by string or regex."""
    try:
        if not query:
            return error_response("query is required")
        _page, session = await _session()
        await _enable_debugger(session)
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags) if is_regex else None
        matches = []
        total = 0
        for sid, meta in list(browser_manager._cdp_scripts.items()):
            if url_filter and url_filter.lower() not in (meta.get("url") or "").lower():
                continue
            try:
                source = await _script_source(session, sid)
            except Exception:
                continue
            if exclude_minified and _is_probably_minified(source):
                continue
            if pattern:
                for match in pattern.finditer(source):
                    start, end = match.start(), match.end()
                    matched_text = match.group(0)
                    total += 1
                    if len(matches) >= max_results:
                        continue
                    line, col = _line_col(source, start)
                    matches.append({
                        "scriptId": sid,
                        "url": meta.get("url"),
                        "offset": start,
                        "lineNumber": line,
                        "columnNumber": col,
                        "match": matched_text[:240],
                        "context": source[max(0, start - context_chars):min(len(source), end + context_chars)],
                    })
            else:
                haystack = source if case_sensitive else source.lower()
                needle = query if case_sensitive else query.lower()
                start_at = 0
                while True:
                    start = haystack.find(needle, start_at)
                    if start < 0:
                        break
                    end = start + len(query)
                    matched_text = source[start:end]
                    total += 1
                    if len(matches) < max_results:
                        line, col = _line_col(source, start)
                        matches.append({
                            "scriptId": sid,
                            "url": meta.get("url"),
                            "offset": start,
                            "lineNumber": line,
                            "columnNumber": col,
                            "match": matched_text[:240],
                            "context": source[max(0, start - context_chars):min(len(source), end + context_chars)],
                        })
                    start_at = start + max(1, len(query))
        return {"query": query, "total_matches": total, "returned": len(matches), "truncated": total > len(matches), "matches": matches}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def set_breakpoint_on_text(text: str, url_filter: str = "", occurrence: int = 1, condition: str = "") -> dict:
    """Find code text in loaded CDP scripts and set a breakpoint at that line."""
    try:
        if not text:
            return error_response("text is required")
        if occurrence < 1:
            return error_response("occurrence must be >= 1")
        _page, session = await _session()
        await _enable_debugger(session)
        found = 0
        for script_id, meta in list(browser_manager._cdp_scripts.items()):
            url = meta.get("url") or ""
            if url_filter and url_filter.lower() not in url.lower():
                continue
            try:
                src = (await session.send("Debugger.getScriptSource", {"scriptId": script_id})).get("scriptSource", "")
            except Exception:
                continue
            pos = -1
            start = 0
            while True:
                pos = src.find(text, start)
                if pos < 0:
                    break
                found += 1
                if found == occurrence:
                    line, col = _line_col(src, pos)
                    params: dict = {"location": {"scriptId": script_id, "lineNumber": line, "columnNumber": col}}
                    if condition:
                        params["condition"] = condition
                    bp = await session.send("Debugger.setBreakpoint", params)
                    bp_id = bp.get("breakpointId")
                    if bp_id:
                        browser_manager._cdp_breakpoints[bp_id] = {"breakpointId": bp_id, "type": "text", "text": text, "url_filter": url_filter, "condition": condition, "scriptId": script_id, "url": url, "lineNumber": line, "columnNumber": col}
                    return {"status": "set", "breakpointId": bp_id, "location": _location(bp.get("actualLocation")), "matched_url": url, "lineNumber": line, "columnNumber": col, "context": _line_context(src, line, 2)}
                start = pos + len(text)
        return error_response("text not found in loaded scripts")
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def set_cdp_breakpoint(script_id: str | None = None, url: str | None = None, line_number: int = 0, column_number: int = 0, condition: str = "") -> dict:
    """Set a breakpoint by scriptId/URL and zero-based line/column."""
    try:
        _page, session = await _session()
        found = await _find_script(session, script_id=script_id, url=url)
        if not found:
            return error_response("script not found")
        sid, meta = found
        params: dict = {"location": {"scriptId": sid, "lineNumber": line_number, "columnNumber": column_number}}
        if condition:
            params["condition"] = condition
        bp = await session.send("Debugger.setBreakpoint", params)
        bp_id = bp.get("breakpointId")
        if bp_id:
            browser_manager._cdp_breakpoints[bp_id] = {"breakpointId": bp_id, "type": "location", "condition": condition, "scriptId": sid, "url": meta.get("url"), "lineNumber": line_number, "columnNumber": column_number}
        return {"status": "set", "breakpointId": bp_id, "location": _location(bp.get("actualLocation")), "url": meta.get("url")}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def list_cdp_breakpoints() -> dict:
    """List breakpoints set through this MCP instance."""
    return {"count": len(browser_manager._cdp_breakpoints), "breakpoints": list(browser_manager._cdp_breakpoints.values())}


@mcp.tool()
async def remove_cdp_breakpoint(breakpoint_id: str | None = None, all_breakpoints: bool = False) -> dict:
    """Remove one or all CDP breakpoints set through this MCP instance."""
    try:
        _page, session = await _session()
        if all_breakpoints:
            removed = 0
            for bp_id in list(browser_manager._cdp_breakpoints.keys()):
                try:
                    await session.send("Debugger.removeBreakpoint", {"breakpointId": bp_id})
                    removed += 1
                except Exception:
                    pass
            browser_manager._cdp_breakpoints.clear()
            return {"status": "removed", "count": removed}
        if not breakpoint_id:
            return error_response("breakpoint_id is required unless all_breakpoints=True")
        await session.send("Debugger.removeBreakpoint", {"breakpointId": breakpoint_id})
        existed = browser_manager._cdp_breakpoints.pop(breakpoint_id, None) is not None
        return {"status": "removed", "breakpointId": breakpoint_id, "known": existed}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def list_source_maps(url_filter: str = "") -> dict:
    """List loaded CDP scripts that advertise source maps."""
    try:
        _page, session = await _session()
        await _enable_debugger(session)
        scripts = []
        for sid, meta in browser_manager._cdp_scripts.items():
            sm = meta.get("sourceMapURL")
            if not sm:
                continue
            url = meta.get("url") or ""
            if url_filter and url_filter.lower() not in url.lower() and url_filter.lower() not in sm.lower():
                continue
            scripts.append({"scriptId": sid, "url": url, "sourceMapURL": sm, "resolvedSourceMapURL": sm if sm.startswith(("http://", "https://", "data:")) else urljoin(url, sm)})
        return {"count": len(scripts), "source_maps": scripts}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_source_map(script_id: str | None = None, url: str | None = None, include_map: bool = False) -> dict:
    """Fetch and summarize a script source map."""
    try:
        _page, session = await _session()
        found = await _find_script(session, script_id=script_id, url=url)
        if not found:
            return error_response("script not found")
        sid, meta = found
        loaded = await _load_source_map(meta)
        data = loaded["map"]
        result = {
            "scriptId": sid,
            "url": meta.get("url"),
            "sourceMapURL": meta.get("sourceMapURL"),
            "resolvedSourceMapURL": loaded["url"],
            "version": data.get("version"),
            "file": data.get("file"),
            "sources_count": len(data.get("sources") or []),
            "sources": (data.get("sources") or [])[:200],
            "sourcesContent_count": len(data.get("sourcesContent") or []),
            "names_count": len(data.get("names") or []),
            "mappings_length": len(data.get("mappings") or ""),
        }
        if include_map:
            result["map"] = data
        return result
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_source_map_source(script_id: str | None = None, url: str | None = None, source_index: int | None = None, source_path: str | None = None) -> dict:
    """Return an original source from a source map's sourcesContent."""
    try:
        _page, session = await _session()
        found = await _find_script(session, script_id=script_id, url=url)
        if not found:
            return error_response("script not found")
        sid, meta = found
        loaded = await _load_source_map(meta)
        data = loaded["map"]
        sources = data.get("sources") or []
        contents = data.get("sourcesContent") or []
        idx = source_index
        if idx is None and source_path:
            low = source_path.lower()
            for i, src in enumerate(sources):
                if low in str(src).lower():
                    idx = i
                    break
        if idx is None or idx < 0 or idx >= len(sources):
            return error_response("source not found")
        content = contents[idx] if idx < len(contents) else None
        if content is None:
            source_root = data.get("sourceRoot") or ""
            fetch_url = urljoin(loaded["url"], source_root + sources[idx])
            try:
                content = await _fetch_text_from_page(fetch_url)
            except Exception as exc:
                return {"scriptId": sid, "source_index": idx, "source": sources[idx], "content": None, "error": f"sourcesContent missing and fetch failed: {exc}"}
        return {"scriptId": sid, "script_url": meta.get("url"), "source_index": idx, "source": sources[idx], "length": len(content), "content": content}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_paused_info(frame_index: int = 0, include_scopes: bool = True, max_scope_depth: int = 2) -> dict:
    """Get current paused call stack and selected frame scope variables."""
    try:
        ev = browser_manager._paused_info
        if not ev:
            return {"paused": False}
        frames = ev.get("callFrames", [])
        out_frames = []
        for i, frame in enumerate(frames):
            loc = frame.get("location", {})
            script_id = str(loc.get("scriptId") or "")
            out_frames.append({"index": i, "functionName": frame.get("functionName"), "location": _location(loc), "url": browser_manager._cdp_scripts.get(script_id, {}).get("url")})
        result = {"paused": True, "reason": ev.get("reason"), "callFrames": out_frames}
        if include_scopes and 0 <= frame_index < len(frames):
            _page, session = await _session()
            scopes = []
            for scope in frames[frame_index].get("scopeChain", [])[:max_scope_depth]:
                obj_id = scope.get("object", {}).get("objectId")
                props = []
                if obj_id:
                    try:
                        data = await session.send("Runtime.getProperties", {"objectId": obj_id, "ownProperties": True, "generatePreview": True})
                        for p in data.get("result", [])[:80]:
                            v = p.get("value", {})
                            props.append({"name": p.get("name"), "type": v.get("type"), "value": v.get("value"), "description": v.get("description")})
                    except Exception as exc:
                        props.append({"error": str(exc)})
                scopes.append({"type": scope.get("type"), "name": scope.get("name"), "properties": props})
            result["scopes"] = scopes
        return result
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def resume_debugger() -> dict:
    """Resume JavaScript execution if paused."""
    try:
        _page, session = await _session()
        await session.send("Debugger.resume")
        browser_manager._paused_info = None
        return {"status": "resumed"}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def step_debugger(direction: str = "over") -> dict:
    """Step JavaScript execution: over, into, or out."""
    try:
        _page, session = await _session()
        method = {"over": "Debugger.stepOver", "into": "Debugger.stepInto", "out": "Debugger.stepOut"}.get(direction)
        if not method:
            return error_response("direction must be over, into, or out")
        browser_manager._paused_info = None
        await session.send(method)
        return {"status": "stepping", "direction": direction}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def evaluate_on_paused(expression: str, frame_index: int = 0) -> dict:
    """Evaluate a JS expression in a paused call frame."""
    try:
        ev = browser_manager._paused_info
        if not ev:
            return error_response("not paused")
        frames = ev.get("callFrames", [])
        if not (0 <= frame_index < len(frames)):
            return error_response("invalid frame_index")
        _page, session = await _session()
        res = await session.send("Debugger.evaluateOnCallFrame", {"callFrameId": frames[frame_index]["callFrameId"], "expression": expression, "returnByValue": True})
        if "exceptionDetails" in res:
            return {"type": "error", "exception": res["exceptionDetails"]}
        obj = res.get("result", {})
        if obj.get("subtype") == "null":
            return {"value": None, "type": "null"}
        if "value" in obj:
            return {"value": obj.get("value"), "type": obj.get("type")}
        if obj.get("unserializableValue"):
            return {"value": obj.get("unserializableValue"), "type": obj.get("type")}
        if obj.get("objectId"):
            preview = await session.send("Runtime.callFunctionOn", {"objectId": obj["objectId"], "functionDeclaration": "function(){ try { return JSON.stringify(this); } catch(e) { return String(this); } }", "returnByValue": True})
            return {"value": preview.get("result", {}).get("value"), "type": obj.get("type"), "description": obj.get("description")}
        return obj
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def capture_heap_snapshot(save_path: str) -> dict:
    """Capture a Chrome heap snapshot to a file."""
    try:
        _page, session = await _session()
        chunks = []

        def on_chunk(ev: dict) -> None:
            chunks.append(ev.get("chunk", ""))

        session.on("HeapProfiler.addHeapSnapshotChunk", on_chunk)
        await session.send("HeapProfiler.enable")
        await session.send("HeapProfiler.takeHeapSnapshot", {"reportProgress": False})
        with open(save_path, "w", encoding="utf-8") as fh:
            fh.write("".join(chunks))
        return {"status": "saved", "path": save_path, "chunks": len(chunks)}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def capture_screenshot_cdp(format: str = "png", quality: int | None = None) -> dict:
    """Capture screenshot through CDP Page.captureScreenshot."""
    try:
        _page, session = await _session()
        await session.send("Page.enable")
        params: dict = {"format": format}
        if quality is not None and format in ("jpeg", "webp"):
            params["quality"] = quality
        data = await session.send("Page.captureScreenshot", params)
        # Ensure it is valid base64 by decoding once.
        base64.b64decode(data.get("data", ""))
        return {"image_base64": data.get("data"), "format": format}
    except Exception as exc:
        return error_response(exc)
