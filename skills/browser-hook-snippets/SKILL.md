---
name: browser-hook-snippets
description: >-
  生成浏览器 DevTools Console / Snippets 可直接粘贴执行的观察型 hook 脚本。追踪 cookie、XHR、fetch、header、storage、WebCrypto、canvas、Worker、Blob、DOM 注入等动态行为。适合用户已知观察目标、只缺可执行脚本时。默认最小侵入、页面层观察。当需要验证hook效果或定位脚本位置时，MCP使用策略：优先 cloakbrowser-reverse-mcp（启动脚本 E:\\BaiduNetdiskDownload\\JS逆向2622期\\JS逆向17 webpack打包方式 - 2-2026-6-3-顾安\\2026_6_3_webpack - 2\\2026_6_3_webpack - 2\\CloakBrowser\\cloakbrowser-reverse-mcp\\launch.bat，含 CDP/SourceMap/Profiler/WebSocket/Hook 能力）；只有需要 Camoufox 引擎级指纹/属性追踪证据时转 camoufox-js-reverse。不适合：不知道要hook什么，需要先定位函数位置（转 camoufox-js-reverse）、要脱离浏览器在 Node.js 跑（转 env-patch）、要 Python + iv8 脚本（转 iv8-web-reverse）。
argument-hint: "[目标对象或行为]"
compatibility: "需要浏览器调试能力；默认面向 DevTools Console / Snippets / 页面注入脚本。部分模板依赖现代浏览器 API（如 fetch、WebCrypto、Worker、MutationObserver），必要时需切到页面上下文注入。当需要验证hook效果或定位脚本位置时，MCP使用策略：优先 cloakbrowser-reverse-mcp（E:\\BaiduNetdiskDownload\\JS逆向2622期\\JS逆向17 webpack打包方式 - 2-2026-6-3-顾安\\2026_6_3_webpack - 2\\2026_6_3_webpack - 2\\CloakBrowser\\cloakbrowser-reverse-mcp\\launch.bat，含 CDP/SourceMap/Profiler/WebSocket/Hook 能力）；只有需要 Camoufox 引擎级指纹/属性追踪证据时转 camoufox-js-reverse"
---

# browser-hook-snippets

围绕 **$ARGUMENTS** 生成最小可用的浏览器 hook 脚本，并说明注入位置、预期现象和回收方式。

## 目标

当用户已经知道要盯的对象或行为时，直接给出可执行的 hook 方案，而不是停留在原理说明。

## 触发信号

下面这些说法通常应该触发本 skill：

1. “给我一个 hook xxx 的脚本”。
2. “给一段控制台 hook 脚本，临时观察是谁写了 cookie/token/header”。
3. “帮我盯住 fetch/xhr/websocket/postMessage/worker”。
4. “想观察某个 DOM、canvas、blob、随机数、加密 API 调用时的入参和调用栈”。
5. “给一个能直接贴到 DevTools Console 或 Snippets 的脚本”。

下面这些说法通常不该由本 skill 单独处理，应转交对应 skill：

1. "这个签名参数在哪生成" 或 "帮我找到脚本 URL、函数名、行列号" 或 "用浏览器定位关键加解密 JS 代码" → `camoufox-js-reverse`。
2. "把这段浏览器 JS 搞到 Node 里跑" → `env-patch`。
3. "帮我反混淆这个大文件" → `ast-deobfuscate`。
4. "Python + iv8 执行防护页 / 动态 cookie / 翻页请求" → `iv8-web-reverse`。
5. 瑞数/Ruishu/Rivers 如果不是“只要可粘贴 hook 脚本”，按目标分流：入口/调用链定位 → `camoufox-js-reverse`；Node/proxy 跑通 → `env-patch`；iv8/suffix 请求可用性 → `iv8-web-reverse`。
6. 用户目标已超出单点观察、需要完整协议链路恢复（签名/挑战/解码/传输一体化）→ `web-protocol-recovery`。

## 适用范围

按目标读取对应分类：

1. 请求、header、WebSocket、postMessage：`references/network.md`
2. cookie、storage、输入值：`references/storage.md`
3. base64、WebCrypto、随机数、编码边界：`references/crypto.md`
4. createElement、DOM 注入、MutationObserver、canvas：`references/dom.md`
5. JSON、eval、Function、Blob、Worker：`references/runtime.md`

## 输出要求

默认给出这 4 项：

1. 一段可以直接执行的最小 hook 脚本。
2. 脚本应该注入在哪里：Console、Snippets、Sources 断点后注入，还是页面脚本标签注入。
3. 预期能看到什么日志或断点。
4. 需要注意的副作用和恢复方式。

如果用户目标比较明确，再补 1 项：

