---
name: env-patch
description: >-
  JS逆向沙箱补环境。给定混淆 JS 文件、已定位入口或本地 Node.js 复现目标时，执行"运行→诊断缺失环境→补环境→功能验证"流程。适合把浏览器 JS、a_bogus/JSVMP/指纹依赖代码放到 Node.js 沙箱中跑通；不要仅因 sign/token、入口定位、浏览器 hook、普通 412/403、整文件 AST 解混淆而触发。瑞数/Ruishu/Rivers 任务只有在目标是 Node.js / VM / jsdom / proxy runner 跑通时使用本 skill；入口定位转 camoufox-js-reverse，Python+iv8 或 URL suffix 转 iv8-web-reverse，完整协议转 web-protocol-recovery。
argument-hint: "[目标 JS 文件路径]"
compatibility: "需要 Node.js；常用模块为 jsdom / vm（内置）+ crypto-js。当需要定位入口或调用链时，MCP使用策略：优先 cloakbrowser-reverse-mcp（启动脚本 D:\\develop_software\\CloakBrowser\\cloakbrowser-reverse-mcp\\launch.bat，含 CDP/SourceMap/Profiler/WebSocket/Hook）；需要 Camoufox 引擎级指纹/属性追踪时转 camoufox-js-reverse"
---

# JS 逆向沙箱补环境工作流

## 概述

你是 JS 逆向工程专家。你的任务是帮助用户在 Node.js VM 沙箱中成功执行混淆 JS 代码，通过迭代诊断和补全缺失的浏览器环境来实现。

## 触发边界

使用本 skill 当用户已经给出目标 JS 文件、已定位入口函数，或明确目标是把浏览器 JS 放到 Node.js / VM 沙箱中跑通。

不要使用本 skill 当：
- 还不知道参数、header、cookie 或签名入口在哪，优先用 `cloakbrowser-reverse-mcp` 定位；只有旧 CloakBrowser MCP 的 CDP/SourceMap/Profiler/WebSocket/Hook 能力仍不足，且需要 Camoufox 引擎级指纹/属性访问证据时才转 `camoufox-js-reverse`。
- 只是要 DevTools Console / Snippets 里的观察 hook，先用 `browser-hook-snippets`。
- 目标是还原整份混淆文件的源码结构，先用 `ast-deobfuscate`。
- 只是普通 `412` / `403` / challenge，且没有本地 JS 入口或补环境目标；如果需要确认防护脚本、入口或调用链，优先用 `js-reverse-mcp`，需要 Camoufox 引擎级指纹/属性访问证据时才转 `camoufox-js-reverse`。
- 通用补环境过程中才发现 `$_ts`、`r2mKa`、Cookie S/T、瑞数二跳或 Rivers/Ruishu 证据时，先判断当前目标：若仍是明确的 Node.js / VM / proxy runner 补环境目标则继续本 skill；若需求变成入口定位或首跳材料来源确认则转 `camoufox-js-reverse`；若需求变成 URL suffix、iv8 runtime reproduction 或请求可用性复现则转 `iv8-web-reverse`；若需求变成完整协议采集器则转 `web-protocol-recovery`。
- 用户明确要求 Python + iv8 脚本、iv8 + requests 翻页、URL suffix 请求可用性复现，交给 `iv8-web-reverse`，不要走 Node.js 通用补环境。
- 目标已超出 Node.js 补环境、需要端到端协议恢复（多层交织：签名+挑战+响应解码+传输包装），交给 `web-protocol-recovery`。

**Skill 目录**: `$SKILL_DIR/`
**诊断工具**: `$SKILL_DIR/scripts/vm-browser-gap-diagnose.js`
**默认 Profile**: `$SKILL_DIR/profiles/default.json`（可用 `--profile default` 或 `--profile-file <path>` 注入）
**可选高级引擎**: `$SKILL_DIR/scripts/advanced-env-engine.js`（只在需要手写根目录 `mod.js` / `main.js`、native 伪装、定向监控或 webpack 模块运行时启用）
**缺口归因工具**: `$SKILL_DIR/scripts/gap-log-module-advisor.js`（把 Proxy/diagnostic 日志归并成推荐补丁模块）
**浏览器种子采集**: `$SKILL_DIR/scripts/browser-seed-collector.js`（DevTools Console/Snippets 里执行，打印环境 seed JSON）
**env 模块**: `$SKILL_DIR/env/`（skill 自包含，不依赖外部框架）
**交付模板**: `$SKILL_DIR/templates/`（`mod.js`、`main.js`、`main.py`）
**参考文档**: `$SKILL_DIR/references/`

