from __future__ import annotations


def error_response(error: object) -> dict:
    return {"type": "error", "error": str(error)}
