from __future__ import annotations

from typing import Literal

from ..server import browser_manager, mcp
from ..utils.response_fmt import error_response


@mcp.tool()
async def cookies(action: Literal["get", "set", "delete"], domain: str | None = None, cookies_list: list[dict] | None = None, name: str | None = None) -> list | dict:
    """Cookie management."""
    try:
        page = await browser_manager.get_active_page()
        ctx = page.context
        if action == "get":
            items = await ctx.cookies()
            if domain:
                items = [c for c in items if domain in c.get("domain", "")]
            return items
        if action == "set":
            await ctx.add_cookies(cookies_list or [])
            return {"status": "set", "count": len(cookies_list or [])}
        if action == "delete":
            current = await ctx.cookies()
            keep = []
            delete_count = 0
            for c in current:
                hit = (name is None or c.get("name") == name) and (domain is None or domain in c.get("domain", ""))
                if hit:
                    delete_count += 1
                else:
                    keep.append(c)
            await ctx.clear_cookies()
            if keep:
                await ctx.add_cookies(keep)
            return {"status": "deleted", "count": delete_count}
        return error_response("unknown action")
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def get_storage(storage_type: Literal["local", "session"] = "local") -> dict:
    """Get localStorage or sessionStorage."""
    try:
        page = await browser_manager.get_active_page()
        obj = "localStorage" if storage_type == "local" else "sessionStorage"
        return await page.evaluate("""(obj) => {
          const s = window[obj]; const out = {};
          for (let i=0;i<s.length;i++) { const k = s.key(i); out[k] = s.getItem(k); }
          return out;
        }""", obj)
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def export_state(save_path: str) -> dict:
    """Export cookies and storage state to JSON."""
    try:
        page = await browser_manager.get_active_page()
        await page.context.storage_state(path=save_path)
        return {"status": "saved", "path": save_path}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def import_state(state_path: str) -> dict:
    """Create a new context from a Playwright storage_state file."""
    try:
        await browser_manager._ensure_browser()
        if browser_manager.browser is None:
            return error_response("browser not running")
        ctx = await browser_manager.browser.new_context(storage_state=state_path)
        name = f"ctx{len(browser_manager.contexts)}"
        browser_manager.contexts[name] = ctx
        page = await ctx.new_page()
        browser_manager._attach_listeners(page)
        browser_manager.pages[name] = page
        browser_manager.active_page_name = name
        return {"status": "imported", "context": name}
    except Exception as exc:
        return error_response(exc)