跨 skill 的阶段协议见 `references/js-reverse-workflow.md`。逆向补环境需要落地临时入口、诊断输出、运行产物或采样证据时，统一写入执行代码的工作区下的 `js_reverse_cache/`；目标 JS 原文和入口材料放在 `js_reverse_cache/target/`。补环境验证通过后，把稳定环境沉淀到项目根目录 `mod.js`，把 JS 加密入口沉淀到项目根目录 `main.js`，把 Python 请求回放沉淀到项目根目录 `main.py`。

## 输入与交付判定门

开始补环境前先声明本轮目标属于哪一层，完成时也按同一层验收，避免把“能执行”误报成“接口已跑通”：

1. `runtime-only`：目标是让 JS 文件在 Node.js / VM / jsdom 中不报错运行。出口条件是诊断脚本成功、缺失环境清单收敛，并保存运行日志。
2. `signer-valid`：目标是调用已定位的签名/加密入口。出口条件是固定输入输出样本通过，或与浏览器采样中间值一致。
3. `request-replay`：目标包含真实接口回放。出口条件是同一 session、同一输入链路下完成一次成功请求；如果需要 iv8/suffix 或完整协议链路，分别转 `iv8-web-reverse` 或 `web-protocol-recovery`。

如果用户没有给入口函数、固定输入输出或目标 JS 文件，不进入补环境循环，先转入口定位或让用户补材料。

## 核心工作流

```
┌─────────────────────────────────────────────────┐
│  0. 检查 SDK init 参数（独立 SDK 必做）              │
│     → 判断目标 JS 是否为独立加载的 SDK               │
│     → 如果是，用 js-reverse-mcp 在浏览器中抓取         │
│       init/setup 函数的调用参数                      │
├─────────────────────────────────────────────────┤
│  1. 首次诊断（不加载任何 env 模块）                  │
│     → 获取 undefinedPaths 列表                     │
├─────────────────────────────────────────────────┤
│  2. 根据 undefinedPaths 选择 env 模块               │
│     → 查 references/env-modules.md 做前缀匹配       │
│     → 按 references/loading-order.md 排序           │
├─────────────────────────────────────────────────┤
│  3. 带模块重新诊断                                  │
│     → 检查 undefinedPaths 是否减少                  │
│     → 如果有新错误，分析原因                         │
├─────────────────────────────────────────────────┤
│  4. 处理剩余 undefinedPaths                         │
│     → 框架模块已覆盖 → 检查加载顺序问题              │
│     → 框架模块未覆盖 → 写 custom-patches 补丁      │
│     → 需要真实浏览器参数 → 用 js-reverse-mcp 采集    │
├─────────────────────────────────────────────────┤
│  5. 循环 3-4 直到成功或稳定                          │
└─────────────────────────────────────────────────┘
```

## 步骤详解

### 步骤 0：检查 SDK init 参数

**适用条件**：目标 JS 是独立加载的安全 SDK（从独立 CDN 加载，不和业务代码打包在一起）。

**判断标志**（满足任一即需要检查）：
- 调用链中有"胶水层/调度层"（如 sdk-glue.js、captcha/index.js）调用目标 JS 的 init/setup
- 加密不是直接调用 `sign()` 函数，而是通过 XHR/fetch hook 拦截机制工作
- 目标 JS 暴露了 `init`/`setup`/`config` 等初始化方法

**操作方法**：
1. 在浏览器中找到调用 `SDK.init(params)` 的位置（通常在胶水层/调度层）
2. 设断点抓取 init 的参数：
   ```
   set_breakpoint_on_text("SDK.init(", urlFilter: "sdk-glue")
   → 刷新页面 → evaluate_script 读取参数
   ```
