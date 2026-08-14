from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import Literal

from ..cdp_monitor import enable_network_monitor
from ..server import browser_manager, mcp
from ..utils.response_fmt import error_response


async def _ensure_ws_capture() -> None:
    page = await browser_manager.get_active_page()
    session = await browser_manager.new_cdp_session(page)
    await enable_network_monitor(browser_manager, session)


def _payload_group(payload: str) -> tuple[str, str]:
    text = payload or ""
    stripped = text.strip()
    if not stripped:
        return "empty", "empty payload"
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            keys = sorted(str(k) for k in data.keys())[:20]
            return "json:" + hashlib.sha1(",".join(keys).encode("utf-8")).hexdigest()[:10], "json object keys: " + ",".join(keys)
        if isinstance(data, list):
            first_type = type(data[0]).__name__ if data else "empty"
            return f"json_array:{first_type}:{len(data)}", f"json array len={len(data)} first={first_type}"
        return f"json_scalar:{type(data).__name__}", f"json scalar {type(data).__name__}"
    except Exception:
        pass
    if re.fullmatch(r"[A-Za-z0-9+/=\s]+", stripped) and len(stripped) >= 24:
        return "base64_like", "base64-like text"
    if re.fullmatch(r"[0-9a-fA-F]+", stripped) and len(stripped) >= 16:
        return "hex_like", "hex-like text"
    shape = re.sub(r"\d+", "#", stripped[:200])
    shape = re.sub(r"[A-Za-z_][A-Za-z0-9_]{3,}", "w", shape)
    digest = hashlib.sha1(shape.encode("utf-8", errors="ignore")).hexdigest()[:10]
    return "text:" + digest, "text shape: " + shape[:120]


def _filtered_messages(wsid: int | None = None, direction: str | None = None, url_filter: str = "") -> list[dict]:
    rows = list(browser_manager._websocket_messages)
    if wsid is not None:
        rows = [m for m in rows if m.get("wsid") == wsid]
    if direction:
        rows = [m for m in rows if m.get("direction") == direction]
    if url_filter:
        rows = [m for m in rows if url_filter in (m.get("url") or "")]
    return rows


@mcp.tool()
async def websocket_capture(action: Literal["start", "clear", "status"] = "start") -> dict:
    """Enable, clear, or inspect CDP WebSocket capture."""
    try:
        if action == "start":
            await _ensure_ws_capture()
            return {"status": "capturing", "connections": len(browser_manager._websockets), "messages": len(browser_manager._websocket_messages)}
        if action == "clear":
            connections = len(browser_manager._websockets)
            messages = len(browser_manager._websocket_messages)
            browser_manager._websockets.clear()
            browser_manager._websocket_messages.clear()
            browser_manager._websocket_id_counter = 0
            browser_manager._websocket_frame_counter = 0
            return {"status": "cleared", "connections": connections, "messages": messages}
        if action == "status":
            return {"enabled_sessions": len(browser_manager._cdp_network_enabled_sessions), "connections": len(browser_manager._websockets), "messages": len(browser_manager._websocket_messages)}
        return error_response("unknown action")
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def list_websockets(url_filter: str = "", include_closed: bool = True) -> list[dict]:
    """List captured WebSocket connections."""
    try:
        await _ensure_ws_capture()
        rows = []
        for ws in browser_manager._websockets.values():
            if url_filter and url_filter not in (ws.get("url") or ""):
                continue
            if not include_closed and ws.get("closed"):
                continue
            rows.append({
                "wsid": ws.get("wsid"),
                "request_id": ws.get("request_id"),
                "url": ws.get("url"),
                "status": ws.get("status"),
                "sent": ws.get("sent"),
                "received": ws.get("received"),
                "closed": ws.get("closed"),
                "created_at": ws.get("created_at"),
                "closed_at": ws.get("closed_at"),
            })
        rows.sort(key=lambda x: int(x.get("wsid") or 0))
        return rows
    except Exception as exc:
        return [error_response(exc)]


@mcp.tool()
async def get_websocket_messages(wsid: int | None = None, direction: Literal["sent", "received"] | None = None, url_filter: str = "", page_idx: int = 0, page_size: int = 20, show_content: bool = False, analyze: bool = False, group_id: str = "", frame_index: int | None = None) -> dict:
    """List WebSocket messages or analyze/group them by payload shape."""
    try:
        await _ensure_ws_capture()
        rows = _filtered_messages(wsid=wsid, direction=direction, url_filter=url_filter)
        if frame_index is not None:
            row = next((m for m in rows if m.get("frame_index") == frame_index), None)
            if not row:
                return error_response("frame_index not found")
            return dict(row)
        if analyze:
            groups: dict[str, dict] = {}
            group_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            group_key_to_id: dict[str, str] = {}
            for msg in rows:
                key, description = _payload_group(str(msg.get("payload") or ""))
                if key not in group_key_to_id:
                    idx = len(group_key_to_id)
                    group_key_to_id[key] = group_names[idx] if idx < len(group_names) else f"G{idx + 1}"
                gid = group_key_to_id[key]
                if group_id and gid != group_id:
                    continue
                group = groups.setdefault(gid, {"groupId": gid, "key": key, "description": description, "count": 0, "sent": 0, "received": 0, "sizes": [], "sample_indices": [], "sample_payloads": []})
                group["count"] += 1
                group[msg.get("direction") or "received"] += 1
                group["sizes"].append(msg.get("size") or 0)
                if len(group["sample_indices"]) < 8:
                    group["sample_indices"].append(msg.get("frame_index"))
                    group["sample_payloads"].append(str(msg.get("payload") or "")[:500])
            out = []
            for group in groups.values():
                sizes = group.pop("sizes")
                group["min_size"] = min(sizes) if sizes else 0
                group["max_size"] = max(sizes) if sizes else 0
                group["avg_size"] = round(sum(sizes) / len(sizes), 2) if sizes else 0
                out.append(group)
            out.sort(key=lambda g: g["count"], reverse=True)
            return {"mode": "analyze", "total_messages": len(rows), "groups": out}

        start = max(0, page_idx) * max(1, page_size)
        end = start + max(1, page_size)
        page_rows = []
        for msg in rows[start:end]:
            item = dict(msg)
            if not show_content:
                item.pop("payload", None)
            page_rows.append(item)
        by_direction = Counter(str(m.get("direction")) for m in rows)
        return {"mode": "messages", "total": len(rows), "page_idx": page_idx, "page_size": page_size, "returned": len(page_rows), "by_direction": dict(by_direction), "messages": page_rows}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_websocket_connection(wsid: int, include_messages: bool = False, max_messages: int = 50) -> dict:
    """Get one WebSocket connection with handshake metadata and optional recent messages."""
    try:
        await _ensure_ws_capture()
        ws = next((dict(x) for x in browser_manager._websockets.values() if x.get("wsid") == wsid), None)
        if not ws:
            return error_response("wsid not found")
        if include_messages:
            msgs = [dict(m) for m in _filtered_messages(wsid=wsid)][-max_messages:]
            ws["messages"] = msgs
        return ws
    except Exception as exc:
        return error_response(exc)
