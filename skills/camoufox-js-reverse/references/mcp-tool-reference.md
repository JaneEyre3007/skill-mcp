# MCP 工具分类索引（v1.1.0）

> 本文只保留 `camoufox-reverse-mcp` 当前可调用工具，避免 AI 误调旧接口。SKILL.md 核心层优先；本文作为详细速查。

## Browser

| 工具 | 用途 |
|---|---|
| `launch_browser` | 启动 Camoufox；引擎追踪需 `enable_trace=True` |
| `close_browser` | 关闭浏览器并释放资源 |
| `navigate` | 导航，支持 `pre_inject_hooks`、`wait_until`、响应链追踪 |
| `reload` | 刷新当前页面 |
| `click` / `type_text` / `wait_for` | 页面交互 |
| `get_page_info` | URL、标题、窗口和屏幕信息 |
| `take_screenshot` / `take_snapshot` | 截图 / 无障碍树 |

## JavaScript

| 工具 | 用途 |
|---|---|
| `evaluate_js` | 页面上下文执行 JS；Firefox Xray 下页面全局函数常需 `window.wrappedJSObject` |
| `scripts(action='list')` | 列出脚本 |
| `scripts(action='get', url=...)` | 获取脚本源码；内联脚本用 `inline:<index>` |
| `scripts(action='save', url=..., save_path=...)` | 保存脚本源码 |
| `search_code(keyword, script_url=...)` | 搜索已加载脚本；大文件建议传 `script_url` |

## Network

| 工具 | 用途 |
|---|---|
| `network_capture(action='start', capture_body=True)` | 开始抓包 |
| `network_capture(action='status'|'clear'|'stop')` | 查看、清理、停止抓包 |
| `list_network_requests` | 列出请求，支持 URL/method/type/status 过滤 |
| `get_network_request` | 获取请求详情、headers、body、post data |
| `get_request_initiator` | 获取请求调用栈；当前 Firefox/Camoufox 下不稳定，必须准备降级路径 |
| `intercept_request(action='log'|'block'|'modify'|'mock'|'stop')` | 拦截、修改、mock 或停止路由 |

## Hook

| 工具 | 用途 |
|---|---|
| `inject_hook_preset` | 注入 xhr/fetch/crypto/websocket/debugger_bypass/cookie/runtime_probe 预设 |
| `hook_function(mode='trace')` | 函数追踪；对 `window.fetch` 等可解析路径更可靠 |
| `hook_function(mode='intercept', position=..., hook_code=...)` | before/after/replace 自定义 Hook |
| `remove_hooks` | 移除 Hook |
| `get_console_logs(level=..., keyword=..., clear=...)` | 读取控制台日志；没有 `type_filter` 或 `limit` 参数 |

## JSVMP / Instrumentation

| 工具 | 用途 |
|---|---|
| `trace_property_access` | 引擎级 DOM 属性追踪；需定制版浏览器 + `enable_trace=True` |
| `hook_jsvmp_interpreter(mode='transparent')` | 低风险页面侧 JSVMP 探针 |
| `hook_jsvmp_interpreter(mode='proxy', track_props=True)` | 高覆盖但高风险，可能挂浏览器，仅明确需要时使用 |
| `evaluate_js("window.__mcp_jsvmp_log")` | 读取页面侧 JSVMP 探针日志 |
| `instrumentation(action='install', url_pattern=..., mode=..., tag=...)` | HTTP 层源码插桩 |
| `instrumentation(action='log', tag_filter=..., type_filter=..., limit=...)` | 获取插桩日志 |
| `instrumentation(action='status'|'stop'|'reload')` | 查看、停止、重载插桩 |

## Environment / State

| 工具 | 用途 |
|---|---|
| `compare_env` | 采集浏览器环境指纹基准 |
| `export_fingerprint_profile` | 导出 Camoufox 运行时指纹 profile |
| `cookies(action='get'|'set'|'delete')` | Cookie 管理 |
| `get_storage` | 读取 localStorage/sessionStorage |
| `export_state` / `import_state` | 导出/导入浏览器状态；导入会切换 context |
| `reset_browser_state` | 清理 MCP 残留状态 |
| `check_environment` | MCP、依赖、浏览器、trace 状态自检 |

## Verify

| 工具 | 用途 |
|---|---|
| `verify_signer_offline` | 用用户提供样本离线验证签名函数；signer 入参是 sample 的 `input` 字段 |

## 使用原则

1. 新分析只使用本文列出的工具名和参数。
2. 请求调用栈获取失败时，降级到 `get_network_request`、`search_code`、`hook_function` 和 `get_console_logs` 组合分析。
3. 页面 HTML 用 `evaluate_js("document.documentElement.outerHTML")`。
4. JSVMP 日志用 `evaluate_js("window.__mcp_jsvmp_log")`，不要假设存在独立日志工具。
5. Cookie 归因用 `cookies(action='get')` + `get_console_logs(keyword='COOKIE-HOOK')` 手动合并判断。