5. 为什么优先 hook 这个点，而不是附近其它点。

## 工作方式

按最小侵入原则处理：

1. 先确认 hook 目标是“属性”“方法”还是“构造器”。
2. 优先包装单个目标，不要一上来全局代理整页对象。
3. 保留原函数引用，调用原实现时避免递归调用自身。
4. 默认只做记录和断点，不主动改返回值，除非用户明确要求篡改行为。
5. 如果目标代码跑在页面上下文而不是 Console 沙箱里，使用 `script.textContent = '(' + fn + ')()'` 注入页面上下文。
6. 如果页面存在完整性检测、native 伪装检测、原型链检测或 JSVMP 环境探测，先提醒用户：JS hook 可能改变行为、失去命中或直接被检测。

### 确认检查点

默认只输出观察型脚本。遇到下面情况必须先确认用户意图，再生成或注入脚本：

1. 用户要求阻断请求、篡改参数、改返回值、覆盖 cookie/storage 或改变页面行为。
2. 用户要求打印完整 Cookie、Authorization、token、请求体、响应体、canvas/dataURL、ArrayBuffer、Blob 或其它敏感原文；默认只给预览、长度、哈希或 `FULL_LOG` 开关。
3. 脚本需要全局代理 `window`、`document`、`navigator`、所有 XHR/fetch/WebSocket，或会显著增加页面开销。
4. 需要用工具直接注入到真实目标页，而不是只给 Console/Snippets 代码；先确认页面已打开、注入范围和回收方式。
5. 页面有完整性检测、native 检测、JSVMP 环境检测或 hook 后行为变化；先收缩 hook 点或转 `camoufox-js-reverse`，不要叠加更大的代理。

### 浏览器工具注入与降级

本 skill 默认交付可粘贴脚本，不强制启动浏览器工具。只有用户要求“帮我直接注入/验证/截图/抓日志”，或当前会话已经在浏览器工具里运行目标页时，才使用工具化注入。

优先级：

1. 当前已打开目标页的页面上下文：直接注入 hook，读取 console/network 日志。
2. 未打开页面时，启动 `cloakbrowser-reverse-mcp`：用于页面导航、evaluate_script/main-world evaluate、network、console、CDP 断点、SourceMap、Profiler、WebSocket 和 Hook。不可用时降级为手工 Console/Snippets 脚本或用户样本。
3. 工具不可用或会改变页面行为时：只输出 Console/Snippets 脚本和触发说明。
4. 被目标站风控拦截（412/403/验证码）时，说明需要反检测能力，转交 `camoufox-js-reverse`。

如果工具化注入改变页面行为，立即降级为更小 hook 点或只给手工脚本，不继续叠加全局 proxy。

跨 skill 的阶段协议见 `references/js-reverse-workflow.md`。本 skill 主要服务 `Capture` 阶段：优先用 hook 采样真实运行行为；hook 无法回答函数位置或完整调用链时，再升级到 `camoufox-js-reverse`。需要落地 hook 日志、采样证据或临时脚本时，按共享协议写入执行代码的工作区下的 `js_reverse_cache/`；不存在则先创建，不要写到工作区之外。

### Hook 数据降噪

默认输出要帮助定位调用点，不要把页面刷死或泄出整份无关数据。生成 hook 时优先保留字段名、URL、调用栈、类型、长度和少量预览，必要时再给“完整值开关”。

1. 对 cookie、Authorization、token、storage value、请求体或响应字段，默认使用 `mask()`、`slice()`、`substring()`、`bodySnippet` 或长度/哈希摘要降噪。
2. 高频 hook 默认加 URL、字段名、调用次数、时间戳、去重 key 等辅助字段，避免重复刷屏。
3. 对 request body、WebSocket message、canvas/dataURL、ArrayBuffer、Blob 等大体积数据，默认只打印类型、长度和前后片段。
4. 如果用户明确要求“完整原文 / 不脱敏 / 不截断 / 用于补环境复现”，再输出完整值或提供 `FULL_LOG = true` 开关。
5. 如果目标是后续补环境，额外补充候选环境依赖，如 `cookie`、`storage`、`Date`、`crypto`、`location`，并说明如何临时打开完整值采样。

### Request Binding

当用户要观察“哪个请求带了目标字段”时，hook 输出应尽量绑定请求上下文：

1. `target`: fetch | xhr | websocket | form | beacon。
2. `event`: open | send | setRequestHeader | response | message。
3. `method` 和 `url`。
4. 命中的 header / query / body 字段名。
5. 可选 `console.trace()` 或一次性 `debugger`，用于后续转交 `camoufox-js-reverse`。

如果用户只要最小脚本，不要强行附带复杂摘要器；但可以在说明里给出如何按 URL/字段过滤，以及如何切换为完整值输出。

