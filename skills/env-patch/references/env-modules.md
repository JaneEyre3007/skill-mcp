# 环境模块属性映射表

根据 `undefinedPaths` 的前缀选择最小 env 模块。模块路径均相对于 `$SKILL_DIR/env/`。

## 查找规则

1. 取 undefinedPath 的前缀，如 `navigator.userAgent` → `navigator`。
2. 在映射表中匹配前缀，选择最小相关模块。
3. 按 `references/loading-order.md` 手动排序。
4. 没有匹配时，写项目本地 `js_reverse_cache/env/ai-generated/<object>-<property>.js` 补丁。

## core/ 核心基础

#### `core/proxy-access-monitor.js` ⭐ 首选
- **提供**: `watch()`, `safefunction()`, `makeFunction()`, `window.__ProxyMonitor__`
- **说明**: `vm-browser-gap-diagnose.js` 始终自动加载，用于记录属性访问、函数调用和 undefined 读取。

#### `core/profile-seed-manager.js`
- **提供**: `window.__profile__`, `window.__ProfileManager__`
- **说明**: 仅当传入 `--profile` 或 `--profile-file` 时自动加载，在其他 env 模块前注入 profile seed。

#### `core/minimal-proxy-browser-env.js`
- **提供**: 基础 `document`, `navigator`, `location`, `history`, `screen`, `localStorage`, `sessionStorage` 代理对象
- **依赖**: `core/proxy-access-monitor.js`
- **说明**: 仅当未指定 `--env` 时自动加载；显式指定 env 模块后会跳过，避免 `configurable:false` 冲突。

#### 监控模块选择

| 需求 | 推荐模块 |
|---|---|
| 基础 watch/safefunction，常规补环境诊断 | `core/proxy-access-monitor.js` |
| 日志分类、查询 API、多类型 mock 存储 | `core/classified-env-monitor.js` |
| 元素创建代理、属性回调、mock 钩子 | `core/element-mock-monitor.js` |

> `classified-env-monitor.js` 和 `element-mock-monitor.js` 均注册 `window.__EnvMonitor__`，不要同时加载。

## bom/ Browser Object Model

#### `bom/navigator-fingerprint.js`
- **前缀匹配**: `navigator`
- **提供**: UA、platform、language、hardwareConcurrency、deviceMemory、webdriver、plugins、mimeTypes、connection、permissions、mediaDevices、serviceWorker、userAgentData 等 navigator 指纹面。

#### `bom/location-url-state.js`
- **前缀匹配**: `location`
- **提供**: `location.href/protocol/host/hostname/port/pathname/search/hash/origin` 与 `assign()/replace()/reload()`。

#### `bom/screen-fingerprint.js`
- **前缀匹配**: `screen`
- **提供**: `screen.width/height/availWidth/availHeight/colorDepth/pixelDepth/orientation/isExtended`。

#### `bom/web-storage.js`
- **前缀匹配**: `localStorage`, `sessionStorage`, `StorageEvent`
- **提供**: Web Storage 的 `getItem/setItem/removeItem/clear/key/length`。

#### `bom/window-global-apis.js`
- **前缀匹配**: `window.innerWidth`, `window.devicePixelRatio`, `window.visualViewport`, `window.requestAnimationFrame`, `window.matchMedia`, `window.getComputedStyle`, `indexedDB`, `CSS`, `trustedTypes`, `caches`
- **提供**: 窗口尺寸、滚动、弹窗、RAF/RIC、选择、postMessage、基础 Worker、IndexedDB、CSS、Observer、Notification、Clipboard、scheduler 等窗口级 API 大包。
- **注意**: 不创建 window 本身，只补充 sandbox window 上的属性和方法。

#### `bom/history-state.js`
- **前缀匹配**: `history`, `window.history`
- **提供**: history 栈、`back/forward/go/pushState/replaceState` 与 popstate 派发。
- **依赖**: `bom/location-url-state.js`

#### `bom/web-crypto-stub.js`
- **前缀匹配**: `crypto`, `window.crypto`, `CryptoKey`
- **提供**: `crypto.getRandomValues()`, `randomUUID()`, `crypto.subtle.*` 最小 Promise stub。
- **关键场景**: JSVMP、a_bogus 等常依赖随机数和 subtle 入口。

#### `bom/performance-timing.js`
- **前缀匹配**: `performance`, `PerformanceObserver`
- **提供**: `performance.now()`, `timeOrigin`, `timing`, `navigation`, `memory`, marks/measures 和 PerformanceObserver。

#### `bom/console-log-buffer.js`
- **前缀匹配**: `console`
- **提供**: 完整 `console.*` 方法和内部日志缓冲。
- **说明**: 诊断器已有基础 console，只有需要 `console.table/dir/time/count` 等完整形态时加载。

#### `bom/observer-constructors.js`
- **前缀匹配**: `MutationObserver`, `IntersectionObserver`, `ResizeObserver`, `PerformanceObserver`, `ReportingObserver`
- **提供**: Observer 构造器、记录对象和测试触发辅助。

## dom/ Document Object Model

