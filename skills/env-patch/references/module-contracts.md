# Env Patch Module Contracts

这份参考用于设计手写补环境模块或高级缓存区补丁，并最终合并到根目录 `mod.js`。它不是新的触发入口，也不替代 `scripts/vm-browser-gap-diagnose.js` 和现有 `env/` 模块树。

## 统一输入

1. `target`：当前要补的对象名或模块名。
2. `seed`：真实浏览器采集到的种子数据。
3. `runtime`：当前 Node.js / VM 里的运行时对象。
4. `diagnostics`：Proxy 吐环境日志、异常日志、堆栈、缺口清单。
5. `options`：开关项，如 `protectNative`、`strictDescriptor`、`logOpen`。

## 统一输出

1. `patchPlan`：本模块准备补哪些点。
2. `patchCode`：可执行补丁代码或代码片段。
3. `runtimeState`：补丁后应写入的运行态。
4. `validation`：本模块对应的检查点。
5. `residualRisk`：当前模块仍无法完全脚本化处理的风险。

## 常见模块边界

### `prototype-builder`

用于构造函数、原型链、实例创建、全局挂载。

验证点：`instanceof`、`Object.getPrototypeOf`、`constructor === Xxx`。

### `native-protector`

用于 `Function.prototype.toString`、getter/setter、`name`、`length` 保护。

验证点：`fn.toString()`、`fn.toString.toString()`、getter/setter `toString`、`name`、`length`。

### `descriptor-guard`

用于 `Object.getOwnPropertyDescriptor`、`defineProperty`、`propertyIsEnumerable`、`ownKeys` 对齐。

验证点：描述符形态、枚举性、Symbol 标记。

### `navigator-module`

输入通常包含 `seed.navigator`、`seed.plugins`、`seed.mimeTypes`、`seed.userAgentData`。

验证点：`navigator.webdriver`、`plugins.length`、`mimeTypes.length`、`getBattery`、`userAgentData`。

### `document-module`

输入通常包含 `seed.document`、cookie、query API 需求、`document.all` 特殊风险。

验证点：`document.URL`、`readyState`、`cookie`、`document.all`。

### `storage-module`

输入通常包含 `localStorage`、`sessionStorage`、cookie 状态。

验证点：`getItem/setItem/removeItem/key/length`、cookie 读写联动。

### `fingerprint-module`

输入通常包含 `screen`、canvas、WebGL、battery、window metrics。

验证点：canvas hash、WebGL vendor/renderer、`screen` 与窗口尺寸一致性。

### `crypto-module`

输入通常包含随机种子、是否需要 `subtle`、是否需要 `msCrypto`。

验证点：`crypto.getRandomValues` 类型检查、返回数组原对象、`subtle` 行为是否符合目标最低要求。

### `webrtc-module`

输入通常包含 `allowCandidateLeak`、SDP 模板、ICE candidate 策略。

验证点：`typeof RTCPeerConnection`、`createOffer()` 返回 Promise、默认不主动泄露真实候选信息。

### `worker-module`

输入通常包含 Worker 脚本 URL、inline source、广播频道名称。

验证点：`Worker`、`SharedWorker`、`MessagePort`、`MessageChannel`、`BroadcastChannel` 是否存在，以及最小 `postMessage` 通路。

### `profile-manager`

输入通常是浏览器采集 seed 或项目本地 profile JSON。Profile 不是“全量浏览器状态”，而是各模块可读取的默认值来源。

验证点：`window.__ProfileManager__.getProfileName()`、`navigator.userAgent`、`screen.width`、`window.innerWidth`、`location.href` 等是否来自同一份 profile。

## Gap Log 分析脚本

`scripts/gap-log-module-advisor.js` 可把 Proxy 观察日志或手工整理的缺口清单归并成推荐模块。

```bash
node <skill-dir>/scripts/gap-log-module-advisor.js js_reverse_cache/env/gap-log.json
```

输入可以是：

```json
{
  "logs": [
    { "type": "missing", "path": "window.navigator.webdriver" },
    { "type": "descriptor", "path": "document.all" }
  ]
}
```

输出重点看：

1. `recommendedModules`
2. `groupedByModule`
3. `nextActions`

## 浏览器种子采集

`scripts/browser-seed-collector.js` 是浏览器侧 snippet，用于 DevTools Console / Snippets。它只读取本地页面状态并打印 JSON，不做网络上传。

采集内容包含：navigator、document、location、history、screen、window metrics、cookie、storage、canvas/WebGL 摘要。

注意：采集结果可能含 cookie、storage、canvas 指纹等敏感信息，默认只保存到当前任务的 `js_reverse_cache/`，不要写入公开 case。
