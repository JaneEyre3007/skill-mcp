# cloakbrowser-reverse-mcp

Self-contained MCP server for reverse engineering with the local CloakBrowser binary.

The browser binary is expected next to this MCP project by default:

```text
<browser_root>\chrome.exe
```

If the whole `CloakBrowser` folder is moved to another drive, updates follow that new folder automatically. If `CLOAKBROWSER_BINARY_PATH` is set, the folder containing that `chrome.exe` becomes the update target.

Start from opencode with `launch.bat`. The server exposes Playwright-based page control, hook/instrumentation tools, and Chromium CDP debugging helpers.

Official CloakBrowser wrapper behavior replicated locally:

- Core fingerprint args: `--fingerprint`, `--fingerprint-platform`, screen/window size, locale, timezone.
- Proxy normalization and `--proxy-server` launch path.
- `geoip=True` support with GeoLite2 database stored under `<browser_root>\.cloakbrowser-reverse\geoip`.
- WebRTC exit IP injection when `geoip=True` or `--fingerprint-webrtc-ip=auto` is used with a proxy.
- Persistent profile support under `<browser_root>\profiles`.
- Humanized click/type/scroll when `humanize=True`.
- Binary update tools update the folder containing the active `chrome.exe` directly. No global C: cache is used.

Binary update tools:

- `browser_binary_info()`
- `check_browser_update()`
- `update_browser_binary(version=None, force=False, close_running_browser=False)`

Reverse engineering helpers:

- CDP debugger: `cdp_enable_debugger()`, `search_cdp_sources()`, `set_breakpoint_on_text()`, `set_cdp_breakpoint()`, `list_cdp_breakpoints()`, `remove_cdp_breakpoint()`.
- CDP source reading: `list_cdp_scripts()`, `get_cdp_source()`, `save_cdp_script_source()`.
- Source maps: `list_source_maps()`, `get_source_map()`, `get_source_map_source()`.
- Puppeteer-style network initiator: `network_capture("start")`, `list_cdp_network_requests()`, `get_cdp_network_request()`, `get_cdp_request_initiator()`.
- WebSocket CDP capture: `websocket_capture("start")`, `list_websockets()`, `get_websocket_messages(analyze=True)`, `get_websocket_connection()`.

Engine-level property tracing is not available because CloakBrowser does not expose the Camoufox-specific trace control files.
