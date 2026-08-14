---
name: wechat-miniapp-reverse
description: >-
  【优先级：微信小程序任务必选】微信小程序 / WeChat Mini Program / WMPF 逆向调试。强触发关键词：微信小程序、PC微信小程序、WMPF、WeChatAppEx、AppService、WebView、127.0.0.1:62000、WMPFDebugger、小程序调试。使用 miniapp-reverse-mcp 通过 CDP 调试端口分析小程序网络请求、源码、断点、调用栈和加密参数入口。不要被 camoufox-js-reverse 抢占。不要用于：普通 Web API 签名（转 camoufox-js-reverse 或 web-protocol-recovery）、浏览器 hook 脚本、Node.js 补环境、iv8 请求脚本、AST 解混淆或瑞数骨架任务。
argument-hint: "[小程序名称/目标行为/API关键词/加密参数]"
compatibility: "需要已注册的 miniapp-reverse-mcp；WMPFDebugger 依赖应已集成到 <WMPFDebugger_ROOT>/node_modules，不检查或安装 yarn/node_modules/frida"
---

# WeChat Miniapp Reverse

## 目标

使用本机 `miniapp-reverse-mcp` 通过 WeChat Mini Program 的 CDP 调试端口，定位小程序里的网络请求、脚本源码、断点上下文、调用栈、Runtime 事件、Profiler 证据和 WebSocket 数据。

本 skill 是微信小程序运行时调试 skill，不是普通 Web 站点逆向 skill，也不是离线协议复现 skill。

## 触发边界

使用本 skill 当用户提到以下任一目标：

- 微信小程序、PC 微信小程序、微信开发者工具小程序、WMPF、WeChatAppEx、AppService、WebView。
- 需要抓小程序 XHR/Fetch/WebSocket 请求、响应体、POST body、请求 initiator、调用栈、ExtraInfo、失败原因。
- 需要在小程序 JS 源码里搜索函数/参数、读取脚本片段、保存脚本源码。
- 需要在小程序运行时设置 XHR 断点或文本断点，查看 paused scope 变量。
- 需要捕获 Runtime console/exception/context，或用 CPU Profiler/coverage 定位热点函数和执行脚本。
- 需要设置 DOM event listener breakpoint 分析点击、输入、提交等事件入口。
- 需要切换 AppService/WebView target 来分析逻辑层或渲染层。
- 用户给的是小程序页面行为、接口关键词、加密参数名，但没有普通浏览器页面 URL。

不要使用本 skill：

- 普通 Web 页面/API 签名、反爬、挑战页、浏览器环境指纹逆向 → `camoufox-js-reverse` 或 `web-protocol-recovery`。
- 只要一段 Console/Snippets hook 脚本 → `browser-hook-snippets`。
- 已有 JS 入口，要在 Node.js/vm 中补环境跑通 → `env-patch`。
- 明确要 Python + iv8 + requests 脚本 → `iv8-web-reverse`。
- 整文件 AST 解混淆、控制流还原 → `ast-deobfuscate`。
- 普通 Web 瑞数/Ruishu/Rivers 任务不属于小程序调试：入口/调用链定位 → `camoufox-js-reverse`；已有 JS 入口要在 Node.js/vm 跑通 → `env-patch`；明确 Python + iv8 或 URL 后缀可用性 → `iv8-web-reverse`；完整协议采集器 → `web-protocol-recovery`。

## 启动前置

不要检查或安装 WMPFDebugger 的 yarn、`node_modules`、frida 等依赖；这些依赖应已集成在用户本机的 `<WMPFDebugger_ROOT>/node_modules`。

本前置流程只检查 WMPFDebugger 调试服务是否已启动；如果服务没启动，直接启动它。

先定位 `<WMPFDebugger_ROOT>`，不要写死机器路径；优先复用本机缓存：

1. 先读取本 skill 目录下的 `local.config.json`。如果存在 `wmpfDebuggerRoot`，且该目录包含 `package.json`、`src/index.ts`、`node_modules/`，直接复用该路径。
2. 如果缓存不存在或校验失败，再检查当前工作目录本身是否包含 `package.json` 和 `src/index.ts`，且项目名/README 表明是 WMPFDebugger。
3. 否则检查当前工作目录的父目录、兄弟目录中是否存在名为 `WMPFDebugger` 的目录，且包含 `package.json`、`src/index.ts`、`node_modules/`。
4. 如果仍找不到，向用户问一句：`WMPFDebugger 根目录在哪里？`，不要猜测固定盘符路径。
5. 用户提供路径后，先校验该目录包含 `package.json`、`src/index.ts`、`node_modules/`；校验通过则写入本 skill 目录下的 `local.config.json`，格式为 `{ "wmpfDebuggerRoot": "..." }`，后续启动直接复用。