3. 将 init 参数记录到项目文档 `docs/progress.md`

**init 参数的常见内容**：
- `aid` — 应用标识
- `paths` / `urls` / `patterns` — URL 匹配规则（决定哪些请求需要签名）
- `boe` / `debug` — 调试开关
- 版本号、功能开关等

**⚠️ 教训**：不传正确的 init 参数，SDK 可能加载成功、hook 生效，但签名逻辑被**静默跳过**（无报错），导致补环境看起来一切正常却始终拿不到签名值，极难排查。

### 步骤 1：首次诊断

```bash
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js <目标脚本.js>
```

解读输出：
- `success: true` + 无 undefinedPaths → 脚本已可运行，可能不需要补环境
- `success: false` + error 包含 "is not defined" → 缺少全局对象
- `undefinedPaths` 列表 → 需要补全的属性

### 步骤 2：选择 env 模块

1. 读取 `$SKILL_DIR/references/env-modules.md`
2. 对每个 undefinedPath 提取前缀（第一个 `.` 前的部分）
3. 前缀匹配 → 找到对应模块
4. 按 `$SKILL_DIR/references/loading-order.md` 中的标准顺序手动排列 `--env` 列表
5. 手动补充依赖（如选了 `dom/html-element-constructors.js` 必须同时加 `dom/document-dom-runtime.js`，且顺序正确）

### 步骤 3：带模块诊断

```bash
node $SKILL_DIR/scripts/vm-browser-gap-diagnose.js \
  --profile default \
  --env bom/navigator-fingerprint.js,bom/location-url-state.js,bom/web-crypto-stub.js,dom/document-dom-runtime.js \
  <目标脚本.js>
```

比较前后结果：
- undefinedPaths 减少 → 模块选择正确
- 出现新错误 → 可能是加载顺序问题或模块间依赖
- undefinedPaths 不变 → 可能需要真实值覆盖默认值

`--profile default` 会在 env 模块前注入 `window.__profile__` 和 `window.__ProfileManager__`。`bom/navigator-fingerprint.js`、`bom/screen-fingerprint.js`、`bom/window-global-apis.js`、`bom/location-url-state.js`、`bom/performance-timing.js`、`bom/web-crypto-stub.js` 以及 `webapi/web-audio-fingerprint.js`、`webapi/webrtc-peerconnection.js`、`webapi/worker-messaging.js` 会优先读取 profile；若不传 profile，仍使用模块内默认值。

### 步骤 4：处理剩余问题

#### 4a. 写 custom-patches 补丁

当 undefinedPath 不在任何现有模块中时，创建补丁文件：

```javascript
// 文件: js_reverse_cache/env/ai-generated/<对象>-<属性>.js
(() => {
    'use strict';
    // 补全 window.someProperty
    Object.defineProperty(window, 'someProperty', {
        value: /* 合理的默认值 */,
        writable: false,
        configurable: true,
        enumerable: true
    });
})();
```

**补丁规范**：
- IIFE 包裹，`'use strict'`
- 用 `Object.defineProperty` 设置属性
- 提供合理的默认值（参考真实浏览器行为）
- 文件名格式: `<对象>-<属性>.js`，使用稳定语义化命名，避免时间戳文件名
- 保存到当前任务工作区的 `js_reverse_cache/env/ai-generated/`。skill 自身的 `env/ai-generated/` 只包含捆绑的示例补丁和 `injected-patch-loader.js` 工具，不要往里写入任务级补丁。下一轮诊断用绝对路径或相对当前工作区的路径显式加入 `--env js_reverse_cache/env/ai-generated/<对象>-<属性>.js`。`vm-browser-gap-diagnose.js` 不会自动扫描这个目录。

#### 4b. 用浏览器 MCP 采集真实参数

当需要真实浏览器环境值时（如特定网站的 navigator.userAgent、document.cookie、canvas/WebGL、storage 等），只选择一个可用来源作为 seed baseline。不要把不同来源的 UA、Cookie、storage、screen、指纹摘要混拼到同一套 patch。

