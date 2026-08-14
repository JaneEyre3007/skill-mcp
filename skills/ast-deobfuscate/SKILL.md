---
name: ast-deobfuscate
description: >-
  用 Babel AST 对混淆 JavaScript 做结构化还原，优先按 sojson、sojsonv7、obfuscator、awsc、jjencode、common 这类家族选择解混淆流水线，产出更可读、可继续分析的源码和中间产物。适合“帮我解混淆这段 JS”“还原 obfuscator/sojson/_0x 风格代码”“展开字符串数组、控制流平坦化、while-switch”“参考 Decode_action 那种插件式 pass 处理”，前提是用户真正要的是还原源码结构、拆 pass、保留中间产物，而不是只找参数入口、只要浏览器 hook 脚本或直接补环境执行。不要用于浏览器 DevTools hook、参数入口定位或 Node.js 补环境，以及目标是"跑通/执行/生成结果"而非"阅读源码"（转env-patch或iv8-web-reverse）
argument-hint: "[混淆代码文件路径或 URL]"
compatibility: "需要 Node.js 与 Babel 工具链；常用依赖为 @babel/parser/@babel/traverse/@babel/generator/@babel/types；某些字符串恢复可选 isolated-vm 或等价沙箱。"
---

# ast-deobfuscate

对 **$ARGUMENTS** 执行 AST 解混淆，目标是最大化恢复可读结构，同时保留可回退的中间产物。

这个 skill 现在按 `Decode_action-main` 的思路组织，但不照搬单次样本代码。它吸收的是该仓库的结构方式：入口负责路由，plugin 负责家族级 pipeline，visitor 负责单一 AST 变换，`input.js -> output.js` 之间保留可回退产物。

1. 先识别混淆家族，再选对应 pipeline。
2. 用一组小 visitor 串成多轮 pass，不堆成一个万能大脚本。
3. 每轮大改后都 `generate -> reparse -> next pass`，降低节点失效和误替换风险。
4. 默认在目标项目里落地脚本、输入输出和中间文件，不只停留在分析。

如果用户想要“先有一个能跑的模板，再基于样本继续细化”，优先使用随 skill 附带的 `scripts/decode_action_scaffold.js` 作为起手脚手架。

如果用户已经明确要长期维护某个目标、持续补 visitor 和 plugin，优先使用 `scripts/template-project/` 目录模板，而不是继续把所有逻辑堆在单文件里。目录版模板命名为 `src/plugins/` 与 `src/visitors/`，对应 `Decode_action-main` 中 `src/plugin/` 与 `src/visitor/` 的职责拆分。

目录版模板还带有低风险残留度量工具：`src/tools/collect-residue-metrics.js` 和 `src/tools/compare-with-reference.js`。它们只解析和统计 AST，不执行目标样本代码，用于判断下一轮应补控制流、dispatcher、重命名还是参考对比。

如果用户明确说“我要阅读解混淆后的代码”，优先交付**阅读版输出**：不额外引入 `require` / `module.exports` / 调用包装，只在原文件内部做字符串恢复、保守控制流整理和确定性重命名。

如果用户明确说“我要直接调用这个解密逻辑”，再额外补**调用版输出**。不要把阅读版和调用版混成同一个默认产物。

跨 skill 的阶段协议见 `references/js-reverse-workflow.md`。本 skill 不替代 `Observe` / `Capture`：如果目标是请求参数复现，应先确认关键请求和脚本范围，再对命中的混淆文件做定向还原。需要生成临时源码、中间产物或调试文件时，按共享协议写入执行代码的工作区下的 `js_reverse_cache/`；不存在则先创建，不要写到工作区之外。

## 何时触发

下面这些需求通常应该触发本 skill：

1. “帮我解混淆这段 JS / 这个大文件”。
2. “还原 obfuscator / sojson / sojsonv7 / awsc / jjencode 风格代码”。
3. “把 while-switch、字符串数组、控制流平坦化展开”。
4. “参考 Decode_action / decode-js 的插件式流程帮我拆 pass”。

下面这些需求通常不该由本 skill 单独处理：

