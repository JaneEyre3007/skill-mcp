# JS Reverse Workflow

<!-- 共享协议：此文件与 ast-deobfuscate / browser-hook-snippets / camoufox-js-reverse / env-patch / iv8-web-reverse / rs-reverse / web-protocol-recovery 中的副本须保持同步，修改时一并更新。 -->

这份共享参考用于串联 `rs-reverse`、`camoufox-js-reverse`、`browser-hook-snippets`、`env-patch`、`ast-deobfuscate`、`iv8-web-reverse` 和 `web-protocol-recovery`。它不是独立 skill，而是前端 JS 逆向任务的阶段协议。

## 阶段

1. `Observe`：确认目标请求、关键脚本、候选函数、触发动作。
2. `Capture`：用最小 hook 或断点采样真实参数、调用顺序和中间值。
3. `Rebuild`：把页面证据导出为本地 Node 可运行入口。
4. `Patch`：按诊断报告和 `first divergence` 最小补环境。
5. `Consolidate`：补环境通过后，固定 fixture、收口本地可复现入口，并沉淀后续移植所需事实。
6. `Port`：Node 侧本地复现稳定后再迁移到 Python 或其他宿主。

## Front Door

先按当前工程状态判题，再决定进入哪个阶段，不要只靠线索词路由。

1. `412`、`token`、`worker`、`wasm`、`JSVMP`、`cookie` 这类词只能帮助缩小问题域，不能直接替代阶段判断。
2. 明确出现瑞数/Ruishu/Rivers，或 `412/403` 同时伴随 `$_ts`、`r2mKa`、`Cookie S/T`、`meta[r=m]` 等瑞数证据时，先判断交付目标；固定项目结构、首跳材料缓存、基础 Node runner 或最小 proxy 观察才进入 `rs-reverse`。
3. 先回答：真实请求是否已确认、上游依赖是否真实、写边界是否已证明、当前主阻塞是定位/壳层/运行时/验证哪一类。
4. 只有当前阶段的退出条件满足后，才进入下一阶段。

## Complexity

复杂任务可先做轻量复杂度分级，用来校准工件深度，但不直接覆盖阶段路由：

1. `L1 Transparent chain`：明文拼接、简单映射、无混淆、无环境依赖。
2. `L2 Single-layer shell`：简单混淆、webpack 包裹、单层 crypto 调用。
3. `L3 Multi-layer shell + env`：`JSVMP` / `wasm` / `worker` / 环境依赖分支 / 反调试。
4. `L4 Adversarial protection`：多跳 cookie、动态下发、反调试、指纹分支、强风控链路。

经验规则：

1. L1/L2 可以使用简化交接卡。
2. L3/L4 默认需要完整证据工件、阶段记录和验证闭环。
3. 复杂度可以在新证据出现后上调；没有证据不要下调。

## 阶段切换

1. 没有确认目标请求和脚本，不进入补环境。
2. 没有真实运行样本，不开始本地 rebuild。
3. 没有本地可运行入口和诊断报告，不盲补宿主对象。
4. 没有 `env rebuild` 跑通、服务端验收和固定 fixture，不进入收口与移植准备阶段。
5. 没有稳定的 Node 侧 fixture 对齐结果，不直接写 Python / execjs 版本。

用户提到后续阶段关键词时，以当前证据满足的阶段为准，而不是以关键词为准。例如"想补 window/document 但不知道入口"仍回到 `Observe`；"env 还没跑通但想写 Python execjs"仍停在 `Patch`。

## 阶段间交接数据契约

在 skill 之间传递任务时，前一阶段的退出产物即后一阶段的准入输入。下游在接收任务时应对必填字段做校验。

### Observe → Capture

上游: `camoufox-js-reverse` / `rs-reverse`
下游: `browser-hook-snippets`

| 字段 | 类型 | 说明 |
|---|---|---|
| `target_url` | string | 目标请求完整 URL |
| `target_method` | string | GET / POST |
| `target_fields` | string[] | 需追踪的字段名（如 `["x-sign","X-t"]`） |
| `suspect_scripts` | string[] | 候选脚本 URL 列表 |
| `entry_candidates` | {url,line,fn}[] | 候选入口函数位置 |
| `injection_timing` | string | 推荐 hook 注入时机 |

### Capture → Rebuild

上游: `browser-hook-snippets` / `camoufox-js-reverse`
下游: `env-patch`

| 字段 | 类型 | 说明 |
|---|---|---|
| `entry_function` | string | 确认的入口函数签名 |
| `entry_script_url` | string | 入口所在脚本完整 URL |
| `entry_script_local` | string | 本地保存路径（`js_reverse_cache/` 下） |
| `sample_input` | any | 采样到的真实入参 |
| `sample_output` | any | 采样到的真实输出 |
| `env_reads` | string[] | 脚本实际读取的全局对象路径 |

### Rebuild → Patch

上游: `env-patch`
下游: `env-patch`（内部迭代）

| 字段 | 类型 | 说明 |
|---|---|---|
| `undefined_paths` | string[] | env-diagnose.js 输出的缺失属性路径 |
| `first_divergence` | {path,expected,actual} | 浏览器 vs 本地首次差异位置 |
| `loaded_modules` | string[] | 已加载的 env 模块列表 |

