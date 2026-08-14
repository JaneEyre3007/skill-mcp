# Tool playbook

Use this file as the fast map from reverse-engineering task to tool choice.

## Preferred order

1. Capture one clean baseline request.
2. Find the real request.
3. Trace the initiator.
4. Diff the moving fields.
5. Add the narrowest runtime proof that still preserves the sample.
6. Reproduce one stable request.
7. Scale collection only after the first request is repeatable.

Prefer clean baselines, initiator stacks, and narrow proofs over broad hooks. Prefer focused source reads over loading giant bundles into context.

## Browser tier policy

Default to normal Chrome for ordinary JavaScript reverse work.

Use `chrome-devtools-mcp` as the first browser baseline for page flow, redirects, UI-triggered requests, and first-pass network capture.

Use `js-reverse-mcp` (starts as normal Chrome, switchable to CloakBrowser via `launch_browser({cloakBinaryPath: "..."})`) for all ordinary JS reverse work: initiator stacks, source search, breakpoints, wrapper tracing, WebSocket analysis, and runtime inspection.

Use CloakBrowser mode only after fingerprint or environment-sensitive verification evidence appears:

- normal Chrome hits unexplained fingerprint, webdriver, bot, risk-control, `403`, `412`, `429`, or challenge behavior
- page code reads or hashes `navigator`, `screen`, canvas, WebGL, audio, fonts, timing, plugins, permissions, WebRTC, or automation flags before the protected request
- fixed-input output depends on browser environment values that normal Chrome cannot reproduce cleanly
- hooks or breakpoints perturb the target and a stealthier baseline is needed to separate observer effect from protocol logic

When CloakBrowser mode is activated via `launch_browser`, state the exact evidence that justified the upgrade and keep final delivery browser-free.

## MCP capability matrix

Do not use every MCP tool by default. Pick the smallest capability that proves the current hypothesis, but know the full surface before declaring a blocker.

### Startup and hygiene

- `browser_binary_info` / `check_environment`: confirm browser type and mode.
- `launch_browser({cloakBinaryPath})`: switch browser at runtime—normal Chrome ↔ CloakBrowser—without restarting the MCP server. Also toggle `humanize` mode.
- `close_browser`: close the current browser and clear runtime overrides. Next tool call automatically relaunches with default (normal Chrome).
- `clear_network_requests`: clear stale request history before reproducing the action under study.
- `clear_site_data`: reset cookies, cache, and storage when testing replay assumptions or first-visit bootstraps.
- `get_page_info` / `select_page` / `select_frame`: verify the active target before evaluating script, setting breakpoints, or reading frame state.
- `reset_browser_state`: reset hooks, network captures, routes, and optionally cookies/storage when observer-effect is suspected or before starting a fresh analysis phase.

### Network and protocol evidence

- `list_network_requests`: index requests by method, resource type, URL, or Set-Cookie flow.
- `list_network_requests(reqid=..., outputFile=..., outputPart=...)`: export exact query params, request bodies, response bodies, headers, or full replay bundles. Save these exports under the generated project's root-level `js_reverse_cache/` during reconnaissance, then copy only stable proof artifacts into that same project's `analysis/` tree.
- `network_capture(action='start'|'stop'|'clear'|'status')`: control network capture lifecycle—start fresh capture after clearing stale requests, stop when the action under study is complete, or inspect capture state.
- `get_request_initiator`: tie the real request back to the call stack.
- `get_cdp_request_post_data` / `get_cdp_network_request`: use CDP-native request detail when the normal network summary omits exact POST data or body bytes.
- `intercept_request`: log, modify, block, or mock only after a clean baseline proves why interception is needed.

### Source, sourcemap, and debugger work

- `cdp_enable_debugger` / `cdp_status`: enable and verify debugger state before breakpoint-heavy work.
- `list_scripts` / `search_in_sources` / `get_script_source` / `save_script_source`: locate and preserve the smallest relevant source region.
- `list_source_maps` / `get_source_map` / `get_source_map_source`: recover original source names or readable sources when bundles advertise sourcemaps.
- `set_breakpoint_on_text` / `break_on_xhr` / `get_paused_info` / `evaluate_on_paused` / `step` / `resume_debugger`: inspect mutation inputs at the exact execution boundary.
- `set_event_listener_breakpoint`: pause on click, submit, input, keydown, or other DOM events when the protocol transition starts from user interaction.

### Runtime hooks and instrumentation

