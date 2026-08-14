---
name: iv8-web-reverse
description: >-
  交付紧凑可运行的 Python + iv8 + requests 脚本。用 iv8 执行浏览器侧 JavaScript，用 requests 或 curl_cffi 发真实 HTTP 请求。适合 h5st/a_bogus/BDMS改写URL/__zp_stoken__/挑战页cookie/瑞数XHR后缀/可信输入TDC、412/202/challenge 已确认用 iv8 执行 JS、已有浏览器环境样本需桥接到 iv8、把本 skill cases 案例改造为可运行脚本。动态素材写入当前工作区 js_reverse_cache/。不要用于：只定位 sign/token 入口或调用链（转 camoufox-js-reverse）、只要浏览器 hook 脚本（转 browser-hook-snippets）、AST 解混淆（转 ast-deobfuscate）、通用 Node.js 补环境（转 env-patch）、完整分层协议恢复（转 web-protocol-recovery）。瑞数/Ruishu/Rivers 只有目标是 iv8 runtime、challenge cookie、XHR 后缀或请求可用性复现时进入本 skill；Node/proxy 跑通转 env-patch。
argument-hint: "[目标 URL 或站点名]"
compatibility: "需要 Python 3 + iv8 + requests；可选 curl_cffi"
---

# iv8 Web Reverse

本 skill 只用于交付一个可运行的紧凑 Python 主脚本：用 `iv8` 执行浏览器侧 JavaScript，再用 Python `requests` 或必要时 `curl_cffi.requests` 发真实 HTTP 请求。默认可配套极小的 `utils/iv8_silent.py` 和 `utils/logger.py`，分别用于静默导入 iv8 和统一日志输出。

目标输出默认是 PyCharm 友好的紧凑主 `.py` 文件，不是框架、CLI 工具或通用模板集合。

## 硬性约束

- 自动下载或生成的目标站点动态材料统一写入当前工作目录的 `js_reverse_cache/`（不存在则先创建）。
- 不要把新任务的动态素材写入本 skill 目录或 `references/cases/`。只有用户明确要求"沉淀为案例"时才进入案例回写模式。
- 真实请求链路要保持同一个 `requests.Session` 中的 Cookie、动态 JS、签名参数、时间戳和后缀，不要混用旧值。
- 使用浏览器环境桥接时，一个 iv8 真实请求链路只能选择一个 `BROWSER_BASELINE` 来源；其它抓包、快照或日志只做诊断对照，不能把 UA、Cookie、screen、storage、TLS 等字段混拼进同一条链路。
- 如果没有可用的浏览器 baseline，使用用户提供的抓包/HTML/JS 样本或 iv8 默认 environment，并在报告里明确来源和缺口。
- 脚本和 utils 的输出规则见下方"输出规则"章节。

## 参考文件

本 skill 使用已复制进 skill 的真实案例、`references/api-examples/` 的 iv8 API 示例和 `references/api-inventory.md` 的 API 索引。

- `references/api-inventory.md`：iv8 API 索引和内置示例文件导读。
- `references/api-examples/README.md`：iv8 API 示例文件速查，只用于快速选择要读的 `.py` 示例。
- `references/api-examples/`：复制进 skill 的 iv8 API 示例 `.py` 文件，覆盖 context、environment、page.load、eventLoop、netLog、真实网络桥接、wrapNative、可信输入和 DevTools。
- `references/browser-iv8-bridge.md`：浏览器环境采样结果归一到 iv8 的四层流程、baseline 选择、`browser_env.json` schema 和 API 映射。
- `references/example-taxonomy.md`：真实 examples 的网站逆向分类。
- `references/script-writing-rules.md`：生成紧凑主脚本、`utils/iv8_silent.py`、`utils/logger.py`、缓存目录规则和写法约束。
- `references/case-ingestion-rules.md`：用户明确要求回写案例时，如何选择目录、复制 frozen 素材并更新 taxonomy；默认不脱敏、不截断，除非用户明确要求生成公开脱敏案例。
- `references/reverse-process/index.md`：真实案例的逆向过程索引；适配 bundled case 前先读它。若某案例没有对应逆向过程文档，则直接读 case `.py`。
- `references/cases/`：按类型分类保存的真实案例代码副本。
- `references/cases/js_reverse_cache/`：skill 自带的 frozen 示例素材，例如 JD h5st bundle、JD HTML、BDMS runtime。
- `references/js-reverse-workflow.md`：跨 skill 阶段协议。本 skill 主要覆盖 `Port` 阶段，把 Node 侧已稳定的链路用 iv8 + Python 做运行时复现和真实请求。

