from __future__ import annotations

import time
from typing import Any

from .browser import BrowserManager


async def enable_debugger_monitor(browser_manager: BrowserManager, session: Any) -> None:
    """Enable Runtime/Debugger once per CDP session and cache script/paused events."""
    session_key = id(session)
    if session_key in browser_manager._cdp_debugger_enabled_sessions:
        return

    def on_script(ev: dict) -> None:
        script_id = str(ev.get("scriptId") or "")
        if not script_id:
            return
        browser_manager._cdp_scripts[script_id] = {
            "scriptId": script_id,
            "url": ev.get("url"),
            "startLine": ev.get("startLine"),
            "startColumn": ev.get("startColumn"),
            "endLine": ev.get("endLine"),
            "endColumn": ev.get("endColumn"),
            "executionContextId": ev.get("executionContextId"),
            "hash": ev.get("hash"),
            "isModule": ev.get("isModule"),
            "length": ev.get("length"),
            "sourceMapURL": ev.get("sourceMapURL"),
            "hasSourceURL": ev.get("hasSourceURL"),
        }

    def on_paused(ev: dict) -> None:
        browser_manager._paused_info = ev

    def on_resumed(_ev: dict | None = None) -> None:
        browser_manager._paused_info = None

    session.on("Debugger.scriptParsed", on_script)
    session.on("Debugger.paused", on_paused)
    session.on("Debugger.resumed", on_resumed)
    await session.send("Runtime.enable")
    await session.send("Debugger.enable")
    browser_manager._cdp_debugger_enabled_sessions.add(session_key)


