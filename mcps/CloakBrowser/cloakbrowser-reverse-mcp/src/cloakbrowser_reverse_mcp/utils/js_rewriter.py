from __future__ import annotations

import re

INSTRUMENT_RUNTIME = r"""
;(() => {
  if (window.__mcp_instrument_runtime) return;
  window.__mcp_instrument_runtime = true;
  window.__mcp_instrument_log = window.__mcp_instrument_log || [];
  window.__mcp_tap_get = function(tag, key, value) {
    try { window.__mcp_instrument_log.push({type:'tap_get', tag, key:String(key), value:String(value).slice(0,300), ts:Date.now()}); } catch(e) {}
    return value;
  };
  window.__mcp_tap_call = function(tag, key, fn, thisArg, args) {
    try { window.__mcp_instrument_log.push({type:'tap_call', tag, key:String(key), argc:args ? args.length : 0, ts:Date.now()}); } catch(e) {}
    try { return fn.apply(thisArg, args); }
    catch (e) { try { window.__mcp_instrument_log.push({type:'tap_call_err', tag, key:String(key), error:String(e), ts:Date.now()}); } catch(_) {} throw e; }
  };
})();
"""

ACORN_REWRITE_JS_TEMPLATE = ""


def regex_rewrite(
    src: str,
    tag: str,
    rewrite_member_access: bool = True,
    rewrite_calls: bool = True,
    max_rewrites: int = 20000,
    filter_property_names: list[str] | None = None,
    filter_object_names: list[str] | None = None,
) -> tuple[str, int]:
    """Conservative regex instrumentation for common obj.prop reads/calls.

    This is intentionally lighter than the Camoufox AST path. It is useful for
    targeted JSVMP probes when filters are provided.
    """
    edits = 0
    out = src
    prop_filter = set(filter_property_names or [])
    obj_filter = set(filter_object_names or [])

    if rewrite_member_access:
        pattern = re.compile(r"\b([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\b")

        def repl(match: re.Match[str]) -> str:
            nonlocal edits
            obj, prop = match.group(1), match.group(2)
            if obj in {"window", "document", "navigator", "screen", "performance", "localStorage", "sessionStorage"}:
                pass
            elif obj_filter and obj not in obj_filter:
                return match.group(0)
            elif not obj_filter:
                return match.group(0)
            if prop_filter and prop not in prop_filter:
                return match.group(0)
            if edits >= max_rewrites:
                return match.group(0)
            edits += 1
            return f"window.__mcp_tap_get({tag!r},{(obj + '.' + prop)!r},{obj}.{prop})"

        out = pattern.sub(repl, out)

    return INSTRUMENT_RUNTIME + "\n" + out, edits