`scripts/start-wmpf-debugger.cmd` 已内置同样的 root 定位顺序；首次运行没有 `local.config.json` 时可以直接无参数调用，脚本找不到 root 才会返回需要询问用户的提示。
`local.config.json` 是本机私有缓存，可能包含用户机器上的绝对路径；不要提交、打包或复制给其他用户，分发 skill 时应排除该文件。
启动脚本会隐藏长期运行的后台窗口，只把输出写入 `<WMPFDebugger_ROOT>\wmpf-debugger.log`；如果看到无信息黑窗口，优先检查是否绕过脚本直接运行了 raw `cmd`/`start` 命令。

每次使用 `miniapp-reverse-mcp` 前，先确认 WMPFDebugger 调试服务是否已启动，但不要在用户打开小程序前抢跑 target 枚举：

1. 如果近期没有服务状态证据，轻量检查 `127.0.0.1:62000` 是否拒绝连接；可以用一次 `miniapp-reverse-mcp_list_targets()` 仅区分“连接拒绝/服务未启动”和“服务已启动但暂无 target”。
2. 如果连接失败或报错类似连接拒绝，启动 WMPFDebugger 调试服务：优先运行本 skill 附带的 `scripts/start-wmpf-debugger.cmd [<WMPFDebugger_ROOT>]`；不传参数时脚本会复用 `local.config.json`、当前目录、父目录和兄弟 `WMPFDebugger` 目录定位 root，找不到会快速返回提示，此时再向用户询问。不要把 raw `start` 命令直接放进当前工具调用，除非用户要求在自己的终端手动执行；不要追加 `&& ping`、`timeout`、`tail -f`、持续 `type` 日志或任何长轮询等待。
3. 启动后最多做 2 次短探测：用 `Grep` 查 `wmpf-debugger.log` 中的 `proxy server running` 或 `you can now open any miniapps`，或用一次短超时端口检查；总等待预算控制在 5 秒以内。看到 ready 日志后，立即停止进一步 target/network MCP 调用，提示用户先打开/重新打开目标小程序；5 秒内未 ready 时，报告日志路径并让用户稍后重试，不要继续卡住当前回合。
4. 只有用户明确说“已打开”、已经给出目标小程序正在运行、或已经触发了目标行为后，才调用 `miniapp-reverse-mcp_list_targets()` 建立 target 上下文。
5. 如果服务已启动但 `list_targets` 超时，不要反复重试堵塞；说明“服务已启动，等待目标小程序接入”，让用户重新打开小程序后再枚举。

推荐启动命令（在本 skill 目录下的相对脚本，能立即返回当前工具调用）：

```cmd
call scripts\start-wmpf-debugger.cmd ["<WMPFDebugger_ROOT>"]
```

不要在 `SKILL.md` 中写死某台机器上的绝对路径；如果当前运行环境需要绝对路径，运行时用本 skill 的实际 base directory 拼接 `scripts\start-wmpf-debugger.cmd`。
通过 `bash`/`cmd` 工具调用 `.cmd` 或 `.bat` 时必须使用 `call`，避免当前 shell 把 batch 内容误解析。

如果用户坚持手动启动，只建议用户在自己的独立终端执行等价命令；助手不要把 raw `start` 命令作为工具调用运行。需要实时看日志时，另开终端读取 `<WMPFDebugger_ROOT>\wmpf-debugger.log`，不要把长期运行服务或日志跟随挂在当前 `bash`/shell 工具调用里。

连接成功后的 UI 快路径：一旦 `miniapp-reverse-mcp_list_targets()` 成功返回 target，直接把 `devtools://devtools/bundled/inspector.html?ws=127.0.0.1:62000` 发给用户自行打开。不要调用浏览器 MCP 的 new_page/导航工具打开普通 Chrome 页面，不要检测 `about:blank`，不要追问“是否看到 UI”。只有用户明确说链接打不开时，才给出系统浏览器兜底命令或让用户手动复制 URL。发出链接后停止自动分析，向用户询问：要抓的数据字段、API URL、请求/响应样本，或具体业务动作。

