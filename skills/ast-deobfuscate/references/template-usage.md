# Template Usage

这份文档说明如何使用本 skill 附带的 `scripts/decode_action_scaffold.js`。

它的定位不是“一键彻底解完所有混淆”，而是：

1. 先基于 `Decode_action-main` 的结构快速跑出第一版结果
2. 先做家族识别和低风险清理
3. 让后续定制 pass 有一个更干净的起点

## 两种交付模式

根据用户目标，先选交付模式，再决定要不要继续激进变换：

1. **阅读版输出**
   - 目标：给人看，便于继续人工分析
   - 默认不加 `require` / `module.exports` / 调用包装
   - 优先做：字符串恢复、低风险整理、确定性重命名、关键入口手工顺序化

2. **调用版输出**
   - 目标：直接拿来跑或集成
   - 可以额外补导出、包装函数、调用入口
   - 仅在用户明确要“直接调用”时再做

默认优先阅读版，不要把两者混成一个产物。

## 适合什么场景

下面这些场景优先用模板起手：

1. 刚拿到一份新混淆样本，还不确定具体家族
2. 想先快速看看低风险 pass 后结构会不会明显变清晰
3. 打算按 plugin/visitor 风格继续细化，但不想每次从零搭框架

## 模板提供了什么

`scripts/decode_action_scaffold.js` 里已经带了这些能力：

1. `-i` / `-o` 输入输出参数
2. `parse -> transform -> generate` 主流程
3. plugin 链路与首个命中插件落地策略
4. 通用低风险 visitor：
   - 删除 `extra`
   - 二元表达式折叠
   - `![]` / `!![]` 布尔还原
   - 相邻字符串拼接
   - `obj['x'] -> obj.x`
   - sequence statement 拆分
   - 恒定 `if` 清理
   - 空语句与未使用变量清理
5. 初始家族插件：
   - `obfuscator`
   - `sojsonv7`
   - `sojson`
   - `awsc`
   - `common`
6. 一个简单的 `while-switch` 展开器

## 推荐起手方式

### 1. 复制模板到目标项目

建议复制为：

```text
project/
├── source/original/target.js
├── source/deobfuscated/
├── intermediate/
└── <target-project>/scripts/deobfuscate_target.js
```

把 `decode_action_scaffold.js` 复制成 `<target-project>/scripts/deobfuscate_target.js`。注意：带 `<target-project>/` 的路径都是目标项目内生成产物，不是 skill 内置文件。

### 2. 安装最小依赖

```bash
npm init -y
npm install @babel/parser @babel/traverse @babel/generator @babel/types
```

### 3. 先直接跑第一版

```bash
node <target-project>/scripts/deobfuscate_target.js -i source/original/target.js -o source/deobfuscated/target_deobf.js
```

先看输出里的 `plugin=`，它就是当前脚手架判定的首个命中家族。

## 如何继续改模板

### 情况 1：输出已经明显变清晰

继续沿当前插件增强：

1. 增加更强的 visitor
2. 每加一组 pass 就重新 parse
3. 保留中间文件，别直接覆盖唯一输出
4. 每做一轮激进内联前，先确认当前版本还能运行或至少能稳定解析

### 情况 2：命中了 sojson/sojsonv7，但字符串没还原

说明该样本需要“运行初始化代码 + 定点替换 decrypt call”的专项 pass。

在模板里改 `runSojson()`：

1. 识别字符串数组、预处理函数、解密函数
2. 只执行最小必要初始化片段
3. 只替换命中的 decrypt call / member access
4. 再走 `runCommon()`

目录版模板现在已经内置了这条最小链路，可以直接先跑，再按样本收紧 bootstrap 识别范围。

当前这条链路还会优先选择“在 bootstrap 候选里被高频调用/高频成员访问”的函数作为解密候选，适合常见 sojson 变体，但仍不该把它当成全变体自动识别器。

### 情况 3：命中了 obfuscator，但 while-switch 只展开了一部分

优先补：

1. dispatcher object 合并和内联
2. 顺序表变种识别
3. `continue` / `break` 尾巴清理

目录版模板现在已经内置了：

1. `merge-object.js`
2. `inline-dispatcher.js`
3. `while-switch-unpack.js`

如果第一版输出还是不够干净，下一步优先增强这 3 个 visitor，而不是先动 `common`。

当前 `while-switch-unpack.js` 已经覆盖这些常见变体：

1. `while(true)` / `while(!0)`
2. `switch(order[idx++])`
3. `switch(order[++idx])`
4. `switch(order[idx])` 配合循环体外部自增
5. `order` 来自 `'2|0|1'.split('|')`
6. `order` 来自 `['2', '0', '1']`
7. `case` 内部再包一层或多层 block
8. 前置空 `case` 落到后一个 `case` 的 fallthrough 链

