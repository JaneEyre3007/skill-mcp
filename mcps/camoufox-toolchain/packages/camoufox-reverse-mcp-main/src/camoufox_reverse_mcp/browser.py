# 模块说明: 统一管理 Camoufox 浏览器生命周期、窗口行为、上下文和页面级监听器。
from __future__ import annotations

import asyncio
import os as _os
import platform
import time
from collections import deque
from typing import Any, Sequence

from playwright.async_api import Page, BrowserContext, Browser as PlaywrightBrowser, Request as PWRequest, Response as PWResponse, ConsoleMessage

MAX_LOG_SIZE = 2000
MAX_BODY_SIZE = 200_000


def detect_host_os() -> str:
    """Return the Camoufox os identifier matching the current host."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return "windows"


def detect_system_locale() -> str:
    """Best-effort detection of the host's locale (e.g. 'zh-CN')."""
    for var in ("LANG", "LC_ALL", "LC_MESSAGES"):
        val = _os.environ.get(var, "")
        if val and val not in ("C", "POSIX"):
            return val.split(".")[0].replace("_", "-")
    return "en-US"


def detect_work_area_size() -> tuple[int, int] | None:
    """Best-effort real OS work-area size for headful window sizing."""
    errors: list[str] = []
    try:
        if platform.system().lower() == "windows":
            import ctypes
            from ctypes import wintypes

            rect = wintypes.RECT()
            ok = ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
            if ok:
                width = int(rect.right - rect.left)
                height = int(rect.bottom - rect.top)
                if width > 0 and height > 0:
                    return width, height
    except Exception as e:
        errors.append(f"win32: {e}")

    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
        if monitors:
            mon = max(monitors, key=lambda m: int(m.width) * int(m.height))
            width = int(getattr(mon, "width", 0) or 0)
            height = int(getattr(mon, "height", 0) or 0)
            if width > 0 and height > 0:
                return width, height
    except Exception as e:
        errors.append(f"screeninfo: {e}")

    return None


def _positive_int(value: Any) -> int | None:
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return None
    return ivalue if ivalue > 0 else None


def maximize_browser_window() -> dict[str, Any]:
    """Maximize the visible Camoufox window at the OS window-manager level."""
    if platform.system().lower() != "windows":
        return {"supported": False, "reason": "system maximize is only implemented on Windows"}

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long),
            ]

        candidates: list[dict[str, Any]] = []
        callback_errors: list[str] = []
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        # 这里枚举系统顶层窗口,按标题过滤出 Camoufox 窗口,再选面积最大的一个。
        # 这样既能兼容多窗口场景,也避免依赖 Playwright 暴露原生 hwnd。
        def _callback(hwnd: int, _lparam: int) -> bool:
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "Camoufox" not in title:
                    return True
                rect = RECT()
                if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    return True
                width = int(rect.right - rect.left)
                height = int(rect.bottom - rect.top)
                if width <= 0 or height <= 0:
                    return True
                candidates.append({
                    "hwnd": hwnd,
                    "title": title,
                    "width": width,
                    "height": height,
                    "area": width * height,
                })
            except Exception as e:
                callback_errors.append(f"{int(hwnd)}: {e}")
            return True

        callback = enum_proc(_callback)
        user32.EnumWindows(callback, 0)
        if not candidates:
            return {
                "supported": True,
                "maximized": False,
                "reason": "Camoufox window not found",
                "callback_errors": callback_errors or None,
            }

        target = max(candidates, key=lambda item: item["area"])
        hwnd = target["hwnd"]
        ok = bool(user32.ShowWindowAsync(hwnd, 3))  # SW_MAXIMIZE
        try:
            user32.SetForegroundWindow(hwnd)
            foreground_error = None
        except Exception as e:
            foreground_error = str(e)
        return {
            "supported": True,
            "maximized": ok,
            "hwnd": int(hwnd),
            "title": target["title"],
            "window_before": [target["width"], target["height"]],
            "foreground_error": foreground_error,
            "callback_errors": callback_errors or None,
        }
    except Exception as e:
        return {"supported": True, "maximized": False, "error": str(e)}