写代码前先看下方「## 案例选择」表格匹配目标类型，再读对应 `.py` 案例。需要 iv8 API 写法时读 `references/api-inventory.md` 或 `references/api-examples/`。如果任务启用浏览器环境桥接，还必须读取 `references/browser-iv8-bridge.md`。如果用户明确要求把本次成果回写为案例，还必须读取 `references/case-ingestion-rules.md`。

## 写代码前 Intake Gate

生成或改脚本前，先用 5 行记录本轮输入，不完整时先补材料或降级验证，不要直接套案例：

1. `artifact`: 已有 URL / HTML / JS / 抓包 / Cookie / 浏览器环境样本 / 真实响应是什么。
2. `target_type`: 签名、challenge cookie、browser token、network hook signing、captcha/TDC 或分页组合。
3. `baseline`: `browser` / `devtools` / `manual` / `default` 四选一；同一条链路只允许一个 baseline 来源。
4. `verification`: 只做 `py_compile`、只验证 iv8 生成链路、还是允许真实请求。
5. `nearest_case`: 选择的 bundled case 路径，以及为什么它最接近；没有匹配案例时说明采用哪个 iv8 API 示例起步。

如果用户没有给 JS/HTML/抓包/浏览器样本，也不允许真实请求，就先生成离线骨架和待补材料清单，不声称接口已跑通。

## 触发范围

使用本 skill 当用户目标包含：

- 明确要求 `Python + iv8 + requests` 跑浏览器 JS 并真实请求接口。
- 明确要求把本次 iv8 复现“沉淀为案例 / 回写到 skill / 新增 bundled case”。
- 需要 iv8 在浏览器态生成 cookie、`h5st`、`a_bogus`/BDMS 改写 URL、`__zp_stoken__`、动态 header/sign、动态 URL 后缀，然后由 Python 复现实请求。
- 改造本 skill `references/cases/` 里的真实案例为一个可直接运行的紧凑主脚本。
- 412/202/challenge 页面已确认要用 iv8 执行页面 JS 生成 cookie 或捕获 XHR 后缀。
- 已确认请求可用性依赖浏览器式页面执行、XHR 后缀或 iv8 runtime，且目标是用 iv8 执行链先跑通请求。
- 用户要求页码、关键词、pageSize、UA、URL 写在代码顶部，而不是终端参数。
- 需要 iv8 派发可信 mouse/pointer 事件采集 TDC/验证码行为数据。
- 用户已有浏览器环境样本，或明确要求把当前页面上下文中的 Cookie、UA、headers、storage、JS 可见环境值桥接到 iv8 复现。
- 没有可用浏览器环境样本但目标仍是 iv8 运行时复现时，允许先用用户提供的抓包/HTML/JS 样本或 iv8 默认 environment 起步，并在报告中说明残余风险。

不要使用本 skill 当：

- 只定位 sign/token/header 入口、脚本 URL、调用链。交给 `camoufox-js-reverse`。
- 普通 403/412/challenge 还没确认要用 iv8 跑，只是要入口定位或调用链。交给 `camoufox-js-reverse`。
- 只要浏览器 DevTools hook snippet。交给 `browser-hook-snippets`。
- AST 解混淆、控制流还原、字符串数组还原。交给 `ast-deobfuscate`。
- 通用 Node.js 补环境。交给 `env-patch`。
- 瑞数/Ruishu/Rivers 只是入口定位、首跳材料来源确认或调用链分析，交给 `camoufox-js-reverse`；只是 Node/proxy runner 跑通，交给 `env-patch`。
- 瑞数深度算法、r2mKa 字节码或 URL suffix AST 研究。不要由本 skill 接管；只有用户明确要求 iv8 runtime reproduction 或请求可用性复现时才留在本 skill。
- 目标不是紧凑 iv8 脚本而是完整分层协议恢复（多层加密+解码+传输包装），交给 `web-protocol-recovery`。
- 目标是微信小程序 / PC 微信小程序 / WMPF / WeChatAppEx 的运行时调试。交给 `wechat-miniapp-reverse`。

## 案例选择

写代码前先选择最接近的案例：

**快速匹配**（先看目标属哪类，再读对应 `.py`）：