#### `dom/event-constructors.js`
- **前缀匹配**: `Event`, `CustomEvent`, `UIEvent`, `MouseEvent`, `KeyboardEvent`, `FocusEvent`, `InputEvent`, `WheelEvent`, `TouchEvent`, `PointerEvent`, `SubmitEvent`, `AbortController`
- **提供**: 事件类体系、EventTarget、AbortSignal/AbortController。
- **加载顺序**: 建议在 `dom/document-dom-runtime.js` 前加载。

#### `dom/document-dom-runtime.js`
- **前缀匹配**: `document`, `Node`, `Element`, `Document`, `DOMRect`, `HTMLCanvasElement`, `CanvasRenderingContext2D`, `WebGLRenderingContext`, `Image`
- **提供**: document 元数据、节点树、查询/创建/写入/事件 API、基础 DOM 类、Canvas/WebGL/Image 等大块运行时。

#### `dom/html-element-constructors.js`
- **前缀匹配**: `HTMLElement`, `HTMLDivElement`, `HTMLCanvasElement`, `HTMLImageElement`, `HTMLVideoElement`, `HTMLAudioElement`, `HTMLInputElement`, `HTMLFormElement`, `HTMLScriptElement`, `HTMLIFrameElement` 等
- **提供**: 更完整的 HTML 元素构造器体系、Canvas/WebGL/媒体/表单/表格等元素类型。
- **依赖**: 必须在 `dom/document-dom-runtime.js` 之后加载。

## webapi/ Web API

#### `webapi/fetch-request-response.js`
- **前缀匹配**: `fetch`, `Headers`, `Request`, `Response`, `AbortController`, `AbortSignal`
- **提供**: Fetch API、请求/响应对象、Headers 和 abort 基础实现。

#### `webapi/xml-http-request.js`
- **前缀匹配**: `XMLHttpRequest`, `XMLHttpRequestUpload`
- **提供**: XHR readyState、headers、response、事件回调和模拟响应。
- **说明**: 诊断器内置最小 XHR stub；需要完整 XHR 行为时加载此模块。

#### `webapi/blob-file-formdata.js`
- **前缀匹配**: `Blob`, `File`, `FileReader`, `FormData`
- **提供**: Blob/File/FileReader/FormData 基础实现。

#### `webapi/url-search-params.js`
- **前缀匹配**: `URL`, `URLSearchParams`, `webkitURL`
- **提供**: URL 解析、SearchParams、`createObjectURL/revokeObjectURL/canParse`。

#### `webapi/network-mock-recorder.js`
- **前缀匹配**: `__NetworkStore__`, `__NetworkMock__`
- **提供**: 增强 XHR/fetch、请求记录、URL/method mock 规则。
- **依赖**: `webapi/xml-http-request.js`, `webapi/fetch-request-response.js`

#### `webapi/web-audio-fingerprint.js`
- **前缀匹配**: `AudioContext`, `webkitAudioContext`, `OfflineAudioContext`, `AudioBuffer`, `AudioNode`, `AudioParam`
- **提供**: Web Audio 指纹探测常用 stub、离线渲染最小返回。

#### `webapi/webrtc-peerconnection.js`
- **前缀匹配**: `RTCPeerConnection`, `webkitRTCPeerConnection`, `RTCDataChannel`, `RTCIceCandidate`, `RTCSessionDescription`
- **提供**: PeerConnection 状态、offer/answer、DataChannel、ICE candidate stub。

#### `webapi/worker-messaging.js`
- **前缀匹配**: `Worker`, `SharedWorker`, `MessagePort`, `MessageChannel`, `BroadcastChannel`
- **提供**: Worker/SharedWorker 构造器、MessagePort 双端通信、BroadcastChannel 本地派发。
- **说明**: 比 `bom/window-global-apis.js` 内置 Worker stub 更完整；需要消息通路时显式加载。

## timer/ 定时器

#### `timer/timeout-interval-scheduler.js`
- **前缀匹配**: `setTimeout`, `setInterval`, `clearTimeout`, `clearInterval`, `queueMicrotask`
- **提供**: 带 ID 跟踪的定时器实现和调试方法 `__getActiveTimers__`、`__clearAllTimers__`。

## encoding/ 编码

#### `encoding/base64-codec.js`
- **前缀匹配**: `atob`, `btoa`
- **提供**: Base64 编解码。
- **说明**: 诊断器已内置，通常无需额外加载。

#### `encoding/text-codec.js`
- **前缀匹配**: `TextEncoder`, `TextDecoder`
- **提供**: UTF-8 TextEncoder 和多编码 TextDecoder。

## ai-generated/ 自定义补丁

#### `ai-generated/injected-patch-loader.js`
- **提供**: `window.__aiGeneratedEnv__` 管理系统。
- **说明**: 只用于手动注入 `window.__aiFileContents__` 后集中执行多段补丁；普通补丁文件仍通过 `--env ai-generated/<file>.js` 显式加载。

#### `ai-generated/window-user-agent-patch.js`
- **提供**: 示例 `window.userAgent` 补丁。

#### `ai-generated/navigator-webdriver-patch.js`
- **提供**: 示例 `navigator.webdriver = false` 补丁。
