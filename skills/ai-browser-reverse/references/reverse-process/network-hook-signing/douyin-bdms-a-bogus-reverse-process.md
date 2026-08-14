# Douyin BDMS a_bogus Firefox Reverse Process

Read this when the target is Douyin/ByteDance Web and the useful parameter is `a_bogus` appended to an XHR/fetch URL by BDMS or a similar security SDK.

## Goal

Use Firefox Reverse to collect browser-side evidence, run the BDMS URL mutation locally through Node environment patching, and replay the target API with Python. The completed case targeted:

- Page: `https://www.douyin.com/user/<sec_user_id>?from_tab_name=main`
- API: `https://www.douyin.com/aweme/v1/web/aweme/post/`
- Parameter: `a_bogus`

## Mode And Workspace

- Start in Delegate mode for broad reconnaissance and artifact capture.
- Use Direct-drive only after the worker settles or drifts, especially for precise diagnostics such as narrow `page_eval`, `jsvmp_trace`, `fs_read` slices, and `run_node` probes.
- Land code under the chosen task directory directly. Do not add an extra wrapper directory. Use `collector/`, `tests/`, `analysis/`, `scripts/`, `js_reverse_cache/`, `input/`, and `output/` under that chosen root.

## Evidence Path

1. Start `net_capture(action:"start", captureBody:true)` before navigation or reload.
2. Navigate to the user page and capture `/aweme/v1/web/aweme/post/` with `net_list` and `net_get(includeBody:true)`.
3. Record only masked secrets in notes. Keep raw cookies in local private files only when the user explicitly approves.
4. Use document-start hooks or `page_eval` to wrap `URLSearchParams.prototype.append`, XHR, and fetch. Log only when the key is `a_bogus` or the URL contains the target API.
5. Use `code_search` and `scripts_save(toWorkspace:true)` for `bdms_*.js`, `sdk-glue.js`, `captcha/index.js`, `runtime_bundler_*.js`, and `webmssdk.es5.js`.

Observed browser facts from the completed case:

- Browser target request returned `status_code: 0` and non-empty `aweme_list`.
- Browser URL contained `a_bogus`, `timestamp`, and `x-secsdk-web-signature`.
- `a_bogus` from browser requests was 192 characters in the sampled full request.
- `x-secsdk-web-signature` looked like a separate 32-hex signature and should not be conflated with `a_bogus`.
- `window.byted_acrawler.frontierSign(url)` returned a short `X-Bogus`-style value, not the target `a_bogus`.
- The useful call chain was XHR -> captcha intercept layer -> BDMS JSVMP -> `URLSearchParams.append("a_bogus", value)`.

## Locating The Real Init Path

Do not call `window.bdms.init()` with no arguments and treat failure as a runtime blocker. In the completed case it failed with a missing `boe` read because the config was absent.

Search business bundles and `sdk-glue.js` for `_SdkGlueInit`:

```text
_SdkGlueInit({ bdms: { paths: n, boe: e.isBoe || false } })
```

Then replay the relevant config locally:

```javascript
window.bdms.init({
  paths: ['/aweme/v1/web/aweme/post/'],
  boe: false,
  aid: 6383,
  pageId: 0,
})
```

After init, create an XHR for the protected API URL. BDMS mutates the URL by appending `a_bogus`; the clean boundary is the rewritten URL, not a clean exported `sign()` function.

## Node Environment Patch Lessons

The fastest way to break through the first BDMS JSVMP failure was not bytecode reversal. It was temporary dispatcher instrumentation.

Patch the dispatcher in a copy or in-memory string around the opcode call path:

```javascript
if ("function" != typeof n) {
  console.log("CALL_UNDEF", { pc: a, thisVal: d, callee: n, args: e })
  return f = 3, void(l = new TypeError(typeof n + " is not a function"))
}
```

Also instrument property reads on `window` to print missing properties. In the completed case the first real missing API was:

```text
GET_UNDEF_STATIC requestAnimationFrame
CALL_UNDEF ... thisIsWindow=true args=[function n]
```

Required patch categories:

- Force `globalThis.window` and mirror browser APIs onto both `globalThis` and `window`.
- Add `window.addEventListener`, `removeEventListener`, `dispatchEvent`, `requestAnimationFrame`, `cancelAnimationFrame`, `queueMicrotask`, `requestIdleCallback`, and `cancelIdleCallback`.
- Add XHR and fetch stubs that preserve `xhr._url` after `open()` because the local runner reads the rewritten URL there.
- Override `globalThis.navigator` even if it already exists. Node can expose a native navigator, and `if (!globalThis.navigator)` will leave the wrong fingerprint in place.
- Match the browser baseline where relevant: Firefox UA, language list, platform, screen dimensions, hardwareConcurrency, deviceMemory behavior, `window.innerWidth/innerHeight`, and top-level timer APIs.

Minimal local generation pattern:

```javascript
env.loadBdms()
window.bdms.init({ paths: ['/aweme/v1/web/aweme/post/'], boe: false, aid: 6383, pageId: 0 })
const xhr = new XMLHttpRequest()
xhr.open('GET', unsignedUrl, true)
xhr.send()
const signedUrl = xhr._url
```

## Verification Traps

- Local BDMS appending an `a_bogus` value is not enough. The server may still return HTTP 200 with an empty body.
- In the completed case, browser-captured `a_bogus` length was 192, while local fresh BDMS output was 184 after environment patching. Treat this as partial local generation until a fresh local signed URL gets a non-empty response.
- Do not mix signing order. Browser BDMS appends `a_bogus` before later fields such as `timestamp` and `x-secsdk-web-signature`; including those fields in the BDMS input can change the output.
- Python `requests` can fail on Douyin `content-encoding: br` with a brotli decode error. Send `Accept-Encoding: identity` for replay and debugging.
- A successful fallback replay with a browser-captured complete signed URL proves the Python transport/session/header side, not fresh local signer acceptance.

## Python Replay Pattern

For immediate non-empty data when fresh local signer is not accepted yet:

1. Ask for explicit approval before using account-bound browser cookies.
2. Replay the browser-captured complete signed URL with `--no-resign` semantics.
3. Send the raw `Cookie` header and `uifid` header from the same browser request.
4. Send `Accept-Encoding: identity`.
5. Print the full upstream JSON to console if the user asks for console output; do not save response JSON unless requested.

Verified replay summary from the completed case:

```text
httpStatus: 200
status_code: 0
aweme_count: 21
contentLength: about 2 MB
```

## Code Landing Notes

Recommended files for this pattern:

- `collector/mod.js`: Node browser environment patch and `loadBdms()`.
- `collector/main.js`: `signUrl(url)` that loads BDMS, calls `bdms.init`, triggers XHR, and returns the rewritten URL.
- `collector/main.py`: Python replay wrapper. It may read `input/request.local.json` for local private config so users can run `python collector/main.py` without CLI arguments.
- `tests/fixed_vector.js`: verifies local BDMS appends a non-empty `a_bogus` and the signed URL has the parameter.
- `.gitignore`: ignore `input/*.local.json`, `input/*.local.txt`, and any response JSON if generated.

If the user wants console output, default `main.py` should print the full upstream JSON directly. Add a `--summary` flag only for concise output.

## Completion Claim Gate

Use precise language:

- Claim `local BDMS generation works` only after Node appends `a_bogus` locally.
- Claim `Python replay returns data` only after a non-empty JSON body with `status_code: 0` and `aweme_list` is observed.
- Claim `fresh local signer is accepted` only after a fresh local signed URL, not a browser-captured signed URL, returns non-empty data.

If the last gate fails, report the remaining gap as environment/signature mismatch and keep the browser-captured signed URL replay clearly separated as an operational fallback.