| 目标类型 | 特征 | 参考案例 |
|---|---|---|
| 业务签名 header | 页面正常加载，XHR 带 sign/token/header | `signatures/` |
| 挑战 Cookie（412/202） | 首个请求返回 JS challenge，生成 Cookie 后才放行 | `js-challenges/` |
| 浏览器 Token | API 返回 seed + ts，JS 计算 token 后重试 | `browser-tokens/` |
| XHR Hook 改写 URL | SDK 拦截 XHR 并在 URL 追加签名参数 | `network-hook-signing/` |
| 验证码/可信输入 | TDC/滑块/点选，需要派发 pointer/mouse 事件 | `captcha/` |

- `references/cases/signatures/jd-h5st.py`：京东 `h5st`，本地 HTML + 本地 JS bundle + `MessageChannel` patch + 真实请求。
- `references/cases/signatures/nmpa-md5-cookie.py`：业务 MD5 header sign + challenge 页面 JS cookie。
- `references/cases/signatures/pdd-anti-content.py`：拼多多 PC 分类页 `anti_content`，动态下载当前 Next.js/webpack chunk，捕获 `__webpack_require__` 后调用内部混淆模块。
- `references/cases/signatures/xhs-homefeed.py`：小红书 PC homefeed，浏览器 webpack 模块导出 `signV2Init()`，iv8 中初始化 `window.mnsv2` 后生成 `X-s` / `X-S-Common`。
- `references/cases/js-challenges/chinatax-ruishu.py`：两阶段瑞数风格 cookie，然后 iv8 内触发 XHR 捕获带签名/后缀 URL。
- `references/cases/js-challenges/customs-ruishu.py`：两阶段瑞数风格 cookie + 捕获 URL/header/cookie 后重放。
- `references/cases/js-challenges/chng-ruishu-announcement.py`：华能电子商务 `412` 两阶段瑞数 Cookie，iv8 触发公告 JSON POST 并捕获 `kbfJdf1e` URL 后缀，分页用 `start=0,10,20...`。
- `references/cases/js-challenges/ouyeel-202-cookie-url.py`：HTTP 202 challenge，内联/外链 JS，load 事件，`netLog` URL suffix，`document.cookie`。
- `references/cases/js-challenges/cqvip-journal-search.py`：HTTP 412 challenge，iv8 生成 S/T cookie 后重放中文期刊搜索表单 POST。
- `references/cases/browser-tokens/zhipin-stoken.py`：API 返回 `seed/name/ts`，iv8 计算 `__zp_stoken__` 后重试。
- `references/cases/network-hook-signing/douyin-bdms.py`：BDMS/a_bogus 风格 runtime hook XHR 并改写 URL，从 `netLog` 读取最终 URL。
- `references/cases/captcha/tencent-tdc-slider.py`：腾讯 TDC，可信 pointer/mouse 事件、POW、`collect`/`eks`。

案例文件用于学习 API 和流程，不要盲目整站复制。必须替换当前目标站的 URL、headers、params、cookies、JS 入口和分页逻辑。

## 输出规则

- 默认生成一个短主 `.py` 脚本；同时生成 `utils/iv8_silent.py` 和 `utils/logger.py`。
- 顶部放可编辑常量，按需包含：`START_PAGE`、`PAGE_COUNT`、`PAGE_SIZE`、`KEYWORD`、`UA`、`PAGE_URL`、`API_URL`。
- 如果使用浏览器环境桥接，顶部还要放 `BROWSER_BASELINE = "browser"`、`"devtools"`、`"manual"` 或 `"default"`，以及 `BROWSER_ENV_PATH = CACHE_DIR / "browser_env.json"`，并说明切换 baseline 时要重新采集同一套 Cookie、UA、headers、storage 和环境值。
- 默认使用 `requests`；只有目标确实需要浏览器 TLS 指纹或原案例已经使用时才用 `curl_cffi.requests`。
- `loguru` 可选；默认在 `utils/logger.py` 中封装 `try loguru / PrintLogger`，不默认安装 `loguru`。
- 不添加 `logger.remove()` / `logger.add()`。
- 不添加 `sys.stdout.reconfigure(...)`。
- 主脚本用 `from utils.iv8_silent import import_iv8_silent` 和 `iv8 = import_iv8_silent()` 静默导入 `iv8`。
- 主脚本用 `from utils.logger import logger`，业务输出用 `logger.info(...)`。
- 业务流程附近写短中文注释。
- 终端打印完整响应。
- 默认原样输出和保存逆向所需字段，不脱敏、不截断 cookie、token、header、sign、URL、请求体、响应字段或 telemetry；只有用户明确要求“脱敏/截断/公开发布版本”时才处理。
- 避免类、大型 wrapper 和未使用的通用能力。