目标确认闸门：用户没有给字段、API、请求样本或明确业务动作前，不要自动盲抓网络、切换多个 target、搜索源码、保存脚本或下断点。允许做的仅限于确认服务、确认 target、打开 UI、报告当前状态和等待用户目标。

工作目录：

```text
<WMPFDebugger_ROOT>
```

## 能力矩阵

按用户目标选择工具，不要只按清单顺序机械调用：

| 用户目标 | 首选工具链 | 关键参数/停止条件 |
|---|---|---|
| 确认服务和 target | `miniapp-reverse-mcp_list_targets` → `miniapp-reverse-mcp_switch_target` | 多 target 时先让用户确认 AppService/WebView；选定后停止切换 |
| 打开调试界面 | 直接输出 DevTools URL | 不调用浏览器 MCP；用户明确说打不开时才给兜底命令 |
| 抓取目标请求 | `miniapp-reverse-mcp_list_network_requests` | 先用 `include_preserved_requests=True` 查历史保留请求，再用 `wait_ms=1000~5000` 等实时请求；有接口关键词/域名/路径时必须先带 `url_filter` |
| 查看请求详情/响应 | `miniapp-reverse-mcp_list_network_requests(reqid=...)` → `miniapp-reverse-mcp_get_response_body` | 响应为空或未完成时检查 `loadingFailed` / preserved 请求，再让用户重新触发行为 |
| 获取 POST body | `miniapp-reverse-mcp_get_request_post_data` | 当列表里的 request body 被截断、缺失或需要 CDP 原始 POST 数据时使用 |
| 判断请求失败原因 | `miniapp-reverse-mcp_list_network_requests(reqid=...)` | 优先看 ExtraInfo、`loadingFailed.failure`、blocked/cors/canceled 证据，不凭状态码猜测 |
| 找请求入口调用栈 | `miniapp-reverse-mcp_get_request_initiator` → `miniapp-reverse-mcp_get_script_source` | 有 URL/line/column 后读取上下文，不急着下断点 |
| 搜索参数或函数 | `miniapp-reverse-mcp_list_scripts` → `miniapp-reverse-mcp_search_in_sources` → `miniapp-reverse-mcp_get_script_source` | 搜索顺序：接口路径 → 参数名 → header → 函数名 → 业务词 |
| 保存大脚本 | `miniapp-reverse-mcp_save_script_source` | 写文件前说明保存路径和原因，获得用户确认 |
| XHR 断点 | `miniapp-reverse-mcp_break_on_xhr` → 触发行为 → `miniapp-reverse-mcp_get_paused_info` | URL 片段要尽量窄；命中后先看 scope/stack |
| DOM 事件入口 | `miniapp-reverse-mcp_set_event_listener_breakpoint` → 触发事件 → `miniapp-reverse-mcp_get_paused_info` | 适合 click/input/submit/key*，命中后及时 resume 并清理 |
| 代码文本断点 | `miniapp-reverse-mcp_get_script_source` → `miniapp-reverse-mcp_set_breakpoint_on_text` | 只对函数体内部具体语句下断点，不对函数名/赋值语句下断点 |
| paused 求值/单步 | `miniapp-reverse-mcp_evaluate_script` → `miniapp-reverse-mcp_step` → `miniapp-reverse-mcp_resume_execution` | 优先在当前 `frame_index` 求值；分析完及时 resume |
| 断点盘点/清理 | `miniapp-reverse-mcp_list_breakpoints` → `miniapp-reverse-mcp_remove_breakpoints` | 换 target、任务结束或跑偏前先清理 |
| Runtime 事件 | `miniapp-reverse-mcp_get_runtime_events` | `event_type` 选 `console` / `exception` / `context`；异常先看堆栈和 executionContext |
| CPU 热点定位 | `miniapp-reverse-mcp_start_cpu_profile` → 触发行为 → `miniapp-reverse-mcp_stop_cpu_profile` | 用于 JSVMP 循环、签名函数热点、重型计算入口；不要长时间开启 |
| 覆盖率定位 | `miniapp-reverse-mcp_precise_coverage(action='start'|'take'|'stop')` | 触发目标行为后看哪些脚本/函数实际执行 |
| WebSocket 分析 | `miniapp-reverse-mcp_get_websocket_messages` | 先列连接，再看 handshake、frame error；用 `wsid`、`direction`、`show_content=True` 看内容 |
| 资源释放 | `miniapp-reverse-mcp_resume_execution` → `miniapp-reverse-mcp_list_breakpoints` → `miniapp-reverse-mcp_remove_breakpoints(clear_all=True)` → 必要时 `scripts/stop-wmpf-debugger.cmd` | 代码落地并拿到 response、最终报告可完整复现请求链路、换任务或结束前必须执行 |

