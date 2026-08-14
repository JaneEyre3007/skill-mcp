from __future__ import annotations

from typing import Literal

from ..server import browser_manager, mcp
from ..utils.js_helpers import read_hook, render_persistent_trace_template, render_trace_template
from ..utils.response_fmt import error_response


@mcp.tool()
async def hook_function(function_path: str, mode: Literal["intercept", "trace"] = "intercept", hook_code: str = "", position: Literal["before", "after", "replace"] = "before", non_overridable: bool = False, persistent: bool = False, log_args: bool = True, log_return: bool = True, log_stack: bool = False, max_captures: int = 50) -> dict:
    """Hook or trace a function path such as JSON.stringify."""
    if mode == "trace":
        js = render_persistent_trace_template(function_path=function_path, max_captures=max_captures, log_args=log_args, log_return=log_return, log_stack=log_stack) if persistent else render_trace_template(function_path=function_path, max_captures=max_captures, log_args=log_args, log_return=log_return, log_stack=log_stack)
        if persistent:
            await browser_manager.add_persistent_script(f"trace:{function_path}", js)
        page = await browser_manager.get_active_page()
        await page.evaluate(js)
        return {"status": "tracing", "target": function_path, "persistent": persistent}
    try:
        page = await browser_manager.get_active_page()
        escaped_hook = hook_code.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        freeze = ""
        if non_overridable:
            freeze = "try{Object.defineProperty(parent,fn,{value:parent[fn],writable:false,configurable:false});}catch(e){}"
        if position == "before":
            body = f"(function(){{ {escaped_hook} }}).call(__this); return _orig.apply(this,args);"
        elif position == "after":
            body = f"const __result=_orig.apply(this,args); (function(){{ {escaped_hook} }}).call(__this); return __result;"
        elif position == "replace":
            body = escaped_hook
        else:
            return error_response("invalid position")
        js = f"""(() => {{
          const path={function_path!r}; const parts=path.split('.'); let parent=window;
          for(let i=0;i<parts.length-1;i++){{ parent=parent[parts[i]]; if(!parent) return; }}
          const fn=parts[parts.length-1]; const _orig=parent[fn]; if(typeof _orig !== 'function' && {position!r} !== 'replace') return;
          const wrapper=function(...args){{ const __this=this; {body} }};
          if (_orig) wrapper.toString=()=>_orig.toString(); parent[fn]=wrapper; {freeze}
        }})();"""
        await page.evaluate(js)
        return {"status": "hooked", "target": function_path, "position": position}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def inject_hook_preset(preset: str, persistent: bool = True) -> dict:
    """Inject preset hook: xhr/fetch/crypto/websocket/debugger_bypass/cookie/runtime_probe."""
    mapping = {"xhr": "xhr_hook.js", "fetch": "fetch_hook.js", "crypto": "crypto_hook.js", "websocket": "websocket_hook.js", "debugger_bypass": "debugger_trap.js", "cookie": "cookie_hook.js", "runtime_probe": "runtime_probe.js"}
    if preset not in mapping:
        return error_response(f"Unknown preset: {preset}")
    try:
        js = read_hook(mapping[preset])
        if persistent:
            await browser_manager.add_persistent_script(f"preset:{preset}", js)
        page = await browser_manager.get_active_page()
        await page.evaluate(js)
        browser_manager._init_scripts.append(f"preset:{preset}")
        return {"status": "injected", "preset": preset, "persistent": persistent}
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
async def remove_hooks(keep_persistent: bool = False) -> dict:
    """Clear persistent hook registrations. In-page wrappers remain until reload."""
    count = 0
    if not keep_persistent:
        count = len(browser_manager._persistent_scripts)
        browser_manager._persistent_scripts.clear()
    return {"status": "cleared", "persistent_removed": count, "note": "reload page to drop in-page wrappers"}
