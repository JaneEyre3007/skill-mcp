---
name: rs-reverse
description: >-
  瑞数/Ruishu/Rivers Security 专项逆向。Use ONLY with clear Ruishu evidence: $_ts.nsd/cd/l__, r2mKa, meta[r=m], Cookie S/T/P, basearr, hasDebug, 瑞数 412/403, Cookie T/P 纯算, or 瑞数 URL suffix/动态防护参数。Also use for Ruishu-specific sdenv, JsRpc, browser-rpc, and runtime XHR suffix work. Do not use for ordinary sign/token tracing, generic sdenv/JsRpc/browser RPC, generic browser hooks, generic Node.js env patching, or AST deobfuscation without Ruishu evidence.
---

# RS Reverse Skill

## 硬性约束

- 所有目标站点动态材料、挑战源码、采集数据、后缀样本、运行报告、临时生成器和分析结果，统一写入当前工作区的 `js_reverse_cache/`。
- 如果当前工作区没有 `js_reverse_cache/`，先创建它；不要把目标站点动态素材写入本 skill 目录。
- 固定瑞数项目结构必须保留，不能被仓库里的通用 demo 结构替代。
- `rs_reverse.js` 只放模板占位符，不写入真实动态挑战源码；真实源码只替换到临时运行文件，例如 `rs_reverse_runtime.js`。
- 同一条验证链路必须使用同 session 的首跳 Cookie、`$_ts`、mainjs/r2mKa、Node 生成 Cookie、业务 sign/timestamp 和 suffix；不要混用旧 Cookie、旧 suffix、旧签名。
- 不要因为浏览器网络里出现 suffix 就默认复用 suffix；先证明“完整 Cookie + 正确业务参数 + 无 suffix”是否仍停留在瑞数层。

## MCP 工具选择

- 需要浏览器侧定位、断点、源码搜索、网络请求发起栈或 runtime 调试时，先检查当前可用工具列表是否存在 `js-reverse-mcp_*` 工具；用户口中的 `js-reverse_mcp` 也按此类工具理解。
- 如果存在 `js-reverse-mcp_*`，优先使用它完成页面选择、源码搜索、XHR/fetch 断点、调用栈、WebSocket 和网络请求分析。
- 只有当前会话没有 `js-reverse-mcp_*`，或该工具无法完成的浏览器交互/截图/表单操作，才回退到 `chrome-devtools-mcp_*`。
- 同一条调试链路尽量不要混用两套 MCP 的页面上下文；确需切换时先重新确认当前 page/frame/session，避免把旧页面、旧请求或旧断点当作当前证据。

## sdenv 工作目录

- 使用 `sdenv-sandbox/`、`sdenv-client.js` 或 Ruishu sdenv VM 内 XHR 方案时，把运行代码、配置、采集样本、报告和临时脚本放到当前工作区的 `js_reverse_cache/` 下，例如 `js_reverse_cache/sdenv-sandbox/`。
- 不要在本 skill 目录内直接改写或运行目标站点动态材料；本 skill 目录只作为只读模板和参考来源。
- 如果 `js_reverse_cache/` 不存在，先创建它；如果 `sdenv` 运行目录缺少 `node_modules` 或 lockfile/依赖不完整，在该运行目录执行 `npm install` 或项目声明的等价安装命令补齐依赖。
- 安装依赖前先确认运行目录内存在对应的 `package.json`；缺少时从本 skill 的 `sdenv-sandbox/` 复制最小必要模板到 `js_reverse_cache/` 后再安装。

## 固定项目结构

当用户要把瑞数 Cookie、接口请求或本地补环境落到项目中时，使用以下固定结构：