1. “这个参数在哪个函数里生成”。
2. “给我一个 DevTools 里能直接注入的 hook 脚本”。
3. “把这段浏览器 JS 补环境后放到 Node.js 跑”。
4. “我已经知道是哪个函数了，只想把它搬到 Node.js 跑”。
5. “我不要还原整个文件，只想知道 sign/token/header 的调用链”。

## 转交提示

如果用户真正卡住的是参数入口、header 来源或调用链，转给 `camoufox-js-reverse`。

如果用户真正要的是浏览器运行时 hook 脚本，转给 `browser-hook-snippets`。

如果用户真正要的是浏览器代码脱离浏览器在 Node.js 中跑起来，转给 `env-patch`。

如果源码来自瑞数/Ruishu/Rivers Security 链路，先看用户目标：如果用户明确要对某个混淆 JS 文件做 AST 结构化还原，本 skill 可以直接处理；入口/调用链或首跳材料来源确认转 `camoufox-js-reverse`；Node runtime/proxy 跑通转 `env-patch`；iv8 runtime、URL suffix 或请求可用性复现转 `iv8-web-reverse`。不要把本 skill 当成瑞数运行时补环境或请求复现路线。

如果用户目标是 Python + iv8 执行链路或紧凑 iv8 请求脚本，交给 `iv8-web-reverse`。

如果用户已定位入口且需要端到端协议恢复（签名+bootstrap+解码全链路），交给 `web-protocol-recovery`。

## 默认交付模式

如果用户已经给了代码、文件路径或可下载 URL，且目标明确是“解混淆/还原源码/落地流水线”，默认目标不是“讲思路”，而是直接在目标项目里交付：

1. 目标项目中的 `<target-project>/scripts/deobfuscate_target.js` 或按步骤拆分的 `<target-project>/scripts/stepN_*.js`
2. `source/deobfuscated/target_deobf.js`
3. 关键中间产物，如 `intermediate/target_step1.js`
4. 一份简短说明：命中的家族、用了哪些 pass、剩余什么结构

如果用户没有现成脚本模板，优先从 `scripts/decode_action_scaffold.js` 复制出一个目标专用版，再按样本细化。

默认起手命令链应在报告里明确写出，便于用户复跑：

1. `mkdir -p source/original source/deobfuscated intermediate scripts`，把原始样本保存到 `source/original/<name>.js`。
2. 从本 skill 的 `scripts/decode_action_scaffold.js` 派生目标脚本到 `scripts/deobfuscate_<name>.js`，不要直接改 skill 内置脚手架。
3. 运行 `node scripts/deobfuscate_<name>.js source/original/<name>.js source/deobfuscated/<name>_deobf.js`，每轮 pass 额外写 `intermediate/<name>_stepN.js`。
4. 每次大改后做 `generate -> reparse -> next pass`；最后至少执行一次语法解析检查，必要时再跑残留度量或参考对比工具。
5. 完成报告必须列出命中的家族、执行的 pass、输出路径、仍未处理的残留结构和下一轮最小建议。

如果用户只是要“先判断混淆家族”“解释这段代码大概做什么”“评估是否值得继续还原”，先做轻量分析，不要默认创建完整项目结构。

如果用户已经进入“第二轮及以后”的持续收敛阶段，优先从本 skill 的 `scripts/template-project/` 复制整套目录结构到目标项目，再把单文件脚手架里的逻辑拆回目标项目的 `src/plugins/` 和 `src/visitors/`。

如果需求是“先能读，再能调”，顺序应是：

1. 先交阅读版
2. 确认阅读版可运行或至少语法正确
3. 再按用户需要补调用版入口

只有在以下情况才停在分析阶段：

1. 输入不完整，拿不到实际源码
2. 关键逻辑强依赖运行时状态，静态还原风险过高
3. 用户明确只要分析，不要落地代码

## 确认检查点

下面情况先暂停并让用户确认，再继续扩大产物或提高变换强度：

1. 要从阅读版升级到调用版入口时，先确认用户确实需要可调用 API，而不是只要可读源码。
2. 要执行目标样本中的解密初始化 IIFE、字符串解密函数或可疑自执行代码时，先说明执行范围、沙箱方式和可能副作用；不能确认安全时只做静态替换或插桩版输出。
3. 要做 dispatcher 内联、while-switch 全展开、对象分发表深度合并等高风险语义变换时，先保留上一轮中间文件，并说明本轮可能改变运行语义。
4. 要复制 `scripts/template-project/` 或新增长期维护目录时，先确认用户希望进入持续收敛模式；单次阅读版优先使用最小脚手架。
5. 静态还原后仍依赖运行时状态、浏览器环境或网络样本时，不要声称“已完全还原”；先交残留说明，并建议转 `camoufox-js-reverse`、`env-patch` 或 `web-protocol-recovery`。

