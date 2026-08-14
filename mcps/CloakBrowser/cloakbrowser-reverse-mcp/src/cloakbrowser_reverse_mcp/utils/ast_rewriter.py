from __future__ import annotations

from .js_rewriter import regex_rewrite


def ast_rewrite(*args, **kwargs):
    # CloakBrowser MCP keeps a conservative fallback; full AST rewriting can be
    # added later without changing the public instrumentation() API.
    return regex_rewrite(*args, **kwargs)
