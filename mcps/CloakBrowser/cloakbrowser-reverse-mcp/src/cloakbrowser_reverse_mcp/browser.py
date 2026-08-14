from __future__ import annotations

import asyncio
import fnmatch
import locale as _locale
import os
import random
import shutil
import socket
import subprocess
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import Any, Sequence

from playwright.async_api import (
    Browser as PlaywrightBrowser,
    BrowserContext,
    ConsoleMessage,
    Page,
    Request as PWRequest,
    Response as PWResponse,
    async_playwright,
)

from .binary_manager import browser_root as managed_browser_root, binary_info as managed_binary_info, binary_path as managed_binary_path, download_or_update
from .geoip import is_socks_proxy, normalize_proxy_url, resolve_exit_ip, resolve_proxy_geo_with_ip
from .human import HumanConfig, resolve_config as resolve_human_config

MAX_LOG_SIZE = 3000
MAX_BODY_SIZE = 300_000


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _browser_root() -> Path:
    return managed_browser_root()


def _default_binary_path() -> Path:
    return managed_binary_path()


def _detect_system_locale() -> str:
    loc = _locale.getlocale()[0]
    if loc:
        return loc.replace("_", "-")
    return "zh-CN"


def _arg_key(arg: str) -> str:
    return arg.split("=", 1)[0]