```text
challenge_payload_bootstrap.js  # 412 HTML 内联 $_ts.nsd / $_ts.cd / $_ts.cp 注入层
challenge_payload_runner.js     # 外链 r='m' / r2mKa / mainjs 执行层
mod.js                          # 浏览器环境补充与代理日志，默认从最小 proxy 模板开始
main.js                         # 本地 Cookie 执行入口：require mod/bootstrap/runner 后输出 document.cookie
main.py                         # 首跳采集、动态执行 JS、同 session 带 Cookie 请求接口
rs_reverse.js                   # 瑞数源码模板，只放占位符
js_reverse_cache/               # 统一缓存目录：源码、样本、报告、后缀生成器、临时结果
```

模板文件位于本 skill 根目录的 `project-templates/`：

- `project-templates/minimal-proxy-env-template.js`：创建 `mod.js` 的默认起点。
- `project-templates/rs-runtime-placeholder-template.js`：创建 `rs_reverse.js` 的占位符模板。
- `project-templates/node-cookie-runner-template.js`：创建 `main.js` 的调试模板。
- `project-templates/python-session-request-template.py`：创建 `main.py` 的动态首跳/Node runtime 模板。

## 触发范围

使用本 skill 当用户目标包含：

- 明确说瑞数、Ruishu、Rivers Security、瑞数 4/5/6、药监局瑞数、Rivers 动态安全防护。
- `412` / `403` challenge 同时出现 `$_ts`、`r2mKa`、Cookie S/T/P、`meta[r=m]`、`hasDebug`、`basearr` 任一证据。
- 要采集或验证 `$_ts.nsd`、`$_ts.cd`、`$_ts.cp`、`$_ts.l__`、mainjs、eval code、keys、Cookie S/T/P。
- 要做瑞数 Cookie T/P 纯算、basearr 数据驱动拟合、type=2 映射、混合验证、端到端验证。
- 要分析、复现或本地验证瑞数动态 URL 后缀、防护参数、GET/POST suffix、瑞数 XHR.open hook、Ruishu JsRpc、Ruishu sdenv VM 内 XHR。
- 要使用 `url-suffix-research/ast-tools` 中的 AST 工具链研究 suffix、r2mKa 字节码、session49、child[29]/child[40]。

不要使用本 skill 当：

- 只是普通 `sign`、`token`、`x-sign`、业务请求头入口定位，优先 `find-crypto-entry`。
- 只是要一段 DevTools hook 脚本观察 cookie/fetch/xhr/header，优先 `browser-hook-snippets`。
- 只是普通浏览器 SDK 或已知入口脚本要补 `window/document` 后放 Node.js 跑，优先 `env-patch`。
- 只是通用 obfuscator/sojson/while-switch 还原，优先 `ast-deobfuscate`。
- 只是通用 `sdenv`、JsRpc、浏览器 RPC 或 Node.js 沙箱问题，且没有瑞数证据，优先 `env-patch` 或对应通用 skill。
- 只有普通 403/412 但没有 `$_ts`、r2mKa、Cookie S/T/P、Rivers/Ruishu 文案等证据，先交给 `find-crypto-entry` 判断防护类型。

跨 skill 交接：

- 未确认瑞数、且目标是参数/请求头/cookie 来源定位时，交给 `find-crypto-entry`。
- 只要一段可粘贴的浏览器观察 hook 时，交给 `browser-hook-snippets`；只有需要解释或复现瑞数 runtime 行为时才留在本 skill。
- 已确认瑞数但当前子任务只是“单个混淆文件结构化还原”时，先由本 skill 定阶段，再按需转 `ast-deobfuscate`。
- 已确认入口且用户明确要通用 Node.js 补环境，不需要瑞数 Cookie/basearr/suffix 专项路线时，转 `env-patch`。
- 只要路线判断、检查点设计或案例骨架，且没有明确瑞数证据时，转 `js-reverse-strategy`。

## 任务状态块

仅当任务需要多步执行、跨会话续做或会产出本地工件时，先输出一个简短状态块并据此推进；简单问答、目录检查、轻量 review 或用户明确只要结论时不要强制输出。

