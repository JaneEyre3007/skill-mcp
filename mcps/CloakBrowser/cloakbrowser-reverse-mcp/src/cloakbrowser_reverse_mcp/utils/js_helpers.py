from __future__ import annotations

from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parents[1] / "hooks"


def read_hook(name: str) -> str:
    return (HOOKS_DIR / name).read_text(encoding="utf-8")


def _js_bool(value: bool) -> str:
    return "true" if value else "false"


def render_trace_template(
    *,
    function_path: str,
    max_captures: int,
    log_args: bool,
    log_return: bool,
    log_stack: bool,
) -> str:
    return read_hook("trace_template.js").replace("{{FUNCTION_PATH}}", function_path).replace(
        "{{MAX_CAPTURES}}", str(max_captures)
    ).replace("{{LOG_ARGS}}", _js_bool(log_args)).replace(
        "{{LOG_RETURN}}", _js_bool(log_return)
    ).replace("{{LOG_STACK}}", _js_bool(log_stack))


def render_persistent_trace_template(**kwargs) -> str:
    return render_trace_template(**kwargs)