## 标准工作流

### 1. 建立目标上下文

仅在用户已经打开目标小程序后调用：

- `miniapp-reverse-mcp_list_targets()`：列出 AppService/WebView 目标，确认当前选中 target。
- 如默认 target 不对，调用 `miniapp-reverse-mcp_switch_target(target_id=...)`。
- target 成功返回后，直接输出 DevTools URL，不要调用浏览器工具打开 UI，也不要检测 UI 状态。
- UI 打开后询问用户要抓什么：字段名、API URL、请求/响应样本，或具体业务动作。

向用户简要说明当前分析的是 AppService 还是 WebView，并等待目标确认。

### 2. 观察网络请求

常规入口：

- 只有用户给了字段、API URL、请求/响应样本或明确业务动作后，才开始抓包、切 target、搜索源码或设置断点。
- 如果用户给了接口 URL、域名、路径、参数名或业务关键词，先用 `miniapp-reverse-mcp_list_network_requests(include_preserved_requests=True, url_filter=关键词, wait_ms=0~1000)` 查历史保留请求。
- 如果用户没有给关键词，先问一句目标动作或接口关键词；仍可用 `include_preserved_requests=True` 粗看最近请求，但不要只盯实时空缓冲区。
- 历史没有命中时，再提示用户重新触发目标动作，并用 `miniapp-reverse-mcp_list_network_requests(wait_ms=1000~5000, url_filter=关键词)` 等实时请求。
- 用 `reqid` 查看单条请求详情。
- 用 `miniapp-reverse-mcp_get_response_body(request_id=...)` 获取响应体。
- 请求 body 不完整或需要 CDP 原始 POST 数据时，用 `miniapp-reverse-mcp_get_request_post_data(request_id=...)`。
- 请求失败、CORS、blocked、cancelled 或状态异常时，先查看单条请求详情里的 ExtraInfo 和 `loadingFailed`，再判断是否需要切 target 或重放行为。
- 用 `miniapp-reverse-mcp_get_request_initiator(request_id=...)` 找发起调用栈。

如果实时没有请求，不要立刻判定“没有请求”；先检查 preserved 请求、切换 AppService/WebView target、再让用户复现目标动作。只有这些都无结果时，再进入源码关键词搜索。

### 3. 定位脚本与入口

使用：

- `miniapp-reverse-mcp_list_scripts(url_filter=...)`：列脚本。
- `miniapp-reverse-mcp_search_in_sources(query=...)`：搜索关键词、接口路径、参数名、函数名。
- `miniapp-reverse-mcp_get_script_source(...)`：读取命中上下文。
- `miniapp-reverse-mcp_save_script_source(...)`：只在需要整包或大文件时保存源码到用户工作区。

搜索优先级：接口路径片段 → 参数名 → header 名 → 加密函数名 → 业务关键词。

### 4. 动态断点分析

设置断点前先读取函数体上下文，不要直接在函数名或赋值语句上下断点。

可用工具：

- `miniapp-reverse-mcp_break_on_xhr(url=...)`：按接口 URL 片段打 XHR/Fetch 断点。
- `miniapp-reverse-mcp_set_event_listener_breakpoint(event_name=..., target_name=...)`：按 DOM 事件入口打断点，如 `click`、`input`、`submit`、`keydown`。
- `miniapp-reverse-mcp_remove_event_listener_breakpoint(event_name=..., target_name=...)`：移除 DOM 事件入口断点。
- `miniapp-reverse-mcp_set_breakpoint_on_text(text=...)`：对函数体内部具体语句打文本断点。
- `miniapp-reverse-mcp_list_breakpoints()`：查看当前 XHR/代码断点，避免重复设置或漏清理。
- `miniapp-reverse-mcp_get_paused_info(include_scopes=True)`：查看调用栈和局部变量。
- `miniapp-reverse-mcp_evaluate_script(expression=..., frame_index=...)`：在 paused frame 中求值。
- `miniapp-reverse-mcp_step(action="over"|"into"|"out")`：单步。
- `miniapp-reverse-mcp_resume_execution()`：恢复执行。
- `miniapp-reverse-mcp_remove_breakpoints(clear_all=True)`：任务结束或换目标前清理断点。