```text
Complexity: L3 | L4
Current stage:
Why this stage now:
Read now:
Required artifact:
Exit condition:
```

阶段选择：

- `locate`：还没证明首跳、二跳、Cookie 生产消费关系、业务接口和 suffix 是否必要。
- `recover`：请求链已清楚，但 `r2mKa`、keys、eval code、Cookie 加密链或 suffix 入口仍隐藏。
- `runtime`：入口和边界清楚，但本地/浏览器/sdenv 输出在环境、时间、随机、basearr 或 suffix 上发散。
- `validation`：主要剩下混合验证、端到端验证、同 session 接受验证或多 session 稳定性验证。

## 决策树

```text
1. 确认瑞数证据
   非瑞数 → 退出本 skill，按普通 sign/token/challenge 交给 find-crypto-entry 或 js-reverse-strategy
   412/403 + $_ts/cd/nsd/r2mKa/Cookie S/T/P → 继续

2. 浏览器侧 locate
   采集页面、脚本、业务接口、业务签名、资源中的 suffix 样本、可见 cookie

3. 建立同 session Cookie 链
   首跳 Cookie S/O/acw_tc + JS 生成 T/P → 原页面/二跳 200

4. 接口分层验证
   无 suffix + Cookie only → 是否进入业务层
   无 suffix + 正确业务参数/sign/timestamp → 是否返回业务数据

5. 判断 suffix 是否必要
   无 suffix 已进业务层 → 不做 suffix
   无 suffix 仍 400/412/空 body 且 Cookie/业务签名已对齐 → 进入 suffix 路线

6. suffix 路线
   可用优先 → browser-rpc/
   本地可控 → 固定项目 runtime XHR.open 触发
   sdenv 可用 → sdenv VM 内 XHR
   研究纯算 → url-suffix-research/ast-tools + url-suffix-research/url-suffix-reverse.md

7. Cookie T/P 纯算路线
   先 sdenv/浏览器参考 basearr + 混合验证，再做 basearr 数据驱动适配
```

## 仓库资源索引

上游方法论与可执行资源：

- `agent-skill/upstream-skill.md`：上游 Agent skill 参考文档，已改名避免 opencode 递归注册旧 skill。
- `agent-skill/guides/`：加密链、密钥提取、Coder、basearr、AST、suffix、VM hook 参考。
- `agent-skill/tools/`：`collect-session.js`、`hybrid-verify.js`、`pure-run.js`、`collect-type2.js`、`sdenv-client.js`。
- `agent-skill/reference-impl/`：`coder.js`、`basearr.js`。

后缀 AST 深度研究：

- `url-suffix-research/url-suffix-reverse.md`：URL suffix 逆向完整记录、补环境要点、公开资料汇总。
- `url-suffix-research/ast-tools/trace-rt239.js`：定位后缀核心函数 `rt[239]`。
- `url-suffix-research/ast-tools/suffix-structure.js`：后缀结构分析。
- `url-suffix-research/ast-tools/extract-opcodes.js`：提取 VM opcodes。
- `url-suffix-research/ast-tools/r2mka-disasm.js`：r2mKa 字节码反汇编。
- `url-suffix-research/ast-tools/bytecode-to-js.js`：字节码到伪 JS 翻译。
- `url-suffix-research/ast-tools/trace-session49.js`、`trace-49b-session.js`：追踪 49B session。
- `url-suffix-research/ast-tools/translate-child40.js`、`cookie-s-decrypt.js`、`cookie-s-complete.js`、`session-chain.js`：Cookie S / session 链路研究。
- `url-suffix-research/ast-tools/find-xtea-huffman.js`、`decompose-bs-children.js`、`verify-rt-map.js`：算法与映射辅助分析。
- `url-suffix-research/ast-tools/tool-paths.js`：AST 工具共享路径辅助，避免绑定本机绝对路径。

可用性方案：