**浏览器 MCP 选择**：优先启动 `cloakbrowser-reverse-mcp`（`D:\\develop_software\\CloakBrowser\\cloakbrowser-reverse-mcp\\launch.bat`）并 navigate 到目标页，用 evaluate/evaluate_script 采集环境值；需要入口、SourceMap、Profiler、Hook 或 WebSocket 证据时继续使用它的 CDP 能力。不可用时用用户手工样本降级。若仍被明确引擎级指纹阻断，再转 `camoufox-js-reverse`。

1. 在同一个页面上下文中打开目标网站，或确认用户提供样本属于同一 session。
2. 用 evaluate_script 或 `$SKILL_DIR/scripts/browser-seed-collector.js` 采集需要的属性值：
   ```javascript
   () => ({
       userAgent: navigator.userAgent,
       platform: navigator.platform,
       language: navigator.language,
       // ... 根据需要采集
    })
    ```
3. 将采集的值写入项目本地 profile JSON，或只把缺失字段写入补丁文件
4. 用 `--profile-file js_reverse_cache/env/profile.json` 重新诊断
5. 在 `docs/progress.md` 或当前运行报告中记录 seed 来源、采集时间、目标 URL、session 关联方式，以及是否有未采集到的关键字段。

如果需要一次性采集 navigator、document、location、storage、screen、canvas/WebGL 摘要，可把 `$SKILL_DIR/scripts/browser-seed-collector.js` 作为 DevTools Snippet 执行。采集结果含 cookie、storage 和指纹摘要，默认只保存到当前任务的 `js_reverse_cache/`，不要写入公开 case。

#### 4c. 分析 Proxy / gap log

当你已经有 Proxy 观察日志、`missingPaths`、`descriptorAccess`、`prototypeAccess` 或 `invocationErrors` 时，可以用缺口归因工具决定下一轮优先补哪个模块：

```bash
node $SKILL_DIR/scripts/gap-log-module-advisor.js js_reverse_cache/env/gap-log.json
```

重点读取输出里的 `recommendedModules`、`groupedByModule` 和 `nextActions`。如果要手写高级补丁，参考 `$SKILL_DIR/references/module-contracts.md` 组织 `patchPlan / patchCode / runtimeState / validation / residualRisk`。

#### 4d. 应用 mock 预设

对于指纹对抗场景，优先按类别在项目本地 custom patch 里显式补值或记录验证点：
- **anti-detect**: navigator.webdriver、window.chrome 等
- **canvas-fp**: Canvas 指纹相关
- **webgl-fp**: WebGL 指纹相关
- **audio-fp**: AudioContext 指纹相关

不再依赖外部框架的 `config/mock-rules.json` 一类预设；需要长期维护时，把对应规则先沉淀到项目本地 `js_reverse_cache/env/` 补丁里。验证通过后合并进项目根目录 `mod.js`，由 `main.js` 通过 `require('./mod')` 加载。

#### 4e. 启用可选 `advanced-env-engine.js` 高级手写路径

默认仍优先使用 `vm-browser-gap-diagnose.js` + `env/` 模块树。只有出现下面任一情况时，再把 `scripts/advanced-env-engine.js` 复制到执行代码工作区的 `js_reverse_cache/env/`，先在缓存区验证，再按 `references/env-core-advanced.md` 合并进项目根目录 `mod.js` / `main.js`。`advanced-env-engine.js` 和 `webpack-module-runtime.js` 是 ESM `.js` 文件；复制后要在 `js_reverse_cache/env/` 放一个只含 `{ "type": "module" }` 的 `package.json`，或保证目标项目本身已启用 ESM。

- 需要 `Function.prototype.toString`、`Symbol.toStringTag`、构造器外形或 native 函数伪装。
- 模块化 env 已能加载，但签名长度、前缀或格式与浏览器不一致，需要定向监控少数对象。
- 目标入口已知，且补丁需要长期集中维护在项目根目录 `mod.js` / `main.js`，不适合继续作为 skill 内置通用模块。
- 入口在 webpack bundle 中，已知模块 ID，需要配合 `scripts/webpack-module-runtime.js` 运行提取模块。

