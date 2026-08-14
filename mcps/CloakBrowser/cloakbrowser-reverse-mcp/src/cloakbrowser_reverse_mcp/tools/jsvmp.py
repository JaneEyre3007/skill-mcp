from __future__ import annotations

import json
from typing import Literal

from ..server import browser_manager, mcp
from ..utils.js_helpers import read_hook
from ..utils.response_fmt import error_response


@mcp.tool()
async def hook_jsvmp_interpreter(script_url: str = "", persistent: bool = True, mode: Literal["proxy", "transparent"] = "proxy", track_calls: bool = True, track_props: bool = True, track_reflect: bool = True, proxy_objects: list[str] | None = None, max_entries: int = 10000) -> dict:
    """Install a page-level JSVMP runtime probe."""
    try:
        page = await browser_manager.get_active_page()
        if mode == "transparent":
            js = read_hook("jsvmp_transparent_hook.js").replace("{{SCRIPT_URL}}", script_url).replace("{{MAX_ENTRIES}}", str(max_entries))
        else:
            if proxy_objects is None:
                proxy_objects = ["navigator", "screen", "history", "localStorage", "sessionStorage", "performance"]
            js = read_hook("jsvmp_hook.js").replace("{{SCRIPT_URL}}", script_url).replace("{{MAX_ENTRIES}}", str(max_entries)).replace("{{TRACK_CALLS}}", "true" if track_calls else "false").replace("{{TRACK_PROPS}}", "true" if track_props else "false").replace("{{TRACK_REFLECT}}", "true" if track_reflect else "false").replace("'{{PROXY_OBJECTS}}'", json.dumps(json.dumps(proxy_objects)))
        if persistent:
            await browser_manager.add_persistent_script(f"jsvmp:{mode}:{script_url or 'all'}", js)
        already_loaded = page.url and page.url != "about:blank"
        await page.evaluate(js)
        result = {"status": "instrumented", "mode": mode, "persistent": persistent, "data_location": "window.__mcp_jsvmp_log"}
        if already_loaded:
            result["warnings"] = ["Hooks installed on an already-loaded page; reload or install before navigate for sync-loaded SDKs."]
        if mode == "proxy":
            result.setdefault("warnings", []).append("proxy mode is detectable by anti-bot scripts")
        return result
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def compare_env(properties: list[str] | None = None) -> dict:
    """Collect browser fingerprint environment values."""
    try:
        page = await browser_manager.get_active_page()
        return await page.evaluate("""(customProps) => {
          const result = {navigator:{}, screen:{}, canvas:{}, webgl:{}, audio:{}, timing:{}, misc:{}, custom:{}};
          for (const p of ['userAgent','platform','language','languages','hardwareConcurrency','deviceMemory','maxTouchPoints','vendor','cookieEnabled','webdriver']) { try { result.navigator[p] = {value: navigator[p], type: typeof navigator[p]}; } catch(e) { result.navigator[p] = {error:e.message}; } }
          for (const p of ['width','height','availWidth','availHeight','colorDepth','pixelDepth']) { try { result.screen[p] = {value: screen[p], type: typeof screen[p]}; } catch(e) { result.screen[p] = {error:e.message}; } }
          result.screen.devicePixelRatio = {value: devicePixelRatio, type:'number'};
          result.timing.timezone = {value: Intl.DateTimeFormat().resolvedOptions().timeZone, type:'string'};
          result.timing.timezoneOffset = {value: new Date().getTimezoneOffset(), type:'number'};
          try { const c=document.createElement('canvas'); const gl=c.getContext('webgl') || c.getContext('experimental-webgl'); const ext=gl&&gl.getExtension('WEBGL_debug_renderer_info'); if(gl&&ext){ result.webgl.vendor={value:gl.getParameter(ext.UNMASKED_VENDOR_WEBGL)}; result.webgl.renderer={value:gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)}; } } catch(e) { result.webgl.error=e.message; }
          for (const expr of customProps || []) { try { const v = Function('return (' + expr + ')')(); result.custom[expr] = {value: typeof v === 'object' ? JSON.stringify(v).slice(0,500) : String(v), type: typeof v}; } catch(e) { result.custom[expr] = {error:e.message}; } }
          return result;
        }""", properties or [])
    except Exception as exc:
        return error_response(exc)
