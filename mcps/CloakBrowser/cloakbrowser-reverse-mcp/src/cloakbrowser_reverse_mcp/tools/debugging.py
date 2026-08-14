from __future__ import annotations

import json as _json
import re as _re

from ..server import browser_manager, mcp


def _build_error_response(error_msg: str) -> dict:
    hint = None
    if "unexpected token" in error_msg.lower() or "expected expression" in error_msg.lower():
        hint = "Wrap statements in an IIFE: (() => { var x = 1; return x; })()"
    elif "timeout" in error_msg.lower():
        hint = "The page or expression timed out; simplify the expression or enable await_promise."
    return {"type": "error", "error": error_msg, "hint": hint}


@mcp.tool()
async def evaluate_js(expression: str, await_promise: bool = True) -> dict:
    """Execute a JavaScript expression in the active page."""
    def clean_str(value):
        warns = []
        if not isinstance(value, str):
            return value, warns
        if value.startswith("\ufeff"):
            value = value.lstrip("\ufeff")
            warns.append("stripped BOM")
        stripped = value.strip()
        if stripped != value and stripped:
            value = stripped
            warns.append("trimmed whitespace")
        return value, warns

    def smart_parse(value, warns):
        if not isinstance(value, str) or value.lstrip()[:1] not in '[{"':
            return value, None
        try:
            return _json.loads(value), None
        except Exception as first:
            cleaned = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
            if cleaned != value:
                try:
                    warns.append("stripped control chars")
                    return _json.loads(cleaned), None
                except Exception:
                    pass
            return value, str(first)[:100]

    try:
        page = await browser_manager.get_active_page()
        wrapper = """async ({expression, awaitPromise}) => {
          try {
            const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
            const Fn = awaitPromise ? AsyncFunction : Function;
            const r = await (new Fn('return (' + expression + ');'))();
            const t = typeof r;
            if (r === undefined || r === null) return {result:null, type:t, is_undefined:r===undefined};
            if (t === 'symbol') return {result:null, type:'symbol', symbol_desc:r.toString()};
            if (t === 'object' || t === 'function') {
              try { return {result: JSON.parse(JSON.stringify(r)), type:t}; }
              catch(e) { return {result:String(r), type:t, serialization_warning:e.message}; }
            }
            return {result:r, type:t};
          } catch(e) { return {error:e.message, type:'error'}; }
        }"""
        raw = await page.evaluate(wrapper, {"expression": expression, "awaitPromise": await_promise})
        if isinstance(raw, dict) and "error" in raw:
            return _build_error_response(raw["error"])
        value, warnings = clean_str(raw.get("result") if isinstance(raw, dict) else raw)
        value, parse_error = smart_parse(value, warnings)
        result = {"type": "json" if parse_error is None and not isinstance(value, str) else "primitive", "value": value}
        if warnings:
            result["warnings"] = warnings
        if parse_error:
            result["parse_warning"] = parse_error
        if isinstance(raw, dict) and raw.get("serialization_warning"):
            result.setdefault("warnings", []).append(raw["serialization_warning"])
        return result
    except Exception as exc:
        return _build_error_response(str(exc))