def _dedupe_args(args: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for arg in args:
        seen[_arg_key(arg)] = arg
    return list(seen.values())


def _build_stealth_args(
    *,
    fingerprint_seed: str | None,
    locale: str | None,
    timezone: str | None,
    proxy: str | None,
    headless: bool,
    window_width: int,
    window_height: int,
    block_images: bool,
    block_webrtc: bool,
    extension_paths: list[str] | None,
    extra_args: list[str] | None,
) -> list[str]:
    seed = fingerprint_seed or str(random.randint(10000, 99999))
    args = [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-popup-blocking",
        "--disable-dev-shm-usage",
        "--metrics-recording-only",
        "--ignore-gpu-blocklist",
        f"--fingerprint={seed}",
        "--fingerprint-platform=windows",
        f"--fingerprint-screen-width={window_width}",
        f"--fingerprint-screen-height={window_height}",
        f"--window-size={window_width},{window_height}",
    ]
    if headless:
        # Chromium's newer headless path is closer to headed mode.
        args.append("--headless=new")
    if locale:
        args.extend([f"--lang={locale}", f"--fingerprint-locale={locale}"])
    if timezone:
        args.append(f"--fingerprint-timezone={timezone}")
    if proxy:
        args.append(f"--proxy-server={normalize_proxy_url(proxy)}")
    if block_images:
        args.append("--blink-settings=imagesEnabled=false")
    if block_webrtc:
        args.extend([
            "--disable-webrtc",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        ])
    if extension_paths:
        ext_val = ",".join(str(Path(p).resolve()) for p in extension_paths)
        args.extend([f"--load-extension={ext_val}", f"--disable-extensions-except={ext_val}"])
    if extra_args:
        args.extend(extra_args)
    return _dedupe_args(args)


class BrowserManager:
    default_config: dict[str, Any] = {}

    def __init__(self) -> None:
        self.browser: PlaywrightBrowser | None = None
        self.contexts: dict[str, BrowserContext] = {}
        self.pages: dict[str, Page] = {}
        self.active_page_name: str | None = None
        self._playwright: Any = None
        self._process: subprocess.Popen | None = None
        self._cdp_port: int | None = None
        self._cdp_url: str | None = None
        self._user_data_dir: str | None = None
        self._owned_user_data_dir = False
        self._launch_config: dict[str, Any] = {}
        self._console_logs: deque[dict] = deque(maxlen=MAX_LOG_SIZE)
        self._network_requests: deque[dict] = deque(maxlen=MAX_LOG_SIZE)
        self._request_id_counter = 0
        self._capturing = False
        self._capture_pattern = "**/*"
        self._capture_body = False
        self._persistent_scripts: list[dict[str, str]] = []
        self._init_scripts: list[str] = []
        self._persistent_traces: dict[str, list] = {}
        self._nav_responses: list[dict] = []
        self._route_handlers: dict[str, Any] = {}
        self._cdp_sessions: dict[str, Any] = {}
        self._cdp_scripts: dict[str, dict] = {}
        self._cdp_source_cache: dict[str, str] = {}
        self._cdp_debugger_enabled_sessions: set[int] = set()
        self._cdp_network_enabled_sessions: set[int] = set()
        self._cdp_breakpoints: dict[str, dict] = {}
        self._cdp_network_requests: dict[str, dict] = {}
        self._cdp_network_order: deque[str] = deque(maxlen=MAX_LOG_SIZE)
        self._websockets: dict[str, dict] = {}
        self._websocket_messages: deque[dict] = deque(maxlen=MAX_LOG_SIZE)
        self._websocket_id_counter = 0
        self._websocket_frame_counter = 0
        self._source_maps: dict[str, dict] = {}
        self._paused_info: dict | None = None
        self._humanize = False
        self._human_config: HumanConfig = resolve_human_config("default")
        self._cursor_state: dict[str, float | bool] = {"x": 0.0, "y": 0.0, "initialized": False}

    async def launch(self, config: dict | None = None) -> dict:
        if self.browser is not None:
            return {
                "status": "already_running",
                "cdp_url": self._cdp_url,
                "active_page": self.active_page_name,
                "pages": {name: p.url for name, p in self.pages.items()},
                "captured_requests_count": len(self._network_requests),
                "persistent_scripts_count": len(self._persistent_scripts),
            }

        cfg = {**self.default_config, **(config or {})}
        env_binary = (os.environ.get("CLOAKBROWSER_BINARY_PATH") or "").strip().strip('"')
        binary_path = Path(cfg.get("executable_path") or env_binary or _default_binary_path())
        update_result = None
        if cfg.get("auto_update"):
            update_result = download_or_update(force=False)
        if not binary_path.exists():
            update_result = download_or_update(force=True)
        if not binary_path.exists():
            raise FileNotFoundError(f"CloakBrowser binary not found: {binary_path}")

        headless = bool(cfg.get("headless", True))
        locale = cfg.get("locale", "auto")
        if locale == "auto":
            locale = _detect_system_locale()
        timezone = cfg.get("timezone")
        window_width = int(cfg.get("window_width", 1920))
        window_height = int(cfg.get("window_height", 1080))
        viewport_width = int(cfg.get("viewport_width", window_width))
        viewport_height = int(cfg.get("viewport_height", max(1, window_height - 133)))
        proxy = cfg.get("proxy")
        if isinstance(proxy, dict):
            proxy = proxy.get("server")
        if proxy:
            proxy = normalize_proxy_url(str(proxy))

        exit_ip = None
        geoip_errors: list[str] = []
        if cfg.get("geoip") and proxy:
            try:
                geo_tz, geo_locale, exit_ip = resolve_proxy_geo_with_ip(proxy)
                if not timezone:
                    timezone = geo_tz
                if locale in (None, "auto") and geo_locale:
                    locale = geo_locale
            except Exception as exc:
                geoip_errors.append(str(exc))

        profile_dir = cfg.get("user_data_dir")
        if profile_dir:
            user_data_dir = str(Path(profile_dir).resolve())
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
            self._owned_user_data_dir = False
        elif cfg.get("persistent_profile", True):
            user_data_dir = str((_browser_root() / "profiles" / "default").resolve())
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
            self._owned_user_data_dir = False
        else:
            user_data_dir = tempfile.mkdtemp(prefix="cloakbrowser-reverse-")
            self._owned_user_data_dir = True

        port = int(cfg.get("remote_debugging_port") or _find_free_port())
        extra_args = list(cfg.get("args") or [])
        if proxy:
            for i, arg in enumerate(list(extra_args)):
                if arg == "--fingerprint-webrtc-ip=auto":
                    if exit_ip is None:
                        exit_ip = resolve_exit_ip(proxy)
                    if exit_ip:
                        extra_args[i] = f"--fingerprint-webrtc-ip={exit_ip}"
                    else:
                        extra_args.remove(arg)
        if exit_ip and not any(a.startswith("--fingerprint-webrtc-ip") for a in extra_args):
            extra_args.append(f"--fingerprint-webrtc-ip={exit_ip}")

        self._humanize = bool(cfg.get("humanize", False))
        self._human_config = resolve_human_config(cfg.get("human_preset", "default"), cfg.get("human_config"))
        self._cursor_state = {"x": 0.0, "y": 0.0, "initialized": False}

        args = _build_stealth_args(
            fingerprint_seed=cfg.get("fingerprint_seed"),
            locale=locale,
            timezone=timezone,
            proxy=proxy,
            headless=headless,
            window_width=window_width,
            window_height=window_height,
            block_images=bool(cfg.get("block_images", False)),
            block_webrtc=bool(cfg.get("block_webrtc", False)),
            extension_paths=cfg.get("extension_paths"),
            extra_args=extra_args,
        )
        full_args = [
            str(binary_path),
            *args,
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={user_data_dir}",
            "about:blank",
        ]

        self._process = subprocess.Popen(full_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._cdp_port = port
        self._cdp_url = f"http://127.0.0.1:{port}"
        self._user_data_dir = user_data_dir
        self._launch_config = {
            "binary_path": str(binary_path),
            "headless": headless,
            "locale": locale,
            "timezone": timezone,
            "proxy": proxy,
            "window_width": window_width,
            "window_height": window_height,
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "user_data_dir": user_data_dir,
            "cdp_url": self._cdp_url,
            "args": args,
            "geoip_errors": geoip_errors or None,
            "webrtc_exit_ip": exit_ip,
            "humanize": self._humanize,
            "binary": managed_binary_info(),
            "update_result": update_result,
        }

        if not await self._wait_for_cdp(port):
            await self.close()
            raise RuntimeError("CloakBrowser CDP endpoint did not become ready")

        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.connect_over_cdp(self._cdp_url)
        self.browser = browser
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height}
        )
        self.contexts["default"] = ctx
        for script_info in self._persistent_scripts:
            await ctx.add_init_script(script=script_info["content"])
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        self._attach_listeners(page)
        self.pages["default"] = page
        self.active_page_name = "default"
        return {"status": "launched", **self._launch_config, "pages": list(self.pages.keys())}

    async def _wait_for_cdp(self, port: int, timeout: float = 12.0) -> bool:
        import urllib.request

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                await asyncio.sleep(0.15)
        return False

    async def _ensure_browser(self) -> None:
        if self.browser is None:
            await self.launch()

    def _attach_listeners(self, page: Page) -> None:
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
            except Exception as exc:
                self._console_logs.append({"level": "warn", "text": f"failed to parse trace payload: {exc}", "timestamp": int(time.time() * 1000)})
            return
        self._console_logs.append({
            "level": msg.type,
            "text": text,
            "timestamp": int(time.time() * 1000),
            "location": str(msg.location) if hasattr(msg, "location") else None,
        })

    def _on_request(self, req: PWRequest) -> None:
        if not self._capturing or not fnmatch.fnmatch(req.url, self._capture_pattern):
            return
        self._request_id_counter += 1
        self._network_requests.append({
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
        })

    def _on_response_async(self, resp: PWResponse) -> None:
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
        except Exception as exc:
            entry["response_body_error"] = str(exc)

    def _on_response_for_nav(self, resp: PWResponse) -> None:
        try:
            self._nav_responses.append({
                "url": resp.url,
                "status": resp.status,
                "resource_type": getattr(resp.request, "resource_type", None) if resp.request else None,
                "ts": int(time.time() * 1000),
            })
            self._nav_responses = self._nav_responses[-100:]
        except Exception:
            pass

    def reset_nav_responses(self) -> None:
        self._nav_responses = []

    async def add_persistent_script(self, name: str, content: str) -> None:
        for script in self._persistent_scripts:
            if script["name"] == name:
                script["content"] = content
                break
        else:
            self._persistent_scripts.append({"name": name, "content": content})
        for ctx in self.contexts.values():
            await ctx.add_init_script(script=content)

    def remove_persistent_script(self, name: str) -> bool:
        before = len(self._persistent_scripts)
        self._persistent_scripts = [s for s in self._persistent_scripts if s["name"] != name]
        return len(self._persistent_scripts) < before

    async def create_context(self, name: str, cookies: Sequence[dict[str, Any]] | None = None) -> dict:
        await self._ensure_browser()
        if self.browser is None:
            raise RuntimeError("No browser available after launch")
        ctx = await self.browser.new_context()
        if cookies:
            await ctx.add_cookies(cookies)  # type: ignore[arg-type]
        for script in self._persistent_scripts:
            await ctx.add_init_script(script=script["content"])
        self.contexts[name] = ctx
        page = await ctx.new_page()
        self._attach_listeners(page)
        self.pages[name] = page
        self.active_page_name = name
        return {"status": "created", "context": name}

    async def get_active_page(self) -> Page:
        await self._ensure_browser()
        if self.active_page_name and self.active_page_name in self.pages:
            return self.pages[self.active_page_name]
        raise RuntimeError("No active page available. Call launch_browser first.")

    async def new_cdp_session(self, page: Page | None = None) -> Any:
        await self._ensure_browser()
        page = page or await self.get_active_page()
        key = str(id(page))
        if key not in self._cdp_sessions:
            self._cdp_sessions[key] = await page.context.new_cdp_session(page)
        return self._cdp_sessions[key]

    def cdp_endpoint(self) -> str | None:
        return self._cdp_url

    async def close(self) -> dict:
        close_error = None
        for session in list(self._cdp_sessions.values()):
            try:
                await session.detach()
            except Exception:
                pass
        self._cdp_sessions.clear()
        if self.browser is not None:
            try:
                await self.browser.close()
            except Exception as exc:
                close_error = str(exc)
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                await asyncio.to_thread(self._process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        if self._owned_user_data_dir and self._user_data_dir:
            shutil.rmtree(self._user_data_dir, ignore_errors=True)

        self.browser = None
        self.contexts.clear()
        self.pages.clear()
        self.active_page_name = None
        self._playwright = None
        self._process = None
        self._cdp_port = None
        self._cdp_url = None
        self._user_data_dir = None
        self._console_logs.clear()
        self._network_requests.clear()
        self._request_id_counter = 0
        self._capturing = False
        self._nav_responses = []
        self._route_handlers.clear()
        self._cdp_scripts.clear()
        self._cdp_source_cache.clear()
        self._cdp_debugger_enabled_sessions.clear()
        self._cdp_network_enabled_sessions.clear()
        self._cdp_breakpoints.clear()
        self._cdp_network_requests.clear()
        self._cdp_network_order.clear()
        self._websockets.clear()
        self._websocket_messages.clear()
        self._websocket_id_counter = 0
        self._websocket_frame_counter = 0
        self._source_maps.clear()
        self._paused_info = None
        return {"status": "closed", "error": close_error}