- `browser-rpc/`：浏览器 WebSocket RPC 通杀方案，适合强 suffix 站点。
- `sdenv-sandbox/`：sdenv 客户端和依赖说明，适合采集 Cookie、eval、basearr，或在 VM 内触发 XHR。
- `cookie-t-pure-runtime/`：纯算 Cookie T 方案、脚本、档案。
- `upstream-rs-reverse/`：pysunday/rs-reverse 源码参考。

本地固定项目模板：

- `project-templates/minimal-proxy-env-template.js`
- `project-templates/rs-runtime-placeholder-template.js`
- `project-templates/node-cookie-runner-template.js`
- `project-templates/python-session-request-template.py`

资源读取优先级：

- 默认先读本 `SKILL.md` 和当前工作区证据，不要一开始全量扫描 `upstream-rs-reverse/`。
- Cookie T/basearr 纯算问题优先读 `agent-skill/upstream-skill.md`、`agent-skill/guides/` 和 `cookie-t-pure-runtime/` 中对应文件。
- URL suffix 问题优先读 `url-suffix-research/url-suffix-reverse.md` 和 `url-suffix-research/ast-tools/` 中命名最接近的工具。
- 可用性优先的强 suffix 站点优先读 `browser-rpc/README.md` 或 `sdenv-sandbox/README.md`，不要先钻 AST。
- `upstream-rs-reverse/` 是第三方源码参考，只在需要对照 pysunday 实现、命令参数或 basearr 适配器时定向读取。

## URL Suffix 路线

已知原则：

- 大多数瑞数站点只校验 Cookie，不需要 suffix。
- 国家药监局 `nmpa.gov.cn` 属于瑞数 6 严格站点，GET 接口常见需要 suffix。
- suffix 参数名通常来自 `keys[7].split(';')[1]`。
- suffix 由 `XMLHttpRequest.prototype.open` hook 触发，内部使用 `document.createElement('a')` 解析 URL。
- 纯算后缀的主要瓶颈是 49B session 和 VM 字节码内部状态；短期交付优先 JsRpc、sdenv VM 内 XHR 或固定项目 runtime XHR。

固定项目 runtime 触发要点：

- URL 优先用相对路径，例如 `/datasearch/data/nmpadata/search?...`。
- `document.createElement('a')` 必须用 `new URL(value, location.href)` 动态解析并提供 `href/protocol/host/hostname/port/pathname/search/hash/origin`。
- `XMLHttpRequest.prototype.open/send/setRequestHeader` 必须在瑞数 runtime 执行前存在，供瑞数覆盖或包装。
- 捕获原生 `open` 收到的最终 URL，以及原生 `setRequestHeader` 收到的同名 suffix header。
- suffix 与当前 runtime/Cookie/时间/随机绑定，不能跨 session 复用。

## Cookie T/P 纯算边界

不要把这些阶段混为一谈：

- 加密链验证：用已知正确 basearr + keys 重新生成 Cookie。
- keys 提取：从 `$_ts.cd` 解出 45 组 keys。
- Coder/eval 重写：从 mainjs + nsd/cd 生成 eval code 或解释 codeUid。
- basearr 适配：用多 session 样本逐字段闭包。
- 端到端纯算：连续多 session 同首跳材料生成 Cookie 并通过原页面/二跳/目标接口。

只有最后一步通过后，才可称为端到端纯算。

## 排错优先级

- 412：先查同 session Cookie S/O/acw_tc 与 T/P、Cookie 名、时间、二跳消费关系。
- 空 body 400：优先怀疑瑞数层混 session、旧 suffix、旧 Cookie、runtime 环境不一致。
- JSON 业务错误：大概率已过瑞数，优先修业务参数、sign、timestamp、token。
- suffix 不生成：查相对 URL、anchor 解析、XHR 原型、是否同 runtime 先生成 Cookie 再触发 XHR。
- Coder 输出不匹配：逐字节找差异，不要格式化运行用 eval code。
