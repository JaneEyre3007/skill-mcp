from __future__ import annotations

import os
from typing import Literal

from ..server import browser_manager, mcp
from ..utils.response_fmt import error_response


@mcp.tool()
async def scripts(action: Literal["list", "get", "save"], url: str | None = None, save_path: str | None = None) -> dict | list:
    """List/get/save page scripts."""
    if action == "list":
        return await _list_scripts()
    if action == "get":
        if not url:
            return error_response("url is required")
        src = await _get_script_source(url)
        return {"url": url, "source": src, "length": len(src)}
    if action == "save":
        if not url or not save_path:
            return error_response("url and save_path are required")
        src = await _get_script_source(url)
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as fh:
            fh.write(src)
        return {"status": "saved", "path": save_path, "size": len(src)}
    return error_response("unknown action")


async def _list_scripts() -> list[dict]:
    try:
        page = await browser_manager.get_active_page()
        return await page.evaluate("""() => Array.from(document.scripts).map((s,i)=>({index:i, src:s.src||null, type:s.type||'text/javascript', is_module:s.type==='module', inline_length:s.src?0:(s.textContent||'').length, preview:s.src?null:(s.textContent||'').slice(0,200)}))""")
    except Exception as exc:
        return [error_response(exc)]


async def _get_script_source(url: str) -> str:
    page = await browser_manager.get_active_page()
    if url.startswith("inline:"):
        idx = int(url.split(":", 1)[1])
        return await page.evaluate("""idx => document.scripts[idx] ? document.scripts[idx].textContent : ''""", idx)
    return await page.evaluate("""async url => { const r = await fetch(url); return await r.text(); }""", url)


@mcp.tool()
async def search_code(keyword: str, script_url: str | None = None, context_chars: int = 200, context_lines: int = 3, max_results: int = 200) -> dict:
    """Search loaded scripts by substring."""
    try:
        if script_url:
            src = await _get_script_source(script_url)
            matches = []
            pos = 0
            while len(matches) < max_results:
                idx = src.find(keyword, pos)
                if idx < 0:
                    break
                matches.append({"offset": idx, "context": src[max(0, idx-context_chars):idx+len(keyword)+context_chars]})
                pos = idx + len(keyword)
            return {"script_url": script_url, "total_matches": len(matches), "matches": matches, "mode": "char"}
        page = await browser_manager.get_active_page()
        return await page.evaluate("""async ({keyword,maxResults}) => {
          const out = []; let total = 0; const scripts = Array.from(document.scripts);
          for (let i=0;i<scripts.length;i++) {
            let src = '', url = scripts[i].src || ('inline:' + i);
            try { src = scripts[i].src ? await (await fetch(scripts[i].src)).text() : scripts[i].textContent || ''; } catch(e) { continue; }
            let pos = 0;
            while (true) { const idx = src.indexOf(keyword, pos); if (idx < 0) break; total++; if (out.length < maxResults) out.push({script_url:url, offset:idx, context:src.slice(Math.max(0,idx-200), idx+keyword.length+200)}); pos = idx + keyword.length; }
          }
          return {total_matches:total, returned_matches:out.length, matches:out, truncated:total>out.length, mode:'char'};
        }""", {"keyword": keyword, "maxResults": max_results})
    except Exception as exc:
        return error_response(exc)
