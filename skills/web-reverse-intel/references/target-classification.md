# Target Classification

Classify the target before searching. A target can have multiple types; choose a primary type and one or two secondary types.

## Types

| Type | Signals | Search Focus |
| --- | --- | --- |
| `web_api_signature` | `sign`, `signature`, `timestamp`, `nonce`, sorted params, hash output | request signing, hash algorithm, salts, canonical string, timestamp drift |
| `encrypted_parameters` | encrypted payload, `data`, `payload`, AES/RSA/Base64, unreadable body | crypto libraries, key derivation, IV, mode, padding, pack/unpack routines |
| `anti_bot_challenge` | 403/412/429, challenge page, sensor, dynamic cookie, redirect loop | vendor marker, challenge JS, cookie names, browser fingerprint, WASM |
| `captcha` | slider, image puzzle, GeeTest, Dingxiang, Tencent Captcha, challenge token | captcha SDK, token flow, risk control callback, image/track evidence |
| `javascript_obfuscation` | packed JS, string arrays, control flow flattening, JSVM, anti-debug | obfuscator, dispatcher, string decoder, webpack chunks, source maps |
| `wasm_crypto` | `.wasm`, exported functions, memory reads, crypto constants | WASM filename, exports, imports, algorithm names, old module versions |
| `device_fingerprint` | canvas, WebGL, audio, navigator, fonts, timezone, hardware signals | fingerprint fields, browser environment reads, sensor libraries |
| `token_generation` | session token, csrf, nonce, refresh token, local storage dependency | token lifecycle, bootstrap endpoint, storage key, expiration behavior |
| `mobile_protocol` | APK/IPA package, app version, device ID, native SDK, protobuf | package name, decompiled strings, app version, SDK names, endpoints |
| `graphql_api` | `/graphql`, operation name, persisted query, variables hash | operation names, query hash, schema leaks, client bundle fragments |
| `protobuf_api` | binary body, `application/x-protobuf`, `.proto`, gRPC-web | proto names, message classes, generated clients, field numbers |

## Classification Procedure

1. Extract obvious signals from the user prompt, URLs, request samples, JS filenames, and parameter names.
2. Assign one primary type and optional secondary types.
3. Record confidence as high, medium, or low.
4. Emit a classification plan with `search_priority`, `keywords`, and `ignore` lists.
5. Use type-specific vocabulary in first-round queries.
6. Reclassify after new evidence appears; do not stay locked to the first guess.

## Classification Plan

Use this compact shape in the intelligence brief:

```yaml
type: web_api_signature
confidence: medium
search_priority:
  - github_code
  - js_analysis_blog
  - reverse_forum
keywords:
  - sign
  - signature
  - timestamp
  - nonce
  - canonical string
ignore:
  - captcha_solver
```

## Type-Driven Search Strategy

| Type | Search Priority | Keywords | Ignore Unless Evidence Appears |
| --- | --- | --- | --- |
| `web_api_signature` | GitHub/code search, JS analysis blogs, reverse forums | `sign`, `signature`, `timestamp`, `nonce`, `hash`, `canonical string` | captcha solvers, TLS fingerprinting |
| `encrypted_parameters` | code search, crypto writeups, package registries | `AES`, `RSA`, `CryptoJS`, `JSEncrypt`, `payload`, `decrypt` | anti-bot vendor threads |
| `anti_bot_challenge` | vendor markers, forums, current issue threads, archives | `challenge`, `sensor`, `fingerprint`, `cookie`, `wasm`, `403`, `412` | generic MD5 signing posts |
| `captcha` | SDK docs, forums, issue threads, image/track writeups | `captcha`, `slider`, `track`, `challenge`, `validate`, provider name | generic request signing |
| `javascript_obfuscation` | AST/deobfuscation posts, code search, bundle strings | `string decoder`, `dispatcher`, `control flow flattening`, `VM`, `opcode` | package API clients |
| `wasm_crypto` | WASM filename/export search, crypto constants, GitHub | `WebAssembly`, `.wasm`, `exports`, `memory`, `crypto`, algorithm name | pure Python requests snippets |
| `device_fingerprint` | anti-bot posts, browser APIs, sensor libraries | `canvas`, `WebGL`, `AudioContext`, `navigator`, `fonts`, `timezone` | simple endpoint examples |
| `mobile_protocol` | package names, app version, decompiled strings, protobuf | APK, package name, device ID, SDK, `.proto`, app version | browser-only hook snippets |
| `graphql_api` | operation names, persisted queries, client bundles | `operationName`, `persistedQuery`, `sha256Hash`, `/graphql` | captcha/slider content |
| `protobuf_api` | proto names, generated clients, gRPC-web, binary traces | `.proto`, `protobuf`, `message`, field number, `gRPC-web` | HTML challenge pages |

## Handoff Hints

- Use browser tracing or hook workflows after public intel identifies likely runtime attachment points.
- Use AST/deobfuscation workflows when public intel points to string decoders, dispatcher loops, packed bundles, or known obfuscators.
- Use environment patching or JavaScript runtime emulation when public intel exposes browser APIs, crypto libraries, or JS entry functions.
- Use protocol recovery after public intel confirms endpoints, headers, token flow, binary formats, or bootstrap dependencies.