## 生成脚本流程

1. 判断目标类型：签名、JS challenge cookie、浏览器 token、network hook signing、captcha/TDC 或带分页的组合。
2. 读取最接近的 `references/cases/` 案例。
3. 读取 `references/script-writing-rules.md`，使用其中的 `WORK_DIR = Path.cwd()` 和 `CACHE_DIR = WORK_DIR / "js_reverse_cache"` 规则。
4. 需要 iv8 API 写法时读取 `references/api-inventory.md`，并按索引打开 `references/api-examples/` 下的对应示例文件。
5. 如果目标依赖浏览器环境或用户提供了浏览器样本，先执行“浏览器环境桥接”流程；如果没有可用浏览器样本，就按用户抓包/HTML/JS 样本或 iv8 默认环境起步；最终保存可用来源的原始快照和 `browser_env.json` 到 `js_reverse_cache/`。
6. 在当前工作目录写最小可运行主 `.py` 文件，并写入 `utils/iv8_silent.py`、`utils/logger.py`。
7. 所有下载 JS、临时 JS、挑战 HTML、运行报告写入 `js_reverse_cache/`。
8. 如果 sign/header/token/suffix 与 page/body/timestamp 有关，必须在翻页循环内重建。
9. 可行时运行 `python -m py_compile <script.py> utils/iv8_silent.py utils/logger.py`。
10. 如果网络、Cookie、账号和目标环境允许，再运行脚本或至少验证 iv8 生成链路。

### 确认检查点

下面情况先暂停并让用户确认，不要自动扩大权限或写入长期资产：

1. 需要安装 `iv8`、`requests` 或 `curl_cffi` 时，先说明缺失依赖和安装命令，得到确认后再安装。
2. 要发真实网络请求、使用账号 Cookie、提交验证码/可信输入或触发有状态接口时，先确认请求目标、频率和是否允许使用当前 session。
3. 要从浏览器样本生成 `browser_env.json` 时，先确认唯一 `BROWSER_BASELINE` 来源，避免混拼不同 UA、Cookie、headers、storage 或环境值。
4. 要把成果回写到本 skill 的 `references/cases/` 时，必须先完成当前工作区脚本验证，并再次确认是否保留真实 Cookie、token、header、请求体和响应字段原文。
5. 如果只能完成 `py_compile` 或 iv8 生成链路、不能发真实请求，在完成报告里标注“未做真实请求验证”，不要把脚本描述成已跑通接口。

## 常见工作流

### Challenge Cookie / 页面 JS

1. 用一个 `requests.Session` 发送首个请求。
2. 如果响应是保护/挑战页，保存 HTML、headers、cookies 到 `js_reverse_cache/`。
3. 提取外链 JS 或内联脚本。
4. 用同一个 session 和 headers 下载 JS，并保存到 `js_reverse_cache/`。
5. 创建 `iv8.JSContext(environment=..., config={"timezone": "Asia/Shanghai"})`。
6. 生命周期和外链脚本重要时用 `__iv8__.page.load(snapshot)`。
7. 只需要 DOM 或案例明确手动执行脚本时才用 `document.documentElement.innerHTML = ...`。
8. 有 timer/XHR/promise 时推进 `__iv8__.eventLoop.sleep(...)` 或 `drain()`。
9. 读取 `document.cookie` 或 `__iv8__.netLog.entries[-1].cookieHeader`。
10. 更新同一个 session 的 cookie jar 并重试真实 API。

### Runtime Sign / Header / Token

1. 把目标 JS bundle 或页面 snapshot 加载进 iv8。
2. 只补目标案例确实需要的最小 patch，例如 `MessageChannel` + `__iv8__.wrapNative`。
3. 调用已知 JS 入口，用 `ctx.eval(..., to_py=True)` 返回字符串或 dict。
4. 合并 sign/header/cookie 到 Python 请求。
5. 真实请求并打印完整响应。

## 浏览器环境桥接（4个Phase压缩版）

