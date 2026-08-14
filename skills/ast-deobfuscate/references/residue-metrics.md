# Residue Metrics

这份参考用于在 AST 解混淆后量化残留结构。它不是新的默认 pass，也不替代人工阅读；它帮助判断下一轮应该补哪个 visitor 或是否需要插桩。

## 工具位置

目录版模板包含两个可选工具：

1. `scripts/template-project/src/tools/collect-residue-metrics.js`
2. `scripts/template-project/src/tools/compare-with-reference.js`

复制 `scripts/template-project/` 到目标项目并安装依赖后使用。

运行前需要在目录版模板或目标项目里执行 `npm install`，确保 `@babel/parser`、`@babel/traverse`、`@babel/generator`、`@babel/types` 已安装。

## collect-residue-metrics

统计当前输出中常见残留：

1. `.split('|')` 顺序表。
2. `while/for + switch` 平坦化。
3. opcode 风格 `if` 链。
4. dispatcher wrapper 对象。
5. `_0x` 风格标识符。
6. 行数。

```bash
node src/tools/collect-residue-metrics.js output.js metrics.json
```

输出示例：

```json
{
  "lineCount": 1200,
  "splitPipeCount": 3,
  "loopSwitchCount": 2,
  "opcodeIfChainCount": 16,
  "dispatcherWrapperCount": 8,
  "hexIdentifierCount": 140
}
```

## compare-with-reference

当你有参考产物或人工整理版时，可以比较当前输出与参考输出的残留差距：

```bash
node src/tools/compare-with-reference.js output.js reference.js compare.json case-id
```

重点看：

1. `status`
2. `gaps`
3. `ours` 与 `reference` 的指标差异。

## 使用原则

1. 指标只能提示残留方向，不能证明语义正确。
2. 行数更少不一定更好；优先保证语法和运行语义。
3. 如果 `loopSwitchCount` 或 `opcodeIfChainCount` 稳定存在，再补控制流 visitor。
4. 如果 `dispatcherWrapperCount` 很高，优先补 dispatcher object 内联。
5. 如果 `_0x` 标识符很多但结构已清楚，可以最后再重命名，不要为了指标提前激进 rename。

## 安全边界

这两个工具只 parse/generate/统计 AST，不执行目标样本代码。相比 VM-backed decoder pass，风险更低，适合作为默认评估辅助工具。
