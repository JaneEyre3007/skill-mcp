from __future__ import annotations

from ..server import browser_manager, mcp
from ..utils.response_fmt import error_response


@mcp.tool()
async def verify_signer_offline(signer_code: str, samples: list[dict], compare_params: list[str] | None = None) -> dict:
    """Run a candidate JS signer against samples in the page context."""
    try:
        page = await browser_manager.get_active_page()
        details = await page.evaluate("""async ({code, samples, compareParams}) => {
          const fn = (new Function('return (' + code + ');'))();
          const details = []; let passed = 0;
          for (const sample of samples) {
            let computed, ok = true, err = null;
            try { computed = await fn(sample.input); } catch(e) { computed = {}; ok = false; err = e.message; }
            const params = compareParams || Object.keys(sample.expected || {});
            const diffs = [];
            for (const p of params) { if (String((computed||{})[p]) !== String((sample.expected||{})[p])) { ok = false; diffs.push({param:p, expected:(sample.expected||{})[p], actual:(computed||{})[p]}); } }
            if (ok) passed++;
            details.push({id: sample.id, ok, error: err, computed, diffs});
          }
          return {details, passed};
        }""", {"code": signer_code, "samples": samples, "compareParams": compare_params})
        total = len(samples)
        return {"total_samples": total, "passed": details["passed"], "failed": total - details["passed"], "pass_rate": details["passed"] / total if total else 0, "details": details["details"], "first_divergence": next((d for d in details["details"] if not d["ok"]), None)}
    except Exception as exc:
        return error_response(exc)
