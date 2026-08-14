# Architecture

This file documents the env-patch skill architecture and runtime behavior.

## What This Is

An OpenCode skill for JS reverse-engineering sandbox environment patching (JS逆向沙箱补环境). Given an obfuscated JS file, it automates the cycle of: execute → diagnose missing browser APIs → patch environment → repeat until the script runs successfully.

This is a **skill directory** (not an npm project). It is self-contained with no external dependencies. At runtime, `$SKILL_DIR` resolves to the skill's installation path.

## Key Commands

```bash
# First diagnosis (no env modules)
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js <target.js>

# Diagnosis with env modules
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js --env bom/navigator-fingerprint.js,bom/web-crypto-stub.js,dom/document-dom-runtime.js <target.js>

# Multiple --env flags also work
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js --env bom/navigator-fingerprint.js --env dom/document-dom-runtime.js <target.js>

# Diagnosis with bundled profile seed
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js --profile default --env bom/navigator-fingerprint.js,bom/screen-fingerprint.js <target.js>

# Diagnosis with project-local profile seed
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js --profile-file js_reverse_cache/env/profile.json --env bom/navigator-fingerprint.js <target.js>

# Options: --timeout <ms> (default 60000), --profile <name>, --profile-file <path>, --quiet/-q
```

`vm-browser-gap-diagnose.js` outputs JSON to stdout with: `success`, `error`, `undefinedPaths`, `moduleLoadErrors`, `stats`, `consoleOutput`. If the target script returns a Promise, the tool waits for it and reports async rejection as `success: false`.

## Architecture

### Core Loading Chain

`vm-browser-gap-diagnose.js` creates a Node.js `vm` sandbox and loads modules in this order:

1. **`core/proxy-access-monitor.js`** — Always loaded. Provides `watch()` (Proxy wrapper that logs all property access), `safefunction()` (makes functions appear native via toString), `makeFunction()`, and `__ProxyMonitor__` global for log access.

2. **`core/profile-seed-manager.js`** — Loaded when `--profile` or `--profile-file` is supplied. Exposes `window.__profile__` and `window.__ProfileManager__` before any browser env module runs.

3. **`core/minimal-proxy-browser-env.js`** — Loaded **only when no `--env` modules are specified**. Creates basic proxy-wrapped browser globals (document, navigator, location, etc.) with `configurable: false`. When env modules are specified, this is skipped to avoid conflicts.

4. **User-specified env modules** — Loaded in the order given via `--env`. Paths are relative to `env/` directory.

5. **Target script** — Executed last. ProxyMonitor logs are cleared before this step so only the target's accesses are captured.

### Env Module Categories

All modules are IIFEs with `'use strict'`. They use `watch()` from `proxy-access-monitor.js` and `Object.defineProperty` to set globals.

- **`bom/`** — Browser Object Model: navigator fingerprint, URL state, screen fingerprint, web storage, window globals, crypto, performance, console, observers
- **`dom/`** — DOM: event constructors, document runtime, HTML element constructors
- **`webapi/`** — Web APIs: fetch/Request/Response, XMLHttpRequest, Blob/File/FormData, URL/URLSearchParams, network mock recorder, AudioContext, RTCPeerConnection, Worker/MessageChannel/BroadcastChannel
- **`encoding/`** — base64 codec (already built into `vm-browser-gap-diagnose.js`), TextEncoder/TextDecoder
- **`timer/`** — setTimeout/setInterval with ID management (`vm-browser-gap-diagnose.js` has basic stubs)
- **`ai-generated/`** — Custom patches for properties not covered by existing modules. Filename format: `<object>-<property>.js`
- **`templates/`** — Project delivery skeletons: root-level `mod.js`, `main.js`, and `main.py`.

### Recommended Project Layout

```text
project/
├── mod.js                     # final verified env patch, required by main.js
├── main.js                    # loads mod.js and prints encrypted params as JSON
├── main.py                    # sends real HTTP requests; pyexecjs2 first, subprocess fallback
├── package.json               # optional, only when JS runner needs dependencies
└── js_reverse_cache/
    ├── target/
    │   ├── raw.js             # original target JS
    │   ├── entry.js           # minimal target entry / fixture runner
    │   ├── fixtures.json      # browser input/output samples
    │   └── browser-evidence.md
    └── env/
        ├── profile.json
        ├── diagnose-output.json
        ├── gap-log.json
        └── ai-generated/
```

During diagnosis, keep volatile files under `js_reverse_cache/`. After functional verification passes, copy the stable environment into root `mod.js`, keep the callable JS entry in root `main.js`, and call it from root `main.py`.

### Critical Loading Order Rules

Module dependency order within `--env` matters. See `references/loading-order.md` for the full standard order. Key constraints:
- `dom/html-element-constructors.js` **must** come after `dom/document-dom-runtime.js` (depends on Element base class)
- `webapi/network-mock-recorder.js` **must** come after `webapi/xml-http-request.js` and `webapi/fetch-request-response.js`
- `dom/event-constructors.js` should come before `dom/document-dom-runtime.js`
- BOM modules generally go before DOM modules

### Module Selection Algorithm

1. Collect `undefinedPaths` from diagnose output
2. Extract prefix (before first `.`) from each path
3. Match prefix to module using `references/env-modules.md` mapping table
4. Manually order modules per `references/loading-order.md`
5. Manually add dependencies (e.g., `dom/html-element-constructors.js` requires `dom/document-dom-runtime.js`)

`vm-browser-gap-diagnose.js` does not sort modules or expand dependencies. It loads exactly the modules supplied via `--env`, in the supplied order.

### Key Design Decisions

- `success: true` from `vm-browser-gap-diagnose.js` only means the script loaded without throwing — it does NOT mean the target functionality (signing, encryption) works. Functional verification starts with temporary cache files, then must end in root-level `mod.js` + `main.js`.
- Python replay lives in root `main.py`. It should try `pyexecjs2` / `execjs` first and fall back to `subprocess.run(["node", "main.js", ...])` if JS execution fails.
- The sandbox's `window`/`self`/`global`/`globalThis` all point to the same sandbox object.
- `vm-browser-gap-diagnose.js` provides built-in stubs for: console, setTimeout/setInterval, atob/btoa, and a minimal XMLHttpRequest.
- `proxy-access-monitor.js` filters its own `[ProxyMonitor]` prefixed logs from consoleOutput to avoid noise.

## Writing Custom Patches

When an undefinedPath has no matching module, create a target-specific patch in the current workspace, not in the installed skill directory:

```javascript
// js_reverse_cache/env/ai-generated/<object>-<property>.js
(() => {
    'use strict';
    Object.defineProperty(window, 'someProperty', {
        value: /* reasonable browser default */,
        writable: false,
        configurable: true,
        enumerable: true
    });
})();
```

Then load it explicitly in the next diagnosis:

```bash
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js --env bom/navigator-fingerprint.js,js_reverse_cache/env/ai-generated/<object>-<property>.js <target.js>
```

`injected-patch-loader.js` is only a management helper for injected file contents; `vm-browser-gap-diagnose.js` does not automatically scan `env/ai-generated/` or any project-local `js_reverse_cache/env/ai-generated/` directory.
