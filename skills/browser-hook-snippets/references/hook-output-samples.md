# Hook 输出样本

以下为各类型 hook 注入后，Console 中预期的日志形态。模型生成 hook 脚本时应以这些输出为参考目标。

## XHR Hook

```text
[XHR Hook] open: GET https://api.example.com/data?keyword=test
[XHR Hook] setRequestHeader: x-sign = a1b2c3d4e5f6...
[XHR Hook] send: body={"page":1,"size":20}
[XHR Hook] readyState: 4, status: 200
  Response: {"code":0,"data":[...]}
=== Call Stack ===
  at XMLHttpRequest.send (native)
  at api.fetchData (https://domain.com/static/app.chunk.js:2345:12)
  at App.componentDidMount (https://domain.com/static/main.bundle.js:890:5)
```

## Fetch Hook

```text
[Fetch Hook] Request: POST https://api.example.com/login
  Headers: {"content-type":"application/json","x-token":"eyJhbG..."}
  Body: {"username":"test","timestamp":1716900000}
[Fetch Hook] Response from https://api.example.com/login
  Status: 200
  Headers: {"set-cookie":"sessionId=xyz; Path=/; HttpOnly"}
  Body snippet: {"code":0,"token":"..."}
=== Call Stack ===
  at fetch (native)
  at loginService.submit (https://domain.com/js/login.v3.js:456:8)
```

## Cookie Write Hook

```text
[Cookie Hook] SET cookie: acw_tc=2f6a1...
  Value preview: 2f6a1fc1701...
  Path: /, Domain: .example.com
=== Call Stack ===
  at Object.defineProperty (native)
  at setCookie (https://domain.com/static/challenge.js:123:5)
  at initProtection (https://domain.com/static/challenge.js:80:3)
```

## Storage Hook

```text
[Storage Hook] localStorage.setItem("token", "eyJhb...")
  Value preview: eyJhbGciOiJIUz...
  Key preview: token
=== Call Stack ===
  at Storage.setItem (native)
  at saveSession (https://domain.com/js/auth.js:234:15)
```

## WebCrypto Hook

```text
[Crypto Hook] crypto.subtle.digest("SHA-256", ArrayBuffer[32])
  Algorithm: SHA-256
  Data length: 32 bytes
  Data preview (hex): a1b2c3d4e5f6...
  Result type: ArrayBuffer
  Result length: 32 bytes
  Result preview (hex): 7f83b165...
=== Call Stack ===
  at SubtleCrypto.digest (native)
  at signData (https://domain.com/static/crypto-utils.js:67:22)
  at buildRequest (https://domain.com/static/api.js:145:12)
```

## Canvas Fingerprint Hook

```text
[Canvas Hook] getContext("2d") called
  Width: 280, Height: 60
[Canvas Hook] fillText at (2, 20): "Cwm fjordbank glyphs vext quiz 😃"
[Canvas Hook] toDataURL called
  DataURL length: 12034 chars
  DataURL preview: data:image/png;base64,iVBORw0KGgo...
```

## 降噪配置

高频场景在 hook 脚本开头加开关：

```js
const HOOK_CONFIG = {
  FULL_LOG: false,           // 设为 true 打印完整值（默认降噪）
  MAX_BODY_LENGTH: 200,      // 请求/响应体截断长度
  MAX_STACK_DEPTH: 5,        // 调用栈深度
  URL_FILTER: null,          // 设为字符串过滤特定 URL，如 "/api/"
  DUPLICATE_SUPPRESS: true,  // 抑制重复日志
};
```

## 请求绑定输出

当用户要观察"哪个请求带了目标字段"：

```text
[Request Binding] target=fetch, event=open, method=POST, url=/api/submit
  Hit fields: header x-sign, body.timestamp
[Request Binding] target=xhr, event=setRequestHeader, header=x-token
  Value preview: eyJhb...
  URL: /api/data/list?page=1
```
