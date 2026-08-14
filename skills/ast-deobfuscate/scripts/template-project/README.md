# Decode Action Template Project

这是目录化模板，适合已经确认要持续迭代某个混淆目标的场景。

## 目录

```text
template-project/
├── input.js
├── output.js
├── package.json
└── src/
    ├── main.js
    ├── lib/
    │   └── core.js
    ├── plugins/
    │   ├── awsc.js
    │   ├── common.js
    │   ├── obfuscator.js
    │   ├── sojson.js
    │   └── sojsonv7.js
    └── visitors/
        ├── awsc-conditional-to-if.js
        ├── awsc-logical-to-if.js
        ├── awsc-normalize-blocks.js
        ├── awsc-void.js
        ├── constant-if.js
        ├── delete-extra.js
        ├── fold-binary.js
        ├── fold-boolean.js
        ├── inline-dispatcher.js
        ├── merge-object.js
        ├── merge-strings.js
        ├── normalize-member.js
        ├── remove-empty.js
        ├── remove-unused-var.js
        ├── split-sequence.js
        └── while-switch-unpack.js
```

## 起手

1. 把目标脚本放到 `input.js`
2. 安装依赖：

```bash
npm install
```

3. 运行：

```bash
npm run decode
```

如果你要自定义输入输出，也可以继续直接用：

```bash
node src/main.js -i input.js -o output.js
```

## 何时用这个模板

1. 你已经不满足于单文件脚手架
2. 你要对某个样本持续补 visitor
3. 你想把家族策略和 visitor 分开维护

## 工作方式

1. `src/main.js` 负责插件路由
2. `src/plugins/*.js` 负责家族级 pipeline
3. `src/visitors/*.js` 负责单一 AST 变换
4. 每加一组 visitor 后，优先 `reparse()` 再进入下一轮

## 当前内置能力

1. `sojson` / `sojsonv7`：带最小解密入口模板
2. `obfuscator`：带对象合并、dispatcher 内联、增强版 while-switch 展开
3. `awsc`：带结构整形 visitor
4. `common`：带低风险通用清理 pass

## 还需要按样本继续补的地方

1. `sojson` 的 bootstrap 识别目前偏保守，只覆盖常见“前几句初始化 + 解密函数”结构
2. `inline-dispatcher` 目前只安全内联这几类常见代理：二元表达式、逻辑表达式、简单函数调用、简单成员访问、简单条件表达式
3. `while-switch` 目前支持字符串顺序表、数组顺序表、`idx++` / `++idx` / `order[idx]` 这类常见判别式，也支持 `case` 内 block 包裹和前置空 `case` 的 fallthrough 链，但仍不覆盖真正依赖运行时 state 的变体
4. 复杂 VM/VMP、动态状态机仍然应转插桩

## 回归样例

新增或修改 visitor 前，先看 `test-fixtures/README.md`。模板项目建议用小 fixture 回归单个结构，不要直接用大型真实 bundle 当模板回归样本。
