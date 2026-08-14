from __future__ import annotations

from typing import Literal

from ..server import mcp


@mcp.tool()
async def trace_property_access(duration: int = 10, mode: Literal["summary", "timeline", "sequence", "search"] = "summary", filter_object: str | None = None, search_query: str | None = None, limit: int = 1000, bucket_ms: int = 500, collect_values: bool = False, control_settle_timeout: float = 0.5, flush_timeout: float = 2.0, poll_interval: float = 0.05) -> dict:
    """CloakBrowser does not expose Camoufox-style engine-level property trace."""
    return {
        "error": "engine_trace_not_available_for_cloakbrowser",
        "message": "CloakBrowser currently has no public C++ property trace control files. Use hook_jsvmp_interpreter() or instrumentation(action='install') instead.",
    }


@mcp.tool()
async def list_trace_files(limit: int = 20) -> dict:
    return {"files": [], "total": 0, "message": "engine trace is not available for CloakBrowser"}


@mcp.tool()
async def query_trace_file(file_path: str, mode: Literal["summary", "timeline", "sequence", "search"] = "summary", filter_object: str | None = None, search_query: str | None = None, limit: int = 1000, bucket_ms: int = 500) -> dict:
    return {"error": "engine_trace_not_available_for_cloakbrowser"}