### 5. Runtime 与 Profiler 证据

用于网络/源码定位不够直接时补强运行时证据：

- `miniapp-reverse-mcp_get_runtime_events(event_type="console"|"exception"|"context")`：查看 console、异常和 execution context。
- `miniapp-reverse-mcp_start_cpu_profile()`：开始 CPU 采样，随后让用户触发目标动作。
- `miniapp-reverse-mcp_stop_cpu_profile(limit=...)`：停止采样并查看热点函数、脚本 URL、行列号。
- `miniapp-reverse-mcp_precise_coverage(action="start")`：开始覆盖率采集。
- `miniapp-reverse-mcp_precise_coverage(action="take"|"stop")`：查看目标动作实际执行过的脚本。

Profiler/coverage 不替代调用栈和断点；它们用于缩小搜索范围，拿到脚本 URL/行列号后仍回到源码上下文或断点验证。

### 6. WebSocket 分析

使用：

- `miniapp-reverse-mcp_get_websocket_messages()`：列连接。
- `miniapp-reverse-mcp_get_websocket_messages(wsid=..., show_content=True)`：看消息。
- 列连接和查看单连接时优先看 handshake request/response headers、状态码和 frame error，再分析 payload。
- 用 `direction="sent"` 或 `direction="received"` 分离上下行。

### 7. 资源释放

满足任一条件时必须释放资源：用户代码已经落地并能实际拿到 response 响应数据；已经给出最终分析报告且可基于报告完整复现请求链路；用户要求结束/换目标/换 skill；当前任务需要转交 `web-protocol-recovery`、`camoufox-js-reverse` 或 `iv8-web-reverse` 继续实现。

释放顺序：

- 如果当前 paused，先调用 `miniapp-reverse-mcp_resume_execution()` 恢复执行。
- 调用 `miniapp-reverse-mcp_list_breakpoints()` 查看残留断点。
- 如存在断点，调用 `miniapp-reverse-mcp_remove_breakpoints(clear_all=True)` 清理所有 XHR/代码断点。
- 如设置过 DOM event listener breakpoint，调用 `miniapp-reverse-mcp_remove_event_listener_breakpoint(...)` 清理事件断点。
- 如开启过 CPU profiler 或 precise coverage，分别调用 `miniapp-reverse-mcp_stop_cpu_profile()` 或 `miniapp-reverse-mcp_precise_coverage(action="stop")` 停止采集。
- 不再保留会影响后续小程序运行状态的断点、paused 状态或临时 target 切换假设。
- 如果 WMPFDebugger 服务是本轮由助手启动的，且已经代码落地拿到 response、最终报告可完整复现链路、用户要求结束或任务转交完成，必须调用 `scripts/stop-wmpf-debugger.cmd` 停止 `127.0.0.1:62000` 后台进程，不再额外等待用户确认。
- 如果 WMPFDebugger 服务是用户原本已启动的，只清理 MCP 调试状态，不主动关闭用户进程；除非用户明确要求停止服务。
- 停止后用一次短端口检查确认 `62000` 不再 LISTENING，并在最终报告写明 DevTools URL 已不可访问或服务仍由用户保留。

## 异常与确认

遇到下面情况时，不要盲目继续：