- `hook_function` with `mode=trace`: trace stable helpers such as `JSON.stringify`, crypto wrappers, signer functions, or transport senders.
- `inject_hook_preset`: use narrow `xhr`, `fetch`, `crypto`, `websocket`, `cookie`, or `debugger_bypass` presets only after the baseline is saved.
- `hook_jsvmp_interpreter` / `instrumentation`: probe VM, JSVMP, or heavily obfuscated runtime access when ordinary source reading cannot expose the mutation point.
- `get_console_logs` / `list_console_messages`: collect runtime warnings, anti-debug logs, and decode errors before changing code.
- `remove_hooks` / `remove_breakpoint` / `remove_event_listener_breakpoint` / `remove_xhr_breakpoint`: clean up instrumentation after the evidence is captured. Call these before re-baselining when hooks perturb the target.
- `set_cdp_skip_all_pauses`: suppress debugger statements and breakpoints globally—useful as an alternative to `debugger_bypass` when the page fires its own `debugger;` traps.
- `list_breakpoints`: review active code and XHR breakpoints before a new analysis phase; stale breakpoints can cause unwanted pauses.

### State and environment evidence

- `cookies` / `get_storage`: inspect cookie and storage state only as protocol evidence, not as final collector dependencies.
- `export_state` / `import_state`: preserve a known-good browser state for controlled replay experiments; never ship it as the final solution.
- `compare_env`: sample navigator, screen, WebGL, canvas, timing, or custom environment values when fingerprint branches are suspected.
- `evaluate_script(mainWorld=true)`: inspect page-owned globals, webpack caches, SDK state, bootstrap objects, and exposed helper outputs.
- `evaluate_js`: lighter-weight alternative to `evaluate_script` that takes a raw JS expression string—convenient for quick property probes.
- `launch_browser({humanize: true/false})`: toggle human-like interaction mode at runtime without restarting. When enabled, `click`, `type_text`, and `human_scroll` use Bezier-curve mouse movement, variable typing delays, and burst scrolling to evade automation detection. Enable only when page interaction is required for evidence gathering and the target is sensitive to synthetic input patterns.

### WebSocket and stream protocols

- `websocket_capture`: clear or verify WebSocket capture before a fresh transcript.
- `list_websockets`: discover all active WebSocket connections and filter by URL before selecting one for deep inspection.
- `get_websocket_connection(wsid=..., include_messages=...)`: get connection metadata plus recent message samples for a specific WebSocket.
- `get_websocket_messages(analyze=true)`: group frames by family before decoding payload semantics.
- `get_websocket_messages(frameIndex=..., show_content=true)`: freeze one exact auth, heartbeat, ack, or business frame for local replay.

### Verification and heavy diagnostics

- `verify_signer_offline`: compare a candidate local signer against captured fixed-input samples before adding live traffic.
- `trace_property_access`: engine-level (C++/SpiderMonkey) property access tracing—reveals exactly which `navigator`, `screen`, `canvas`, `WebGL`, `audio`, `font`, `timing`, or plugin properties the target reads. The primary fingerprint analysis tool for CloakBrowser escalation.
- `list_trace_files` / `query_trace_file`: inspect post-hoc trace data saved by `trace_property_access` from a previous session.
- `start_cpu_profile` / `stop_cpu_profile`: locate hot signer, VM, or decoder paths when source search is too noisy.
- `capture_heap_snapshot`: use only for deep object-retention or hidden-state investigations; it is not part of the normal protocol path.
- `take_screenshot` / `take_snapshot` / `capture_screenshot_cdp`: preserve UI or challenge evidence when page state affects protocol interpretation.

### Escalation rule

All capabilities are available on `js-reverse-mcp` which starts in normal Chrome. Switch to CloakBrowser at runtime via `launch_browser({cloakBinaryPath: "D:\\..."})` when the browser tier policy justifies it. Switch back with `launch_browser({cloakBinaryPath: ""})`. Keep `chrome-devtools-mcp` as the normal-Chrome UI and page-state baseline.

## Recon and network capture

### `js-reverse-mcp`

- `navigate` / `navigate_page`: open the target and follow the real landing URL
- `reload`: reload the current page preserving any hooks and instrumentation
- `list_network_requests`: list XHR, Fetch, document, script, and preflight traffic
- `list_network_requests(reqid=...)`: inspect the chosen request in full
- `get_request_initiator`: jump from request back to the caller stack
- `get_websocket_messages(analyze=true)`: group streaming traffic by message family
- `get_websocket_messages(frameIndex=...)`: inspect one exact frame in full
- `evaluate_script`: inspect `document.cookie`, `localStorage`, `sessionStorage`, or page globals when state matters
- `evaluate_js`: execute an arbitrary JavaScript expression string in the page and return the cleaned result

### `chrome-devtools`