## 工作目录

```text
project/
├── source/
│   ├── original/
│   │   └── target.js
│   └── deobfuscated/
│       └── target_deobf.js
├── intermediate/
│   ├── target_step0.js
│   ├── target_step1.js
│   └── ...
├── scripts/
│   ├── deobfuscate_target.js
│   ├── step1_family_detect.js
│   ├── step2_string_restore.js
│   └── ...
└── decode-action-workspace/        # 可选：从 scripts/template-project/ 复制出的目录版模板
    ├── input.js
    ├── output.js
    ├── package.json
    └── src/
        ├── main.js
        ├── plugins/
        └── visitors/
```

原则：`<target-project>/scripts/deobfuscate_target.js`、`<target-project>/scripts/stepN_*.js`、`<target-project>/decode-action-workspace/` 都是执行 skill 时写入目标项目的产物，不是 skill 内置文件引用；skill 自带资源只有 `scripts/decode_action_scaffold.js` 和 `scripts/template-project/`。每一步读取上一步输出，生成新文件，不覆盖原始输入。

## 关键约束（必读）

不要默认这样做：

1. 一上来就写一个 500 行 visitor 处理所有模式。
2. 还没识别家族就直接暴力替换所有 CallExpression。
3. 在同一份 AST 上叠十几轮替换却不重新 parse。
4. 把运行时依赖很强的逻辑硬说成静态已还原。


## 执行方式

### Step 0: 先识别家族，不要先写大而全 pass

优先回答这 5 个问题：

1. 是 `sojson` / `sojsonv7` / `obfuscator` / `awsc` / `jjencode` / `common` 的哪一类，还是混合体。
2. 有没有“全局字符串解密函数 + 大字符串数组 + 预处理 IIFE”。
3. 有没有 `while(true){switch(...)}`、顺序表、dispatcher object。
4. 有没有反调试、自卫函数、console 封锁、版本检查。
5. 有没有零宽字符、不可见 Unicode、异常 BOM 或混入源码的不可见载荷；命中时先做字符级清理和可视化，不要直接进入 AST pass。

命中家族后，优先读取 `references/decode-action-pipelines.md` 里的对应 pipeline。

如果命中控制流平坦化，再读 `references/control-flow-patterns.md`。

如果静态还原后仍有 VM/VMP 风格残留，再读 `references/instrumentation-patterns.md`。

如果用户要“先跑出第一版结果”的脚手架，再读 `references/template-usage.md` 并复制 `scripts/decode_action_scaffold.js`。

如果用户要“像仓库那样长期维护”的目录版模板，同样读 `references/template-usage.md`，但优先复制 `scripts/template-project/`。

目录版模板现在已经自带 `package.json`，复制后优先让用户直接 `npm install`、`npm run decode` 跑第一版结果，而不是再手动组装依赖。

如果已经有第一版输出，读 `references/residue-metrics.md`，并在目录版模板里运行 `npm run metrics` 或直接运行 `node src/tools/collect-residue-metrics.js output.js`。

### Step 1: 建最小 pipeline

参照 `Decode_action-main`，把 pass 拆成小块，而不是一次 traverse 里做所有事。仓库中 `src/plugin/*.js` 处理家族策略，`src/visitor/*.js` 处理单一变换；本 skill 的目录版模板沿用同样职责，只是目录名使用复数 `plugins/visitors`。

常见 pass 组件：

1. 字面量清理：删除 `extra`，把 `\x` / `\u` 还原成正常字面量
2. 常量折叠：二元表达式、字符串拼接、布尔混淆
3. 对象合并：把分散赋值合并回 object literal
4. 控制流还原：顺序表、dispatcher object、while-switch
5. 死代码清理：恒真恒假分支、空语句、未使用变量
6. 环境限制清理：反调试、自卫、console 封锁、版本弹窗
7. 可读性修复：member access 规范化、sequence 拆分、条件表达式转 if