- `miniapp-reverse-mcp` 工具不可用或启动失败：先说明 MCP 未就绪，要求用户重启 opencode；不要改用普通 Web 逆向 MCP 冒充微信小程序调试能力。
- `127.0.0.1:62000` 连接失败：只启动 WMPFDebugger 调试服务；不要检查或安装 WMPFDebugger 依赖；启动必须优先使用 `scripts/start-wmpf-debugger.cmd`，避免 `start /B`、raw `start` 工具调用或直接运行 `npx ts-node src/index.ts` 卡住工具调用。
- 启动服务时弹出无信息黑窗口：说明可能没有使用隐藏窗口脚本，后续必须改用 `scripts/start-wmpf-debugger.cmd`；不要为了看日志保留黑窗口，日志统一查看 `wmpf-debugger.log`。
- 启动服务后等待过久：立即停止继续等待，改为短探测日志/端口并向用户说明当前状态；不要为了“确认 ready”而让工具调用阻塞超过 5 秒。
- `list_targets` 为空：提示用户重新打开目标小程序，再重试 target 枚举。
- 出现多个可疑 target：先列出 title/url/type，让用户确认要分析 AppService 还是某个 WebView；不要随机切换。
- `save_script_source` 会写文件，或 `set_breakpoint_on_text` / `break_on_xhr` 会改变运行状态：先说明影响并获得用户确认。
- 任务结束、换 target、用户要求停止、代码已拿到 response、或最终报告已能完整复现请求链路时，执行“资源释放”流程。

## 输出要求

每次分析结束，优先给用户这些结果：

- 当前 target：AppService/WebView、target id、URL/title。
- 关键请求：method、URL、reqid、状态、响应摘要。
- 入口证据：initiator 调用栈、脚本 URL、行列号、关键函数/语句。
- 动态证据：断点处参数、局部变量、返回值或相关表达式求值。
- 收尾状态：是否已恢复 paused、是否已清理断点、是否保留或停止 WMPFDebugger 服务。
- 下一步：继续断点、保存源码、切换 target，或选择实现路线。

## 后续路线选择

当需要在多个实现 skill 之间选择时，优先调用 `question` 工具提供键盘上下选择，不要只用自然语言让用户输入。默认候选：`web-protocol-recovery`、`camoufox-js-reverse`、`iv8-web-reverse`、`继续小程序断点分析`。如果用户环境没有某个候选 skill，允许用户通过自定义答案输入实际 skill 名称；收到新名称后，维护者应把它追加到本节默认候选，后续同类任务直接展示为可选项。

如果已经得到接口、签名、cookie/header、调用栈等可实现证据，必须用 `question` 工具让用户用键盘上下选择后续实现路线，不要只让用户打字：

- `web-protocol-recovery`：恢复成 browser-free 的纯协议 Python 采集器，适合已经能还原完整请求链路、目标是脱离微信运行。
- `camoufox-js-reverse`：继续用浏览器/小程序动态证据定位复杂签名、环境或 JSVMP 逻辑，适合算法还没完全闭环。
- `iv8-web-reverse`：用 Python + iv8 执行小程序/浏览器侧 JS，再用 requests 回放，适合想快速桥接已有 JS 生成 token/header。
- `自定义 skill 名称`：如果用户环境没有上述 skill，允许用户在 `question` 的自定义答案里输入 skill 名称；收到后把该名称追加到当前 skill 的候选路线描述中，下一次同类任务直接作为可选项展示。

不要替用户默认选择其中一种；列出当前证据是否足够，并让用户选择。转交前如果当前微信小程序调试任务已经形成可复现链路，先执行“资源释放”流程。

## 更新记录

| 日期 | 要点 |
|---|---|
| 2026-06-21 | 对齐 `miniapp-reverse-mcp` 新能力：AppService 默认优先、Network ExtraInfo/loadingFailed、CDP 原始 POST body、Runtime console/exception/context、CPU Profiler、precise coverage、DOM event listener breakpoint、WebSocket handshake/frame error、断点/资源释放约束。 |

## 注意事项

- WMPFDebugger 调试服务必须在目标小程序启动前完成；如果用户操作顺序反了，建议重新启动 WMPFDebugger 服务并重新打开小程序。
- 看到 `you can now open any miniapps` 只代表调试服务已准备好，不代表 target 已接入；此时不要反复枚举 target，等待用户打开目标小程序。
- 默认 CDP endpoint 是 `devtools://devtools/bundled/inspector.html?ws=127.0.0.1:62000`。
- 当前 `miniapp-reverse-mcp` 工具集不负责打开浏览器界面；默认只输出 DevTools URL 让用户手动打开，避免 UI 检测和 `about:blank` 往返浪费时间。
- `miniapp-reverse-mcp` 不负责启动微信或选择具体小程序；用户需要手动打开目标小程序并触发行为。
- 如果用户最终目标变成“写一个脱离微信/浏览器的 Python 协议采集器”，将已有请求、脚本、调用栈证据转交给 `web-protocol-recovery` 或 `iv8-web-reverse`。