### Patch → Consolidate

上游: `env-patch`
下游: `env-patch`（收口）

| 字段 | 类型 | 说明 |
|---|---|---|
| `stable_sign` | string | 稳定生成的签名值 |
| `stable_cookie` | string | 稳定生成的 cookie 字符串 |
| `fixture_input` | json | 固定输入样本 |
| `fixture_output` | json | 固定预期输出 |
| `server_validated` | boolean | 至少一次服务端验收通过 |

### Consolidate → Port

上游: `env-patch` / `rs-reverse`
下游: `iv8-web-reverse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `fixture_input` | json | 从 Node 侧传递的固定输入 |
| `fixture_output` | json | 从 Node 侧传递的固定输出 |
| `session_cookies` | dict | 已持有的 challenge cookie |
| `challenge_html_path` | string | challenge 页面 HTML 本地路径（若有） |
| `runner_js_urls` | string[] | 外链保护 JS URL 列表（若有） |
| `cookie_keys` | string[] | 需续持的 cookie 名 |

交接卡按本表字段保存到 `js_reverse_cache/tasks/<id>/handoff.json`。上游负责写入，下游负责校验必填字段。

## 证据产物

逆向分析过程中如果需要产出临时文件、抓包证据、下载脚本、格式化源码、运行产物或中间数据，统一写入"执行代码的工作区"下的 `js_reverse_cache/` 文件夹；如果 `js_reverse_cache/` 不存在，先创建这个文件夹再写入。

不要自行把逆向数据写到执行代码工作区之外的位置。

复杂或可续做任务优先沉淀到 `js_reverse_cache/tasks/<task-id>/` 或项目等价目录：

1. `task.json`：目标、阶段、成功标准。
2. `network.jsonl`：目标请求、响应摘要、initiator 线索。
3. `scripts.jsonl`：关键脚本、行列号、候选函数。
4. `runtime-evidence.jsonl`：hook、断点、调用栈、中间值。
5. `env/entry.js`：本地加载入口。
6. `env/env.js`：基础宿主对象和最小 shim。
7. `env/polyfills.js`：代理诊断、函数伪装和缺函数壳 helper。
8. `env/capture.json`：浏览器侧固定样本和状态摘要。
9. `report.md`：当前阶段、结论、first divergence、验证结果。

如果当前任务更偏"请求链定位和会话续接"，至少维护一个轻量交接文档，例如 `js_reverse_cache/tasks/<id>/handoff.json`，用来持续记录：目标请求、目标字段、样本编号、证据编号、来源链、去向链、未闭环项。

不要把真实 cookie、token、完整可复用签名链路写进公开 case 或通用模板。真实任务证据默认留在 task-local 目录。

## Handoff

跨会话或跨阶段继续时，优先留下最小交接卡，而不是只留散落结论：

```text
Complexity:
Current stage:
Why this stage now:
Required artifact:
Exit condition:
Next evidence needed:
```

对于以请求链为主的任务，交接卡应指向 `js_reverse_cache/tasks/<id>/handoff.json` 或等价工件；对于运行时差异任务，交接卡应指向 `runtime-evidence`、`first divergence` 记录或验证夹具。

## First Divergence

`first divergence` 是当前本地复现与浏览器真值最早出现差异的位置。补环境时必须先定位它，再只补对应的最小因果单元。

一个最小因果单元可以是：

1. 一个基础值，如 `navigator.userAgent`。
2. 一个函数壳，如 `document.createElement`。
3. 一个函数返回对象，如 canvas context 的最小结构。
4. 一个不可拆的对象契约，如 `localStorage.getItem/setItem/removeItem`。

每轮补丁都要记录：触发日志、对应页面证据、补丁原因、复测结果、`first divergence` 是否前移。

## Consolidate 准入

只有同时满足这些条件，才进入 `Consolidate`：

1. 目标请求、脚本、关键入口已确认。
2. 本地 `env rebuild` 已稳定跑通目标链路。
3. 至少有一次服务端验收通过。
4. 已记录至少一条 `first divergence` 及修复路径。
5. 已固定一条 fixture，包括输入、关键中间值、最终输出、时间/随机/版本边界。

收口顺序固定为：先稳定 Node 侧复现，再迁移到 Python 或其他宿主。不要在补环境阶段直接跳到 Python `execjs` 调试。

## Skill 路由

1. 瑞数/Ruishu/Rivers 或 `412/403` 加瑞数证据，且目标是固定项目结构、首跳材料缓存、基础 Node runner 或最小 proxy 观察：用 `rs-reverse`。
2. 要找参数入口、脚本位置和调用链：用 `camoufox-js-reverse`。
3. 只缺一个浏览器观察 hook：用 `browser-hook-snippets`。
4. 入口已知，要在 Node.js 中复现：用 `env-patch`。
5. Python + iv8 运行时复现：用 `iv8-web-reverse`。
6. 目标是源码结构化还原：用 `ast-deobfuscate`。
7. 需要端到端协议恢复（多层交织，最终交付 Python 采集器）：用 `web-protocol-recovery`。