## 经验规则

1. `document.createElement`、`XMLHttpRequest.prototype.open` 这类宿主方法，先 `bind` 或保存原引用再调用，避免 `Illegal invocation`。
2. `WebSocket.prototype.send`、`fetch`、`eval` 这类函数 hook 时，返回值必须继续走原实现，否则页面容易异常。
3. 属性 hook 优先用 `Object.defineProperty`；如果原属性已经不可配置，改用外围调用点或原型方法 hook。
4. 只在用户明确要求时才提供“阻断”型脚本；默认提供“观察”型脚本。
5. 如果用户想知道“请求是谁发起的”，而当前环境没有专门的 request initiator 工具，优先在 `fetch` / `xhr` hook 里补 `console.trace()`，用调用栈替代专用调试工具能力。
6. 如果用户问“某个 cookie 是谁写的”，先提醒：`document.cookie` hook 只能看到 JS 写入；若 cookie 实际来自 HTTP `Set-Cookie`，必须同时检查目标请求或响应头。
7. 遇到 SDK 或拦截器型页面时，不要默认只 hook `XMLHttpRequest`；很多站点会同时走 `xhr` 和 `fetch`，漏掉其中一个就会误判“签名函数没跑到”。
8. 观察环境读取型行为时，优先从 `navigator`、`screen`、`document.createElement`、`canvas.getContext`、`WebGLRenderingContext.getParameter`、`performance.now`、`localStorage`、`sessionStorage` 里选一个最可疑点定向下手，不要一次全开。
9. 如果 hook 后页面行为变化、请求消失、签名降级或日志极多，先收缩 hook 点、改断点或补 `console.trace()`，不要继续叠加更多 hook。
10. 高频 hook 默认加 URL、字段名或调用次数条件，并对请求体、cookie、storage 做预览或摘要；只有用户明确要求完整现场值时才全量打印。

## 反模式

不要默认输出下面这些高风险写法：

1. 无条件清空所有定时器。
2. 粗暴替换所有 `debugger`、所有 `console`、所有 `RegExp`。
3. 会递归调用自己的错误 hook，比如在 `send` 里再次调用被改写后的 `send`。
4. 大范围改写原生对象却不说明恢复方式。
5. 默认代理整个 `window`、`document`、`navigator`。
6. 在强完整性检测页面里，不提醒风险就直接输出重写原型链的大脚本。

这些片段可以作为特殊场景候选，但不作为默认答案。

## 参考片段

索引见 `references/snippets.md`。hook 输出样本和降噪效果示例见 `references/hook-output-samples.md`。

**预置 hook 模板**（可直接复制粘贴使用）：

| 模板 | 用途 |
|------|------|
| `scripts/xhr_fetch.js` | XHR + fetch 双通道 hook，含请求/响应摘要和调用栈 |
| `scripts/cookie_header.js` | document.cookie 写入 + Headers 构造观察 |
| `scripts/crypto_api.js` | WebCrypto.subtle + CryptoJS 加解密调用 hook |
| `scripts/storage.js` | localStorage / sessionStorage 读写监控 |

生成答案时：

1. 先按用户目标只读最相关的 1 个分类文件，必要时再补第 2 个。
2. 按当前页面需求裁剪，不要整份堆给用户。
3. 如果用户给了关键字或 URL 片段，直接代入条件判断。
4. 如果用户没说注入时机，优先提醒“可在 Sources 首个脚本处暂停后再注入”。
5. 如果页面明显会因为 hook 方式不同而失效，显式说明是“Console 沙箱 hook”还是“页面上下文 hook”。

## 升级与降级

当最小 hook 不能满足需求时，按这个顺序调整：

1. 先缩小到单个属性、单个方法或单个 URL 条件。
2. 再补 `console.trace()`、条件断点或一次性 `debugger`。
3. 如果用户真正要的是函数位置、脚本 URL、调用链，转给 `camoufox-js-reverse`。
4. 如果用户真正要的是 Node.js 独立复现，转给 `env-patch`。
5. 如果浏览器工具不可用，降级为手工 Console/Snippets 脚本，并在说明中写明未验证运行时日志。

## 回答风格

1. 先给能跑的最小脚本。
2. 再给注入位置和触发条件。
3. 最后再补副作用和升级建议。
4. 除非用户明确要求，不要一次贴多个大脚本方案。

## 完成标准

完成时，用户应能直接拿到：

1. 可执行脚本。
2. 断点或日志触发条件。
3. 为什么这个 hook 点有效。
4. 何时需要升级为调用链定位、补环境或解混淆。
5. 对高频场景，知道如何去重、过滤和绑定到具体请求。