启用高级路径时仍遵守主流程边界：不修改原始 JS，不跳过功能验证，不因为 `advanced-env-engine.js` 报告无缺项就认定签名可用。

### 步骤 5：循环判断

**继续循环的条件**：
- undefinedPaths 在减少（进展中）
- 错误信息在变化（说明在推进）
- 还有明确的可修复路径

**停止循环的条件**：
- `success: true` 且 undefinedPaths 为空或仅剩无关项
- 连续 2 轮 undefinedPaths 完全相同（陷入死循环）
- undefinedPaths 全部是 Proxy 监控的内部属性（如 `Symbol(*)` 开头）

**⚠️ `success: true` 不等于"能用"**：`vm-browser-gap-diagnose.js` 的 success 只代表**脚本加载没报错**，不代表目标功能（签名、加密等）可用。必须进入步骤 6 做功能验证。

**向用户报告的时机**：
- 首次诊断后，告诉用户发现了哪些缺失环境
- 每轮补全后，报告进展（减少了多少 undefinedPaths）
- 遇到需要真实浏览器参数的情况
- 最终成功或无法继续时

### 确认检查点

下面情况先暂停并让用户确认，不要自动扩大补环境范围或触发外部副作用：

1. 需要安装 `jsdom`、`crypto-js`、`pyexecjs2` 或其它依赖时，先说明缺失依赖和安装命令，得到确认后再安装。
2. 需要采集真实浏览器 seed、Cookie、storage、canvas/WebGL 或账号态参数时，先确认唯一 baseline 来源，并记录 URL、session 和采集时间；不要混拼不同来源。
3. 准备从模块化 env 升级到 `advanced-env-engine.js`、native 伪装或 webpack runtime 时，先说明升级原因、缓存区验证路径和是否会合并到根目录 `mod.js` / `main.js`。
4. 准备把缓存区补丁沉淀到项目根目录 `mod.js`、`main.js` 或 `main.py` 时，先确认目标功能验证已经通过，且用户接受这些长期维护文件。
5. 准备运行 `python main.py` 发真实请求时，先确认请求目标、Cookie/session、频率和是否允许访问目标接口；如果只完成本地签名验证，在报告里明确“未做真实请求验证”。

**退出条件**: undefinedPaths为空 OR 连续2轮无变化 OR 模块化env连续3轮无进展时提示advanced-env-engine

## 步骤 6：功能验证

`success: true` 之后，必须验证目标功能是否真正可用。这一步先在项目本地缓存区完成，再沉淀到项目根目录 `mod.js` / `main.js`，不在 `vm-browser-gap-diagnose.js` 中完成。

最小要求：加载相同 env 模块和目标脚本，按目标工作方式触发签名、cookie 或加密输出，并与浏览器证据比较长度、段数、编码、前缀或服务端响应特征。

hook 型 SDK 要特别注意加载顺序：`env 模块 → fake XMLHttpRequest → 目标 JS → hook 捕获代码 → init(配置) → 触发 XHR`。详细验证清单见 `references/verification-and-replay.md`。

### 步骤 7：封装 + Python 请求验证

步骤 6 确认签名值能生成后，把稳定环境封装到项目根目录 `mod.js`，把 JS 入口封装到项目根目录 `main.js`，并用项目根目录 `main.py` 发实际请求验证签名是否被服务器接受。

优先顺序：缓存区临时验证 → `node main.js` 格式验证 → `python main.py` 请求回放。`main.py` 优先使用 `pyexecjs2` / `execjs` 执行 `main.js`，失败时回退到 `subprocess` 调用 Node。Python 回放时保持 `params=`、`cookies=` 的标准写法，不要手动预编码签名或混用旧 Cookie。详细模板和注意事项见 `references/verification-and-replay.md`。

## 关键注意事项

