# 环境模块加载顺序

## 标准加载顺序

```text
core/proxy-access-monitor.js           ← vm-browser-gap-diagnose.js 始终自动加载
core/profile-seed-manager.js           ← 传入 --profile/--profile-file 时自动加载
core/minimal-proxy-browser-env.js      ← 仅未指定 --env 时自动加载
───────────────────────────── ↑ 自动 / ↓ 手动指定
bom/navigator-fingerprint.js
bom/location-url-state.js
bom/screen-fingerprint.js
bom/web-storage.js
bom/window-global-apis.js
bom/history-state.js                  ← 按需，依赖 location-url-state.js
bom/web-crypto-stub.js
bom/performance-timing.js
bom/console-log-buffer.js             ← 可选
bom/observer-constructors.js          ← 可选
dom/event-constructors.js
dom/document-dom-runtime.js
dom/html-element-constructors.js      ← 必须在 document-dom-runtime.js 之后
webapi/fetch-request-response.js      ← 按需
webapi/xml-http-request.js            ← 按需
webapi/blob-file-formdata.js          ← 按需
webapi/url-search-params.js           ← 按需
webapi/network-mock-recorder.js       ← 按需，需在 XHR/fetch 之后
webapi/web-audio-fingerprint.js       ← 按需，AudioContext 指纹
webapi/webrtc-peerconnection.js       ← 按需，RTCPeerConnection 探测
webapi/worker-messaging.js            ← 按需，覆盖 window-global-apis.js 基础 Worker stub
encoding/base64-codec.js              ← vm-browser-gap-diagnose.js 已内置
encoding/text-codec.js                ← 按需
timer/timeout-interval-scheduler.js   ← vm-browser-gap-diagnose.js 已有 stub
ai-generated/*                        ← 最后加载
```

## 分类内部顺序

### BOM 内部顺序

```text
navigator-fingerprint → location-url-state → screen-fingerprint → web-storage → window-global-apis → history-state → web-crypto-stub → performance-timing
```

- `navigator-fingerprint.js` 最先：大多数指纹检测首先读 navigator。
- `location-url-state.js` 其次：`history-state.js` 依赖它更新 URL。
- `history-state.js` 在 `window-global-apis.js` 之后：需要 `window.location._parseUrl()`，且内部栈依赖 window。
- `window-global-apis.js` 在 navigator/location/screen 之后：它补充窗口级属性，不覆盖已有的。
- `web-crypto-stub.js` 和 `performance-timing.js` 可以放在 BOM 最后。

### DOM 内部顺序

```text
event-constructors → document-dom-runtime → html-element-constructors
```

- `event-constructors.js` 定义事件类，`document-dom-runtime.js` 可能用到。
- `html-element-constructors.js` 强依赖 `document-dom-runtime.js` 提供的 `Element` 基类，必须在之后。

### WebAPI 内部顺序

```text
fetch-request-response → xml-http-request → blob-file-formdata → url-search-params → network-mock-recorder
web-audio-fingerprint / webrtc-peerconnection / worker-messaging 可按缺口独立追加
```

- `network-mock-recorder.js` 增强 XMLHttpRequest 和 fetch，必须最后。
- `worker-messaging.js` 会覆盖 `bom/window-global-apis.js` 的基础 Worker/BroadcastChannel stub，建议放在 `window-global-apis.js` 之后。
- `web-audio-fingerprint.js`、`webrtc-peerconnection.js` 无强依赖；若使用 profile，`profile-seed-manager.js` 由诊断器自动提前加载。

## 最小加载集

根据目标脚本需求，只加载实际需要的模块。常见最小集：

### 简单指纹脚本

```text
bom/navigator-fingerprint.js, bom/location-url-state.js, bom/screen-fingerprint.js
```

### JSVMP 类签名（如 a_bogus）

```text
bom/navigator-fingerprint.js, bom/location-url-state.js, bom/screen-fingerprint.js, bom/web-storage.js,
bom/window-global-apis.js, bom/web-crypto-stub.js, bom/performance-timing.js,
dom/event-constructors.js, dom/document-dom-runtime.js, dom/html-element-constructors.js,
webapi/xml-http-request.js, webapi/url-search-params.js, encoding/text-codec.js
```

### 指纹探测较重脚本

```text
--profile default
bom/navigator-fingerprint.js, bom/location-url-state.js, bom/screen-fingerprint.js, bom/window-global-apis.js,
bom/web-crypto-stub.js, bom/performance-timing.js,
webapi/web-audio-fingerprint.js, webapi/webrtc-peerconnection.js, webapi/worker-messaging.js
```

### 完整浏览器环境

加载所有模块（少见，一般不需要）。

## 实战踩坑经验

### a_bogus119.js 教训

1. **`web-crypto-stub.js` 和 `performance-timing.js` 是 JSVMP 签名的关键依赖**
   - 缺少这两个模块，a_bogus 签名计算结果为 `undefined`。
   - JSVMP 用 `crypto.getRandomValues` 生成随机数，用 `performance.now()`/`performance.timeOrigin` 做时间戳。
   - 症状：XHR 流程走通，URL 上有 `a_bogus=undefined`。

2. **环境必须在目标脚本之前加载**
   - `bdms.init()` 在脚本加载时立即执行，读取 navigator/document 等。
   - 如果环境在脚本之后注入，bdms 初始化时拿到的全是 undefined。

3. **标准 XHR 流程不可省略**
   - a_bogus 的 `get_ab()` 用 `bdmsInvokeList` 跳过 `xhr.open()`。
   - JSVMP 的 wrapped open 负责存储 URL，跳过导致拿不到 URL。
   - 解决：用 `xhr.open(method, url) → xhr.send()` 标准流程。

4. **真实环境参数很重要**
   - 框架模块提供的是默认值（Chrome 120 + macOS 等）。
   - 对于校验严格的网站，需要用同一个可用页面上下文或用户样本采集真实浏览器参数覆盖默认值，不要混用多个来源。

## 按 undefinedPaths 前缀选择模块的算法

```text
1. 收集所有 undefinedPaths
2. 提取前缀集合（第一个 . 之前的部分）
3. 前缀 → 模块映射（见 env-modules.md）
4. 按标准顺序手动排列要加载的模块
5. 手动补充依赖（如 html-element-constructors.js 需要 document-dom-runtime.js，document-dom-runtime.js 前建议加载 event-constructors.js）
6. 如需真实指纹 seed，先生成 profile，再加 `--profile-file js_reverse_cache/env/profile.json`
7. 重新执行诊断
```

注意：`vm-browser-gap-diagnose.js` 会按 `--env` 参数给出的顺序逐个加载模块，不会自动排序或补依赖。把这段算法当作人工选择 `--env` 列表的规则。