- `navigate_page` / `new_page`: open the page when UI flow evidence matters
- `take_snapshot`: inspect page structure fast
- `wait_for`: wait on target text while triggering filters, search, or pagination
- `list_network_requests` and `get_network_request`: second source of truth when UI flow matters
- `take_screenshot`: capture evidence for hidden panels, captcha gates, or lazy regions

Use browser DevTools when DOM state matters. Use `js-reverse-mcp` when JavaScript runtime, request initiators, or hooks matter.

## Static JS analysis

- `list_scripts`: enumerate candidate bundles
- `search_in_sources`: search keywords across all loaded sources
- `get_script_source`: inspect the exact function neighborhood
- `save_script_source`: dump a full bundle locally when a file is too large to inspect in slices

Fallback recipes when you wanted a missing helper:

- no `find_in_script`: use `search_in_sources`, then `get_script_source`
- no automatic code summary: read the initiator stack first, then the smallest source slice around the mutation point
- no automatic crypto detector: search helper names, compare fixed inputs, and route to `references/crypto-patterns.md`
- no automatic deobfuscator: use `search_in_sources`, `save_script_source`, and `references/obfuscation-guide.md`

Keyword packs:

- request path: `"/api/"`, `"graphql"`, `"fetch("`, `"axios"`, `"XMLHttpRequest"`
- signer: `"sign"`, `"token"`, `"nonce"`, `"timestamp"`, `"trace"`, `"x-sign"`, `"beforeSend"`, `"ajaxSetup"`, `"requestId"`
- crypto: `"md5"`, `"sha"`, `"hmac"`, `"aes"`, `"rsa"`, `"crypto.subtle"`
- environment: `"navigator"`, `"canvas"`, `"webgl"`, `"performance"`, `"webdriver"`

## Dynamic validation

Start with a clean baseline. Then use initiator stacks and request diffs. Add runtime proofs only after you know why you are instrumenting.

### Baseline-first proof flow

1. capture one clean request and response pair
2. use `get_request_initiator` to jump from the request to the caller stack
3. use `search_in_sources` and `get_script_source` to inspect the smallest relevant code region
4. use `hook_function` with `mode=trace` when a named helper is stable enough to trace without poisoning the target
5. use `break_on_xhr` when you need to stop at the exact request boundary
6. use persistent `hook_function`, `inject_hook_preset`, or `instrumentation(action='install')` only for narrow boundary hooks that you can justify
7. if the target is verifier-gated or behavior-sensitive, remove invasive instrumentation and recapture a clean baseline the moment behavior changes

### Breakpoint tools

- `set_breakpoint_on_text`: best when the bundle is minified
- `get_paused_info`: inspect locals and scope
- `evaluate_script(frameIndex=...)`: print the exact pre-sign string, key, iv, or payload in the paused call frame
- `pause_or_resume`: resume execution after inspection
- `step(direction='over'|'into'|'out')`: only after you already know why you are pausing

## Session and environment handling

- `evaluate_script`: inspect `document.cookie`, storage values, bootstrap globals, or runtime helper outputs
- `evaluate_script(mainWorld=true)`: inspect page-owned globals such as webpack caches, SDK objects, or exposed bootstrap helpers
- persistent `hook_function`, `inject_hook_preset`, or `instrumentation(action='install')`: patch or observe a narrow environment branch before the page script runs
- `save_script_source`: preserve suspicious bundles for offline diffing when environment mismatch remains unclear

## Failure routing

- `403`, `412`, `429`: compare headers, cookies, sign freshness, and request pacing
- business error with normal `200`: compare payload assembly order and timestamp precision
- decrypt failure after a successful `200`: verify whether the runtime key/iv is transformed through a helper such as digit-pair-to-char before AES is applied
- empty data: verify pagination, filters, referer, login state, and cursor evolution
- occasional success: inspect one-time tokens, session refresh, or concurrent request coupling
- first request works but immediate replay fails: compare cookie mutation, in-memory timestamp slots, and whether a page refresh function must run before every request
- response gibberish: search for decrypt path, compression, protobuf, or msgpack
- hooked page fails but clean page works: suspect observer effect, remove invasive hooks, and recapture the baseline before deeper tracing

## Local helper scripts

Use the bundled local scripts when they are faster than re-deriving the same mechanics:

- `scripts/check_reverse_env.py`: confirm the local reverse stack quickly
- `scripts/crypto_fingerprint.py`: classify suspicious digest or alphabet outputs
- `scripts/protocol_diff.py`: compare captured requests or responses and surface the meaningful deltas
- `scripts/scaffold_reverse_project.py`: start a clean Python-first collector layout
