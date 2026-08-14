from __future__ import annotations

import argparse

from .browser import BrowserManager
from .server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="CloakBrowser Reverse Engineering MCP Server")
    parser.add_argument("--proxy", type=str, help="Proxy server URL, e.g. http://127.0.0.1:7890")
    parser.add_argument("--headless", action="store_true", help="Run headless by default")
    parser.add_argument("--locale", type=str, default="auto", help="Browser locale, e.g. zh-CN")
    parser.add_argument("--timezone", type=str, default=None, help="IANA timezone, e.g. Asia/Shanghai")
    parser.add_argument("--fingerprint", type=str, default=None, help="Default fixed fingerprint seed")
    args = parser.parse_args()

    BrowserManager.default_config = {
        "proxy": args.proxy,
        "headless": args.headless,
        "locale": args.locale,
        "timezone": args.timezone,
        "fingerprint_seed": args.fingerprint,
    }
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
