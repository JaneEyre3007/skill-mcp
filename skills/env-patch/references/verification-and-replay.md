# Verification And Replay

Use this reference after `vm-browser-gap-diagnose.js` can load the target script. Loading success is only a syntax/runtime milestone; it does not prove the target sign, token, cookie, or encrypted field is accepted by the server.

## Function Verification

`success: true` is not functional success. `vm-browser-gap-diagnose.js` waits for a top-level returned Promise, but it cannot prove deferred timers, swallowed internal try/catch paths, or business callbacks produced the right sign/token. Verify the target behavior first in cache, then package the stable result into root-level `mod.js` and `main.js`.

Recommended flow:

1. Keep original target material under `js_reverse_cache/target/`.
2. Trigger the target behavior, such as an SDK init call, an XHR send, or a direct sign function call.
3. Check output shape against browser evidence, such as `a_bogus` length, prefix, segment count, encoding, or cookie name.
4. Move the verified environment into root `mod.js` and the callable JS entry into root `main.js`.
5. Use root `main.py` for HTTP replay.

For hook-style SDKs, keep this loading order:

```text
env modules -> fake XMLHttpRequest -> target JS -> capture hook -> init(config) -> trigger request
```

Important details:

1. Fake `XMLHttpRequest` must exist before loading the target JS if the target patches its prototype at load time.
2. Capture hooks such as `URLSearchParams.append` should be injected after the target JS if the target may replace native APIs with polyfills.
3. SDK `init` or `setup` parameters must be captured from the browser when they decide path matching or feature switches.

Common failures after load succeeds:

| Symptom | Likely Cause | Check |
|---|---|---|
| Sign is `undefined` | Missing crypto/performance dependency | Review selected env modules |
| Hook runs but does not sign | Missing SDK init params or path whitelist | Capture init params in the browser |
| Capture hook never fires | Hook injected before a target polyfill overwrote it | Move capture hook after target JS |
| JSVMP silently fails | Internal try/catch swallowed errors | Instrument known error exits cautiously |
| Sign length differs from browser | Environment fingerprint mismatch | Collect real browser seeds and patch minimally |

## Packaging A Callable Interface

After function verification passes, extract the environment and callable entry into root-level `mod.js` and `main.js`:

```javascript
// mod.js
'use strict';

function installEnv(profile) {
  globalThis.window = globalThis;
  globalThis.self = globalThis;
  globalThis.__profile__ = profile || {};
  // paste verified env patches here
}

installEnv();
module.exports = { installEnv };
```

```javascript
// main.js
'use strict';

const { installEnv } = require('./mod');

function getEncryptedParams(input) {
  installEnv(input.profile);
  // require/load target and call verified entry here
  return { sign: '' };
}

module.exports = getEncryptedParams;

if (require.main === module) {
  const input = JSON.parse(process.argv[2] || '{}');
  process.stdout.write(JSON.stringify(getEncryptedParams(input)));
}
```

Root `main.py` should send real HTTP requests and obtain encrypted parameters by executing `main.js`. Prefer `pyexecjs2` / `execjs`; fall back to `subprocess` when the package is missing or JS execution fails:

```python
def get_encrypted_params(payload):
    try:
        import execjs
        source = open('main.js', encoding='utf-8').read()
        # pyexecjs2 exposes the same Python module name: execjs.
        # With cwd set to the project root, require('./mod') can be resolved directly.
        ctx = execjs.compile(source, cwd='.')
        return ctx.call('getEncryptedParams', payload)
    except Exception:
        completed = subprocess.run(['node', 'main.js', json.dumps(payload, ensure_ascii=False)], text=True, capture_output=True, check=True)
        return json.loads(completed.stdout or '{}')
```

## HTTP Replay Checks

Validate in this order:

1. Format check: run `node main.js '{"url":"..."}'` and compare sign shape with browser evidence.
2. Python JS execution check: run `python main.py` and confirm it uses `pyexecjs2`/`execjs` or subprocess fallback successfully.
3. Request replay: send the real API request with the returned sign and the same browser-side request contract.

Python request rules:

1. Use `requests.get(base_url, params=params, cookies=cookies)` or the equivalent `curl_cffi.requests` call.
2. Keep `cookies` as a dict or cookie jar; do not stuff a raw cookie string into `headers["cookie"]` unless the target explicitly requires manual header replay.
3. Do not manually pre-quote the generated sign unless browser evidence proves the exact encoded form.
4. Rebuild time-sensitive sign/header/token values inside pagination or retry loops.

Minimal replay skeleton:

```python
from curl_cffi import requests

SIGN_SERVER = "http://localhost:3456/sign"


def get_sign(url):
    resp = requests.post(SIGN_SERVER, json={"url": url}, impersonate="chrome136")
    return resp.json().get("result") or None


headers = {"user-agent": "...", "referer": "..."}
cookies = {"ttwid": "...", "odin_tt": "..."}
params = {"aid": "6383", "sec_user_id": "...", "msToken": "..."}

base_url = "https://target.example/api/path/"
prepared = requests.Request("GET", base_url, params=params).prepare()
params["a_bogus"] = get_sign(prepared.url)

response = requests.get(base_url, headers=headers, cookies=cookies, params=params, impersonate="chrome136")
print(response.status_code, response.text)
```
