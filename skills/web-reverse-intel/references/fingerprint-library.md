# Fingerprint Library

Static fingerprints often produce better search leads than the target domain. Use this reference when the user provides HTML, JS, WASM, package names, bundle filenames, or snippets from traffic.

## Fingerprint Classes

| Class | Examples | Query Direction |
| --- | --- | --- |
| Bundler/runtime | `webpackJsonp`, `__webpack_require__`, `vite`, `parcelRequire`, `__NEXT_DATA__` | framework plus target alias, source map, chunk name |
| Crypto library | `CryptoJS`, `JSEncrypt`, `forge`, `jsrsasign`, `SubtleCrypto` | library plus `sign`, `encrypt`, parameter name |
| Obfuscator | `_0x`, `obfuscator.io`, `sojson`, `jsjiami`, string array, control-flow flattening | obfuscator plus bundle name, decoder, VM |
| WASM | `.wasm`, `WebAssembly.instantiate`, exports, memory, crypto constants | wasm filename, export name, algorithm |
| Anti-bot/vendor | `bm_sz`, `_abck`, `cf_clearance`, `r2mKa`, `$_ts`, `sensor_data` | cookie/global plus vendor and target alias |
| Fingerprint APIs | `canvas`, `WebGLRenderingContext`, `AudioContext`, `navigator.webdriver`, fonts | API plus vendor, sensor, target type |
| Mobile/protocol | package name, app version, `.proto`, gRPC-web, device ID | package plus endpoint, proto message, SDK |
| GraphQL | `operationName`, `persistedQuery`, `sha256Hash`, `/graphql` | operation name, query hash, client bundle |

## Query Patterns

- `"{fingerprint}" "{target_alias}"`
- `"{fingerprint}" "sign"`
- `"{fingerprint}" "逆向"`
- `"{fingerprint}" "web scraping"`
- `"{fingerprint}" "encryption"`
- `site:github.com "{fingerprint}" "{parameter}"`
- `site:blog.csdn.net "{fingerprint}" "JS逆向"`

## Use Rules

Prefer rare fingerprints over broad framework names. `JSEncrypt` plus a parameter name is stronger than `webpack`.

Pair generic fingerprints with target aliases, endpoints, or vendor names.

Record fingerprints that produce no hits as negative intelligence so the same failed search is not repeated.