class BrowserManager:
    """Manages the Camoufox browser lifecycle, contexts, and pages."""

    default_config: dict[str, Any] = {}

    def __init__(self) -> None:
        self.browser: PlaywrightBrowser | None = None
        self.contexts: dict[str, BrowserContext] = {}
        self.pages: dict[str, Page] = {}
        self.active_page_name: str | None = None
        self._cm: Any = None
        self._console_logs: deque[dict] = deque(maxlen=MAX_LOG_SIZE)
        self._network_requests: deque[dict] = deque(maxlen=MAX_LOG_SIZE)
        self._request_id_counter = 0
        self._capturing = False
        self._capture_pattern: str = "**/*"
        self._capture_body = False
        self._init_scripts: list[str] = []
        self._persistent_scripts: list[dict] = []
        self._persistent_traces: dict[str, list] = {}
        self._nav_responses: list[dict] = []  # 最近一次 navigate 记录到的响应链路
        self._route_handlers: dict[str, Any] = {}  # 已注册的 route handler 映射

    async def launch(self, config: dict | None = None) -> dict:
        """Launch the Camoufox browser with the given or default config."""
        if self.browser is not None:
            pages_info = {}
            for name, p in self.pages.items():
                try:
                    pages_info[name] = p.url
                except Exception:
                    pages_info[name] = "unknown"
            return {
                "status": "already_running",
                "active_page": self.active_page_name,
                "pages": pages_info,
                "contexts": list(self.contexts.keys()),
                "capturing": self._capturing,
            }

        from camoufox.async_api import AsyncCamoufox

        cfg = {**self.default_config, **(config or {})}

        kwargs: dict[str, Any] = {}

        if cfg.get("proxy"):
            kwargs["proxy"] = cfg["proxy"]

        os_type = cfg.get("os", "auto")
        host_os = detect_host_os()
        if os_type == "auto":
            os_type = host_os
        kwargs["os"] = os_type

        if cfg.get("humanize"):
            kwargs["humanize"] = True
        if cfg.get("geoip"):
            kwargs["geoip"] = True
        if cfg.get("block_images"):
            kwargs["block_images"] = True
        if cfg.get("block_webrtc"):
            kwargs["block_webrtc"] = True

        locale = cfg.get("locale", "auto")
        if locale == "auto":
            locale = detect_system_locale()
        kwargs["locale"] = locale

        headless = cfg.get("headless", False)
        kwargs["headless"] = headless

        window_width = _positive_int(cfg.get("window_width"))
        window_height = _positive_int(cfg.get("window_height"))
        if window_width and window_height:
            kwargs["window"] = (window_width, window_height)
        elif cfg.get("maximize") and not headless:
            work_area = detect_work_area_size()
            if work_area:
                kwargs["window"] = work_area

        exe_path = cfg.get("executable_path") or _os.environ.get("CAMOUFOX_EXECUTABLE_PATH")
        if exe_path:
            kwargs["executable_path"] = exe_path

        # Property trace support
        enable_trace = cfg.get("enable_trace", False)
        trace_value_cleanup_errors: list[str] = []
        property_trace_merge_errors: list[str] = []

        if enable_trace:
            from .property_trace import build_property_trace_config, ensure_dirs, cleanup_old_traces, cleanup_traces, CACHE_DIR
            import json as _json
            from functools import partial
            from camoufox.utils import launch_options as _cfx_launch_options
            ensure_dirs()
            cleanup_old_traces(keep_days=7)
            # Clean traces and values from previous sessions
            cleanup_traces()
            values_dir = CACHE_DIR / "values"
            if values_dir.exists():
                for f in values_dir.glob("*"):
                    try:
                        f.unlink()
                    except OSError as e:
                        trace_value_cleanup_errors.append(f"{f.name}: {e}")
            trace_config = build_property_trace_config()

            # Build from_options ourselves, then inject propertyTrace
            from_options = _cfx_launch_options(headless=headless, **{
                k: v for k, v in kwargs.items() if k != "headless"
            })
            env = from_options.get("env", {})
            # Merge propertyTrace into CAMOU_CONFIG_*
            merged = False
            for key in sorted(env.keys()):
                if key.startswith("CAMOU_CONFIG"):
                    try:
                        existing = _json.loads(env[key])
                        existing["propertyTrace"] = trace_config
                        env[key] = _json.dumps(existing)
                        merged = True
                        break
                    except (ValueError, TypeError):
                        property_trace_merge_errors.append(key)
            if not merged:
                env["CAMOU_CONFIG"] = _json.dumps({"propertyTrace": trace_config})
            env["MOZ_DISABLE_CONTENT_SANDBOX"] = "1"
            from_options["env"] = env

            # Pass pre-built from_options to skip launch_options() call
            kwargs["from_options"] = from_options

        self._cm = AsyncCamoufox(**kwargs)
        self.browser = await self._cm.__aenter__()

        if self.browser is None:
            raise RuntimeError("Camoufox launch returned no browser instance")
        context_options: dict[str, Any] = {}
        viewport_width = _positive_int(cfg.get("viewport_width"))
        viewport_height = _positive_int(cfg.get("viewport_height"))
        if viewport_width and viewport_height:
            context_options["viewport"] = {"width": viewport_width, "height": viewport_height}
        elif cfg.get("no_viewport") or (cfg.get("maximize") and not headless):
            context_options["no_viewport"] = True

        ctx = (
            self.browser.contexts[0]
            if self.browser.contexts
            else await self.browser.new_context(**context_options)
        )
        self.contexts["default"] = ctx

        if os_type != host_os:
            from .utils.js_helpers import get_font_fallback_script
            await ctx.add_init_script(get_font_fallback_script())

        for script_info in self._persistent_scripts:
            await ctx.add_init_script(script=script_info["content"])

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        self._attach_listeners(page)
        self.pages["default"] = page
        self.active_page_name = "default"

        maximize_result = None
        if cfg.get("maximize") and not headless:
            bring_to_front_error = None
            try:
                await page.bring_to_front()
            except Exception as e:
                bring_to_front_error = str(e)
            # 先让 Playwright 把页面置前,再调用系统级最大化。
            # 这样窗口按钮状态会变成真正的“最大化”,而不只是尺寸接近工作区。
            maximize_result = maximize_browser_window()
            if bring_to_front_error:
                maximize_result["bring_to_front_error"] = bring_to_front_error

        return {
            "status": "launched",
            "headless": headless,
            "os": os_type,
            "locale": locale,
            "pages": list(self.pages.keys()),
            "window": kwargs.get("window"),
            "context_options": context_options,
            "maximize_result": maximize_result,
            "trace_value_cleanup_errors": trace_value_cleanup_errors or None,
            "property_trace_merge_errors": property_trace_merge_errors or None,
        }

    async def _ensure_browser(self) -> None:
        """Lazy-launch the browser if not already running."""
        if self.browser is None:
            await self.launch()

    async def add_persistent_script(self, name: str, content: str) -> None:
        """Register a script that persists across all navigations via context-level injection."""
        for s in self._persistent_scripts:
            if s["name"] == name:
                s["content"] = content
                break
        else:
            self._persistent_scripts.append({"name": name, "content": content})
        for ctx in self.contexts.values():
            await ctx.add_init_script(script=content)

    def remove_persistent_script(self, name: str) -> bool:
        """Remove a persistent script by name. Returns True if found."""
        before = len(self._persistent_scripts)
        self._persistent_scripts = [s for s in self._persistent_scripts if s["name"] != name]
        return len(self._persistent_scripts) < before

    def _attach_listeners(self, page: Page) -> None:
        """Attach console, network, and trace-collection listeners to a page."""
        page.on("console", self._on_console)
        page.on("request", self._on_request)
        page.on("response", self._on_response_async)
        page.on("response", self._on_response_for_nav)

    def _on_console(self, msg: ConsoleMessage) -> None:
        text = msg.text
        if text and text.startswith("__MCP_TRACE__:"):
            try:
                import json
                payload = json.loads(text[len("__MCP_TRACE__:"):])
                path = payload.pop("__path__", "unknown")
                self._persistent_traces.setdefault(path, []).append(payload)
            except Exception as e:
                self._console_logs.append({
                    "level": "warn",
                    "text": f"failed to parse __MCP_TRACE__ console payload: {e}",
                    "timestamp": int(time.time() * 1000),
                    "location": str(msg.location) if hasattr(msg, "location") else None,
                })
            return

        self._console_logs.append({
            "level": msg.type,
            "text": text,
            "timestamp": int(time.time() * 1000),
            "location": str(msg.location) if hasattr(msg, "location") else None,
        })

    def _on_request(self, req: PWRequest) -> None:
        if not self._capturing:
            return
        import fnmatch
        if not fnmatch.fnmatch(req.url, self._capture_pattern):
            return
        self._request_id_counter += 1
        entry = {
            "id": self._request_id_counter,
            "url": req.url,
            "method": req.method,
            "resource_type": req.resource_type,
            "request_headers": dict(req.headers),
            "request_post_data": req.post_data,
            "timestamp": int(time.time() * 1000),
            "status": None,
            "response_headers": None,
            "response_body": None,
            "duration": None,
        }
        self._network_requests.append(entry)

    def _on_response_async(self, resp: PWResponse) -> None:
        """Handle response events, optionally capturing body asynchronously."""
        if not self._capturing:
            return
        for entry in reversed(self._network_requests):
            if entry["url"] == resp.url and entry["status"] is None:
                entry["status"] = resp.status
                entry["response_headers"] = dict(resp.headers)
                entry["duration"] = int(time.time() * 1000) - entry["timestamp"]
                if self._capture_body:
                    asyncio.ensure_future(self._fetch_response_body(resp, entry))
                break

    async def _fetch_response_body(self, resp: PWResponse, entry: dict[str, Any]) -> None:
        """Asynchronously fetch and store the response body."""
        try:
            body_bytes = await resp.body()
            try:
                body_text = body_bytes.decode("utf-8")
            except UnicodeDecodeError:
                body_text = body_bytes.decode("latin-1")
            if len(body_text) > MAX_BODY_SIZE:
                entry["response_body"] = body_text[:MAX_BODY_SIZE]
                entry["response_body_truncated"] = True
                entry["response_body_total_size"] = len(body_text)
            else:
                entry["response_body"] = body_text
        except Exception as e:
            entry["response_body"] = None
            entry["response_body_error"] = str(e)

    def _on_response_for_nav(self, resp: PWResponse) -> None:
        """Record every response during a navigation for final_status resolution."""
        try:
            self._nav_responses.append({
                "url": resp.url,
                "status": resp.status,
                "resource_type": getattr(resp.request, "resource_type", None) if resp.request else None,
                "ts": int(time.time() * 1000),
            })
            # Keep only the last 100
            if len(self._nav_responses) > 100:
                self._nav_responses = self._nav_responses[-100:]
        except Exception as e:
            self._console_logs.append({
                "level": "warn",
                "text": f"failed to record navigation response: {e}",
                "timestamp": int(time.time() * 1000),
                "location": None,
            })

    def reset_nav_responses(self) -> None:
        self._nav_responses = []

    async def create_context(self, name: str, cookies: Sequence[dict[str, Any]] | None = None) -> dict:
        """Create a new isolated browser context with optional cookies."""
        await self._ensure_browser()
        if self.browser is None:
            raise RuntimeError("No browser available after launch")
        ctx = await self.browser.new_context()
        if cookies:
            await ctx.add_cookies(cookies)  # type: ignore[arg-type]
        for script_info in self._persistent_scripts:
            await ctx.add_init_script(script=script_info["content"])
        self.contexts[name] = ctx
        page = await ctx.new_page()
        self._attach_listeners(page)
        self.pages[name] = page
        self.active_page_name = name
        return {"status": "created", "context": name}

    async def get_active_page(self) -> Page:
        """Get the currently active page, launching the browser if needed."""
        await self._ensure_browser()
        if self.active_page_name and self.active_page_name in self.pages:
            return self.pages[self.active_page_name]
        raise RuntimeError("No active page available. Call launch_browser first.")

    async def close(self) -> dict:
        """Close the browser and clean up all resources."""
        close_error = None
        if self._cm is not None:
            try:
                await self._cm.__aexit__(None, None, None)
            except Exception as e:
                close_error = str(e)
        self.browser = None
        self.contexts.clear()
        self.pages.clear()
        self.active_page_name = None
        self._cm = None
        self._console_logs.clear()
        self._network_requests.clear()
        self._request_id_counter = 0
        self._capturing = False
        self._capture_body = False
        self._init_scripts.clear()
        self._persistent_scripts.clear()
        self._persistent_traces.clear()
        self._nav_responses.clear()
        self._route_handlers.clear()
        result = {"status": "closed"}
        if close_error:
            result["close_error"] = close_error
        return result