如果样本是“case 中动态改写 state 再跳下一轮”的状态机，就不要再强推静态展开，应及时转插桩。

当前 `inline-dispatcher.js` 已经只对几类安全代理做内联：

1. `return a + b`
2. `return a && b`
3. `return fn(arg1, arg2)`
4. `return obj[prop]`
5. `return cond ? a : b`

如果遇到闭包、`this`、`arguments`、赋值副作用，就不要继续放宽默认规则。

补充一条实战规则：如果样本本质上是一个库或大基础对象（例如 CryptoJS 一类），先不要急着对全文件做对象代理内联。优先保留结构并加语义别名，否则很容易把可运行代码改坏。

### 情况 4：命中了 awsc，但还是很多三元和 block 嵌套

继续增强结构整形 pass：

1. 处理 `return (a(), b(), c())`
2. 处理 `if` 测试里的 sequence expression
3. 处理 `switch case` 内 block 归一化

## 模板的边界

单文件脚手架 `scripts/decode_action_scaffold.js` 默认不做这些高风险动作：

1. 不直接执行整份混淆脚本
2. 不自动做 sojson 真正的解密函数求值
3. 不自动内联复杂 dispatcher function
4. 不自动处理 VM/VMP 状态机
5. 不默认把阅读版产物改造成调用版产物

原因不是不能做，而是这些步骤必须先看具体样本，否则很容易误替换。

目录版模板 `scripts/template-project/` 比单文件脚手架更进一步：`sojson` plugin 会在受限 Node VM 里执行前置 bootstrap，并只求值参数可静态确定的解密调用；这不是执行整份业务脚本。目录版的 `common` plugin 保持低风险通用 pass，高风险对象代理内联和 dispatcher 展开应放在 `obfuscator` 或目标专项 plugin 中。

## 一条实用规则

当拿到新样本时，优先流程应该是：

1. 先跑模板
2. 观察命中的 plugin 和输出结构
3. 再针对该家族补专项 pass
4. 静态还原收益变低时，切到插桩

这样比从零写一个大脚本更稳定，也更接近 `Decode_action-main` 真正有价值的工作方式。

## 什么时候升级到目录版模板

满足任一条件时，建议从单文件升级到 `scripts/template-project/`：

1. 已经开始加第 2 个以上的专项 visitor
2. 需要同时维护 `common` 和某个家族专用 pipeline
3. 想把 visitor 复用到多个样本
4. 想把 sojson、obfuscator、awsc 的改动分开管理

目录版模板的优势：

1. `src/main.js` 只负责入口与路由
2. `src/plugins/*.js` 只负责家族级 pipeline
3. `src/visitors/*.js` 只负责单一 AST 变换
4. 更接近 `Decode_action-main` 的真实维护方式
5. 现在已经自带 `sojson` 最小解密入口和 `dispatcher object` 处理骨架

推荐路径：

1. 第一次拿到样本，用 `scripts/decode_action_scaffold.js`
2. 样本确认值得继续投入后，迁移到 `scripts/template-project/`
3. 后续所有专项 visitor 都只往目录版模板里加

## 目录版模板的直接运行方式

`scripts/template-project/` 现在已经自带 `package.json`，复制到目标项目后可以直接：

```bash
npm install
npm run decode
```

如果需要量化第一版输出的残留结构：

```bash
npm run metrics
```

或者显式指定文件：

```bash
node src/tools/collect-residue-metrics.js output.js metrics.json
```

如果有人工整理版或其它参考产物：

```bash
node src/tools/compare-with-reference.js output.js reference.js compare.json case-id
```

这些工具只做 AST parse 和结构统计，不执行目标样本代码。具体指标解释见 `references/residue-metrics.md`。

如果你要检查模板入口和插件文件语法，也可以跑：

```bash
npm run check
```

## 如何用 evals 做回归

这个 skill 现在已经带了 `evals/evals.json`，可以把它当成回归检查清单。

建议关注 3 类结果：

1. 是否选对起手路径：单文件脚手架还是目录版模板
2. 是否选对家族方向：sojson / obfuscator / awsc / common
3. 是否在边界场景下正确转交或停止硬还原

其中最重要的负例是：

1. 浏览器 hook 请求应转 `browser-hook-snippets`
2. 参数入口定位应转 `camoufox-js-reverse`
3. 运行时 state 驱动的 while-switch 应转插桩，而不是继续默认静态展开