**MCP使用策略：**
- 优先使用 js-reverse-mcp 采集环境样本
- 遇到 CDP/Hook/SourceMap/Profiler/WebSocket 证据缺口时使用 `cloakbrowser-reverse-mcp`（`D:\\develop_software\\CloakBrowser\\cloakbrowser-reverse-mcp\\launch.bat`）
- 还缺证据（如需要引擎级 trace/property access）时转 camoufox-js-reverse

**Phase 1: 侦察和baseline选择** (原步骤1-3)
- 确认可用 MCP: cloakbrowser-reverse-mcp（含 CDP/SourceMap/Profiler/WebSocket/Hook）→ 必要时 camoufox-js-reverse
- 选择baseline策略（导出/直连/混合）
- 收集环境快照

**Phase 2: 环境归一化** (原步骤4-7)
- 环境diff分析
- iv8全局对象注入
- 属性映射和getter/setter

**Phase 3: iv8执行验证** (原步骤8-9)
- JS加载和执行
- 输出验证

**Phase 4: 真实请求验证** (原步骤10)
- HTTP请求回放
- 结果验证

详细步骤见 references/browser-iv8-bridge.md

### Dynamic URL / XHR Hook

1. 在 iv8 中初始化目标 SDK/保护 runtime。
2. 在 iv8 内创建目标 XHR/fetch。
3. 从 `__iv8__.netLog.entries` 读取最终 URL、headers、cookieHeader、body 元数据。
4. 用 Python `requests` 发送捕获到的真实请求。

### Trusted Input / TDC

1. Python 请求服务端 challenge/session 数据。
2. 必要时 Python 计算图片缺口、POW、轨迹。
3. 用 `ctx.expose(...)` 暴露轨迹和常量。
4. 用 `__iv8__.input.dispatchPointerEvent` 和 `dispatchMouseEvent` 派发可信事件。
5. 移动点之间推进逻辑时间。
6. 读取目标 JS telemetry 后用 Python 提交。

## 案例回写模式

仅在用户明确要求“把本次成果沉淀为案例 / 回写到 skill / 新增 bundled case”时使用。默认交付脚本时不要回写案例库。

回写前先完成普通任务链路：在当前工作目录生成紧凑主脚本和 `utils/` helper，所有下载素材仍先进入当前工作目录的 `js_reverse_cache/`，并尽量完成 `py_compile`、iv8 生成链路和真实请求状态码验证。

回写时遵守：

- 读取 `references/case-ingestion-rules.md`。
- 选择分类目录，例如 `signatures/`、`js-challenges/`、`browser-tokens/`、`network-hook-signing/` 或 `captcha/`。
- 用稳定短 slug 命名，例如 `site-feature.py`。
- 默认复制已验证的最小可复用脚本到 `references/cases/<category>/<site-slug>.py`，保留真实案例所需字段原文；只有用户明确要求公开脱敏版本时才替换敏感字段。
- 只复制必要 frozen JS/HTML/小样本到 `references/cases/js_reverse_cache/<site-slug>/`。
- 不默认删除或截断账号 Cookie、Authorization、个人 token、手机号、精确个人查询词等现场字段；如果用户要求公开脱敏版本，再按 `references/case-ingestion-rules.md` 清理。完整业务响应 JSON、运行报告或一次性抓包大文件仍不要默认入库，除非用户明确要求保存。
- 更新 `references/example-taxonomy.md` 的目录树、案例说明、素材列表和选择规则。
- 如果新增案例暴露了通用写法，才更新 `references/script-writing-rules.md`；不要为单站点细节污染通用规则。

## 依赖

核心依赖缺失时才安装：

```bash
python -m pip install iv8 requests
```

`loguru` 是可选依赖。除非用户明确要求，不安装。

## 完成报告

完成后简短报告：

- 脚本路径。
- `utils/iv8_silent.py` 路径（如果生成）。
- `utils/logger.py` 路径（如果生成）。
- 使用了哪个 bundled case 作为最近参考。
- 哪些常量控制分页或请求输入。
- `js_reverse_cache/` 是否创建。
- 动态 JS、临时 runtime、样本或报告保存路径。
- 如果使用浏览器环境桥接，报告 `BROWSER_BASELINE`、`browser_env.json`、baseline 快照路径、样本来源和未能承接到 iv8 的环境缺口。
- 如果执行了案例回写，报告新增案例脚本、frozen 素材目录和 taxonomy 更新位置。
- iv8 cookie/sign/header/token/URL 生成是否验证成功。
- 最终真实请求返回 `200` 还是实际状态码。
- 是否没有保存响应 JSON。
