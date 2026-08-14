from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .browser import BrowserManager

mcp = FastMCP(
    "cloakbrowser-reverse-mcp",
    instructions=(
        "CloakBrowser Chromium reverse engineering MCP server. Provides anti-detect "
        "browser control, JavaScript hooks, network capture, source instrumentation, "
        "JSVMP probes, and Chromium CDP debugging helpers."
    ),
)

browser_manager = BrowserManager()

from .tools import navigation  # noqa: E402,F401
from .tools import debugging  # noqa: E402,F401
from .tools import network  # noqa: E402,F401
from .tools import websocket  # noqa: E402,F401
from .tools import storage  # noqa: E402,F401
from .tools import script_analysis  # noqa: E402,F401
from .tools import hooking  # noqa: E402,F401
from .tools import jsvmp  # noqa: E402,F401
from .tools import instrumentation  # noqa: E402,F401
from .tools import cdp_debugger  # noqa: E402,F401
from .tools import environment  # noqa: E402,F401
from .tools import verification  # noqa: E402,F401
from .tools import trace  # noqa: E402,F401
from .tools import binary  # noqa: E402,F401