async def enable_network_monitor(browser_manager: BrowserManager, session: Any) -> None:
    """Enable Network once per CDP session and cache request, initiator, and WS events."""
    session_key = id(session)
    if session_key in browser_manager._cdp_network_enabled_sessions:
        return

    def remember_request_id(request_id: str) -> None:
        if not request_id:
            return
        if request_id not in browser_manager._cdp_network_requests:
            browser_manager._cdp_network_order.append(request_id)
            browser_manager._cdp_network_requests[request_id] = {"cdp_request_id": request_id}

    def on_request(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if not request_id:
            return
        remember_request_id(request_id)
        req = ev.get("request") or {}
        entry = browser_manager._cdp_network_requests[request_id]
        if ev.get("redirectResponse"):
            entry.setdefault("redirects", []).append(ev.get("redirectResponse"))
        wall_time = ev.get("wallTime")
        timestamp_ms = int(float(wall_time) * 1000) if wall_time else int(time.time() * 1000)
        entry.update({
            "cdp_request_id": request_id,
            "loader_id": ev.get("loaderId"),
            "document_url": ev.get("documentURL"),
            "frame_id": ev.get("frameId"),
            "type": ev.get("type"),
            "url": req.get("url"),
            "method": req.get("method"),
            "request_headers": req.get("headers"),
            "request_post_data": req.get("postData"),
            "has_post_data": req.get("hasPostData"),
            "initiator": ev.get("initiator"),
            "timestamp": timestamp_ms,
            "monotonic_timestamp": ev.get("timestamp"),
            "wall_time": wall_time,
        })

    def on_response(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if not request_id:
            return
        remember_request_id(request_id)
        resp = ev.get("response") or {}
        entry = browser_manager._cdp_network_requests[request_id]
        entry.update({
            "status": resp.get("status"),
            "status_text": resp.get("statusText"),
            "mime_type": resp.get("mimeType"),
            "response_headers": resp.get("headers"),
            "remote_ip_address": resp.get("remoteIPAddress"),
            "remote_port": resp.get("remotePort"),
            "from_disk_cache": resp.get("fromDiskCache"),
            "from_service_worker": resp.get("fromServiceWorker"),
            "protocol": resp.get("protocol"),
            "security_state": resp.get("securityState"),
            "response_timestamp": int(time.time() * 1000),
        })

    def on_finished(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if not request_id:
            return
        remember_request_id(request_id)
        entry = browser_manager._cdp_network_requests[request_id]
        finished_ms = int(time.time() * 1000)
        entry.update({
            "finished": True,
            "finished_timestamp": finished_ms,
            "encoded_data_length": ev.get("encodedDataLength"),
        })
        if entry.get("timestamp"):
            entry["duration"] = finished_ms - int(entry["timestamp"])

    def on_failed(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if not request_id:
            return
        remember_request_id(request_id)
        browser_manager._cdp_network_requests[request_id].update({
            "failed": True,
            "blocked_reason": ev.get("blockedReason"),
            "cors_error_status": ev.get("corsErrorStatus"),
            "error_text": ev.get("errorText"),
            "canceled": ev.get("canceled"),
            "failed_timestamp": int(time.time() * 1000),
        })

    def ensure_ws(request_id: str, url: str | None = None) -> dict:
        if request_id not in browser_manager._websockets:
            browser_manager._websocket_id_counter += 1
            browser_manager._websockets[request_id] = {
                "wsid": browser_manager._websocket_id_counter,
                "request_id": request_id,
                "url": url,
                "created_at": int(time.time() * 1000),
                "sent": 0,
                "received": 0,
                "closed": False,
            }
        elif url and not browser_manager._websockets[request_id].get("url"):
            browser_manager._websockets[request_id]["url"] = url
        return browser_manager._websockets[request_id]

    def on_ws_created(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if request_id:
            ensure_ws(request_id, ev.get("url"))

    def on_ws_request(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if not request_id:
            return
        ws = ensure_ws(request_id)
        req = ev.get("request") or {}
        ws["handshake_request_headers"] = req.get("headers")
        ws["handshake_request_timestamp"] = int(time.time() * 1000)

    def on_ws_response(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if not request_id:
            return
        ws = ensure_ws(request_id)
        resp = ev.get("response") or {}
        ws.update({
            "status": resp.get("status"),
            "status_text": resp.get("statusText"),
            "handshake_response_headers": resp.get("headers"),
            "handshake_response_timestamp": int(time.time() * 1000),
        })

    def remember_ws_frame(ev: dict, direction: str) -> None:
        request_id = str(ev.get("requestId") or "")
        if not request_id:
            return
        ws = ensure_ws(request_id)
        frame = ev.get("response") or {}
        payload = frame.get("payloadData")
        if payload is None:
            payload = ""
        browser_manager._websocket_frame_counter += 1
        if direction == "sent":
            ws["sent"] = int(ws.get("sent") or 0) + 1
        else:
            ws["received"] = int(ws.get("received") or 0) + 1
        browser_manager._websocket_messages.append({
            "frame_index": browser_manager._websocket_frame_counter - 1,
            "wsid": ws["wsid"],
            "request_id": request_id,
            "url": ws.get("url"),
            "direction": direction,
            "opcode": frame.get("opcode"),
            "mask": frame.get("mask"),
            "payload": payload,
            "payload_preview": str(payload)[:240],
            "size": len(str(payload)),
            "timestamp": int(time.time() * 1000),
            "cdp_timestamp": ev.get("timestamp"),
        })

    def on_ws_closed(ev: dict) -> None:
        request_id = str(ev.get("requestId") or "")
        if request_id and request_id in browser_manager._websockets:
            browser_manager._websockets[request_id]["closed"] = True
            browser_manager._websockets[request_id]["closed_at"] = int(time.time() * 1000)

    session.on("Network.requestWillBeSent", on_request)
    session.on("Network.responseReceived", on_response)
    session.on("Network.loadingFinished", on_finished)
    session.on("Network.loadingFailed", on_failed)
    session.on("Network.webSocketCreated", on_ws_created)
    session.on("Network.webSocketWillSendHandshakeRequest", on_ws_request)
    session.on("Network.webSocketHandshakeResponseReceived", on_ws_response)
    session.on("Network.webSocketFrameSent", lambda ev: remember_ws_frame(ev, "sent"))
    session.on("Network.webSocketFrameReceived", lambda ev: remember_ws_frame(ev, "received"))
    session.on("Network.webSocketClosed", on_ws_closed)
    await session.send("Network.enable", {"maxTotalBufferSize": 100_000_000, "maxResourceBufferSize": 10_000_000})
    browser_manager._cdp_network_enabled_sessions.add(session_key)