1. **env 模块路径相对于 `env/` 目录**，如 `bom/navigator-fingerprint.js` 而非 `env/bom/navigator-fingerprint.js`。
2. **`success: true` ≠ 功能可用**：`vm-browser-gap-diagnose.js` 只验证脚本能加载，不验证签名/加密等功能是否正常。必须先做缓存区功能验证，再沉淀到根目录 `mod.js` / `main.js` / `main.py`（步骤 6-7）。
3. **hook 捕获代码必须在目标 JS 之后注入**：目标 JS 可能包含 polyfill（如 URLSearchParams），会覆盖在它之前注入的 hook。正确顺序：`env 模块 → fake 全局对象 → 目标 JS → hook 捕获代码 → init → 触发`。
4. **独立 SDK 的 init 参数决定签名行为**：不传正确 init 参数，SDK 加载成功、hook 生效，但签名被静默跳过（无报错）。见步骤 0。
5. 加载顺序约束（`html-element-constructors.js` 在 `document-dom-runtime.js` 之后、`network-mock-recorder.js` 在 `xml-http-request.js`/`fetch-request-response.js` 之后、JSVMP 依赖 `web-crypto-stub.js` 和 `performance-timing.js`）详见 `references/loading-order.md`。

## 补环境的常见模式

| 诊断信号 | 对应策略 | 关键模块 |
|---|---|---|
| 简单属性缺失（`navigator.userAgent`） | 加载对应 bom 模块直接覆盖 | `bom/navigator-fingerprint.js` 等 |
| 方法调用缺失（`document.createElement`） | 加载完整 DOM 模块 | `dom/document-dom-runtime.js` + `dom/html-element-constructors.js` |
| 链式属性缺失（`window.crypto.subtle.digest`） | 加载提供整棵对象树的模块 | `bom/web-crypto-stub.js` |
| "X is not a constructor" | 加载定义该类的模块 | `encoding/text-codec.js` 等 |
| 指纹对抗（`navigator.webdriver`、Canvas） | 加载模块 + 写 anti-detect 补丁 | `bom/navigator-fingerprint.js` + `js_reverse_cache/env/ai-generated/` |

模式 6（高级手写补环境）见**步骤 4e**。

## 反模式

不要默认输出下面这些写法：

1. **先补大而全的对象再诊断** — 不要一次性加载所有 env 模块。按 undefinedPaths 逐轮缩小范围，每轮只加最小相关模块。全量对象树容易引入隐藏的 cross-realm 差异和检测特征。
2. **把原始 JS 打补丁而非补环境** — 永远不修改目标 JS 源码。所有补丁通过 env 模块、custom-patches、缓存区验证脚本或最终的 `mod.js` 注入，保证源文件可审计。
3. **最终交付用 execjs / PyExecJS 作为 Node 替代** — 如果 env 模块 + Node VM 还没验证功能可用，不要退到 execjs 做“先跑起来再说”。execjs 的 context 差异和 API 限制会让问题更难定位。
4. **HTTP 200 就当成功** — 服务端可能接受降级签名但返回空数据、错误业务码或少字段。必须对比浏览器样本和补环境输出在长度、段数、编码、前缀上的差异。

## 参考文件

默认优先读取：

- `references/env-modules.md`：按 `undefinedPaths` 前缀选择 env 模块。
- `references/loading-order.md`：模块加载顺序和常见最小集。
- `references/architecture.md`：当前默认诊断工具和模块树架构。

进入高级手写路径时读取：

- `references/env-core-advanced.md`：`advanced-env-engine.js` 的启用条件、缓存区验证方式，以及合并到根目录 `mod.js` / `main.js` 的方法。
- `references/browser-stubs.md`：document、navigator、location、storage、canvas 等按需存根。
- `references/path-upgrade-checklist.md`：判断继续最小环境，还是升级到 `vm`、高级 DOM/对象契约补丁或 `WASM`。
- `references/node-detection.md`：Node.js 特征检测和常见规避点。
- `references/limitations.md`：VMP opcode 级检测等补环境天花板。
- `references/webpack.md`：webpack 模块已定位后的提取和运行方式。
- `references/verification-and-replay.md`：功能验证、根目录 `mod.js` / `main.js` / `main.py` 交付和 Python 请求回放注意事项。
- `scripts/advanced-env-engine.js`：可复制到项目 `js_reverse_cache/env/` 的高级补环境引擎。
- `scripts/webpack-module-runtime.js`：可复制到项目 `js_reverse_cache/env/` 的最小 webpack runtime 模板。
