# Entry Patterns

Use this reference when locating a request signature, token, cookie, or security header generation entry.

The goal is to identify a handoff point for later deobfuscation or environment patching, not to finish the entire reverse engineering task inside this skill.

## Common Architectures

### Direct Business Assignment

Look for code shaped like:

```javascript
headers['x-sign'] = encrypt(payload)
config.params.sign = makeSign(config.params)
```

Search order:

1. Parameter/header name.
2. API path fragment.
3. Nearby request wrapper function.
4. Encryption function name if visible.

Deliver the request function, assignment line, and encrypt call path.

### Request Interceptor

Common with axios, fetch wrappers, umi request, uni-app request, and custom SDK adapters.

Search order:

1. `interceptors.request.use`.
2. `setRequestHeader` / `headers` / `config.headers`.
3. API allowlist or path matcher.
4. Shared request wrapper imports.

Do not stop at the interceptor registration. Trace from request config to the function that writes the final value.

### External Security SDK

The business bundle may only call a global SDK, while the real algorithm is in a separate obfuscated script.

Search order:

1. Global object name from business caller.
2. SDK init call.
3. Registered paths, switches, or cache options.
4. SDK method that returns or injects the security field.

If the SDK file is heavily obfuscated, finish with the SDK entry function and recommend `ast-deobfuscate` or `env-patch` based on the user's next goal.

### Challenge / Dynamic Cookie

Signals:

1. First request returns `412`, `202`, `204`, redirect, or challenge HTML.
2. Page contains `$_ts`, `cookie_s`, `cookie_t`, `meta[r='m']`, or dynamic script URLs.
3. The field appears as `document.cookie` rather than a normal API header.

Do not treat this as a normal sign parameter search. Identify the challenge branch and hand off to `env-patch` if the user wants protocol reproduction.

## Dynamic Verification

When static search is insufficient:

1. Break on XHR/fetch for the target API.
2. Inspect the request wrapper frame, not only framework internals.
3. Use the call stack to jump to the assignment frame.
4. Evaluate local variables in that frame.
5. Record script URL, line/column, function name, and caller chain.

Avoid repeated step-into through framework code. It is usually slower than checking the current frame and moving up the stack.

## Completion Template

```text
入口位置：
- 参数：<name>
- 脚本：<script URL or local file>
- 位置：第 X 行，第 Y 列
- 函数：<function name or anonymous>
- 调用路径：request -> interceptor -> encrypt
- 入口类别：业务直赋值 | 拦截器统一加签 | 外部 SDK | challenge/动态 cookie
- 下一步：ast-deobfuscate | env-patch | browser-hook-snippets | 已完成
```
