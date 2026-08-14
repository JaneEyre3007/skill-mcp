# WASM 签名加载

## Summary

当加密逻辑主要在 `.wasm` 中实现，JS 只负责加载、桥接和喂参数时，优先走 WASM 加载路径，而不是先做大规模浏览器环境伪装。

## Keywords

1. `.wasm`
2. `WebAssembly.instantiate`
3. `WebAssembly.instantiateStreaming`
4. `imports`
5. `exports`
6. `memory`

## Anti-Bot Type

1. 行为型
2. 纯混淆

## Recommended Path

1. WASM 加载
2. 最小环境复现

## Entry Clues

记录最有效的入口线索：

1. JS 中出现 `WebAssembly` 加载逻辑
2. 网络请求里能拿到 `.wasm` 文件
3. JS 负责准备参数，再调用导出函数
4. 出现缺失 `imports` 或 `memory` 相关报错

## Required Environment Items

记录必补项：

1. `.wasm` 文件本体
2. JS 桥接层
3. `imports` 所需的最小宿主对象
4. 需要时的 `TextEncoder` / `TextDecoder`

## Explicit Undefined Items

记录必须“存在但值为 undefined”的项：

1. 按浏览器对照结果补，只有 JS 桥接层显式探测时才处理

## Unnecessary Items

记录明确试过但当前目标不需要补的项：

1. 不要一上来先补完整 DOM
2. 不要因为看到前端页面就默认进入 jsdom 路径

## Key Pitfalls

记录最容易重踩的坑：

1. 还没搞清楚 `imports` 就先补大环境
2. 没先确认导出函数输入输出，直接盲猜算法
3. JS 桥接层里的编码转换被忽略，导致结果不一致

## Minimal Verifiable Facts

尽量写成可以快速复验的事实：

1. `.wasm` 文件能被定位到
2. 导出函数名或调用入口可确认
3. JS 侧会在调用前做参数编码或内存写入
4. 某些错误来自缺失 `imports`，不是算法本身错误

## Validation

记录最后怎么确认跑通：

1. 导出函数可被独立调用
2. 输出值与浏览器样本一致
3. 最终请求可稳定通过

## Notes

这个 case 更适合沉淀“`.wasm` 与 JS 桥接层的边界、`imports` 最小需求、导出函数验证方式”这类经验，而不是先补全整套浏览器环境。