### Step 2: 多轮执行

推荐按轮次推进：

1. `step0`: 格式化 + 基础体检
2. `step1`: 家族专属入口 pass
3. `step2`: 字符串/常量恢复
4. `step3`: 控制流和对象分发表收敛
5. `step4`: 死代码与环境限制清理
6. `step5`: 可读性整理与最终输出

每轮结束后都重新 parse。这样做的原因：

1. 让后续 visitor 面对更简单的 AST
2. 降低作用域缓存过期和路径失效问题
3. 便于定位是哪一轮引入了错误

### Step 3: 默认优先做目标定制，不追求“万能自动解”

`Decode_action-main` 的价值不是“所有脚本都一把梭”，而是：

1. 入口读取 `input.js`，根据候选 plugin 尝试变换，输出 `output.js`
2. 先自动路由到最像的家族
3. 再按该家族常见结构组合 pass
4. 如果失败，继续换下一个 plugin，而不是硬顶一个错误假设

因此当前 skill 也应这样工作：

1. 先写最像该目标的 pipeline
2. 不命中再切换策略
3. 不要为了通用性把高风险替换默认打开

新增经验规则：

1. 默认优先“可运行 + 可阅读”，不是“最大化内联”
2. 对库型样本（如 CryptoJS、webpack runtime、自定义基础库），优先做字符串恢复和语义别名，不要一开始就激进合并对象/代理函数
3. 只有在局部验证过语义不变时，才继续做 dispatcher 内联和深层 while-switch 展开

## 推荐路由

### sojson / sojsonv7

优先顺序：

1. 运行解密初始化代码
2. 只替换命中的解密函数调用和成员访问
3. 收敛局部控制流存储、字符串拼接、常量表达式
4. 清理反调试、自卫和 console 封锁
5. 重新 parse 后做可读性整理

### obfuscator / obfuscator2

优先顺序：

1. 基础字面量清理
2. 合并拆散对象和 dispatcher table
3. 处理顺序表、while-switch、平坦化控制流
4. 删除死代码和未使用变量
5. 最后再做 member access 和 sequence 规范化

### awsc

优先顺序：

1. `void`、条件表达式、逻辑表达式、sequence 拆分
2. `if` / `switch` / `return` 结构整理
3. 代码块扁平化为正常语句块
4. 再做常量折叠和可读性整理

### jjencode

优先顺序：

1. 先剥壳拿到正常 JS
2. 再把后续工作交给 `common` 或对应家族 pipeline

### common

只做低风险通用 pass：

1. 删除 `extra`
2. 常量折叠
3. 字符串拼接
4. 未使用变量清理

## 输出标准

一次完整交付至少包含：

1. 可运行脚本
2. 最终输出代码
3. 至少一个关键回退点的中间文件
4. 语法校验结果
5. 残留说明，不要只说“基本完成”

如果静态还原后仍有高价值残留结构，额外补交：

1. 目标项目中的 `<target-project>/scripts/instrument_target.js`
2. `intermediate/target_instrumented.js`
3. 插桩目的和下一步收敛建议


## 最小回答结构

完成时优先给出：

1. 命中的混淆家族和判断依据
2. 本轮使用的 pipeline 和关键 pass
3. 产出文件路径
4. 仍未自动化的残留结构

如果本轮是从模板起手，还要补一句：模板命中的首个 plugin 是什么、下一步建议在哪个函数或 visitor 里继续加 pass。

如果本轮交付的是阅读版，还要补一句：为了保运行语义，本轮故意没做哪些激进内联。

## 参考文件

1. `references/decode-action-pipelines.md`：基于 `Decode_action-main` 的插件/visitor 架构与家族流水线
2. `references/control-flow-patterns.md`：dispatcher object 与 while-switch 还原骨架
3. `references/instrumentation-patterns.md`：静态还原不彻底时的插桩策略
4. `references/template-usage.md`：如何把附带脚手架复制到目标项目，先跑出第一版结果
5. `scripts/decode_action_scaffold.js`：可直接复制和改造的起手模板
6. `scripts/template-project/`：更接近 `Decode_action-main` 维护方式的目录版工程模板
7. `references/residue-metrics.md`：解混淆输出的残留结构度量与参考产物对比
