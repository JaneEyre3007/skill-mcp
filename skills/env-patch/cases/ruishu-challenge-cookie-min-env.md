# 瑞数 Challenge Cookie 最小环境

## Summary

首屏或前置请求常先进入瑞数 challenge 流程，而不是直接给业务数据；常见现象是返回 `412` challenge 文档，也有一部分目标表现为 `202`、`204` 或明显的两次请求流程。核心链路通常是“challenge 响应里的文档/脚本 -> 外链 JS 或继续解密 -> 生成动态 cookie -> 携带正确 cookie 重放请求后拿到 `200` 或真实业务响应”。常见现象是首跳拿到 `cookie_s`，重点是继续生成或更新 `cookie_t`。优先走最小环境复现，必要时再升级到 vm / jsdom。

## Keywords

1. `412`
2. `NfBCSins2OywS`
3. `NfBCSins2OywT`
4. `FSSBBIl1UgzbN7N`
5. `sdenv`
6. `ActiveXObject`
7. `cookie_s`
8. `cookie_t`

## Anti-Bot Type

1. 签名型

## Recommended Path

1. 最小环境复现
2. vm 沙箱
3. jsdom 环境伪装

## Entry Clues

记录最有效的入口线索：

1. `412` / `202` / `204` 对应的 challenge 响应
2. challenge 文档里的内联脚本和外链 JS 地址
3. `$_ts.nsd` / `$_ts.cd` / meta-content 一类动态参数
4. `cookie_s` 来自首跳响应、`cookie_t` 在脚本执行后更新
5. `document.cookie` 写入链路
6. `document.createElement` / `getElementsByTagName` / `getElementById`
7. `window.ActiveXObject`
8. 调试前先把首跳 challenge 文档固定下来，而不是每次直接追动态返回

## Required Environment Items

记录必补项：

1. `window.addEventListener`
2. `document.createElement`
3. `document.getElementsByTagName`
4. `document.cookie` 可写可读
5. `location.*`
6. `navigator.userAgent`
7. `setInterval` / `setTimeout`
8. `window.top = window`（命中时）

## Explicit Undefined Items

记录必须“存在但值为 undefined”的项：

1. `window.ActiveXObject`

## Unnecessary Items

记录明确试过但当前目标不需要补的项：

1. 不要默认把整个 `window` 都做重型原型链
2. 不要默认全量补 `screen` / `plugins` / `mimeTypes`

## Key Pitfalls

记录最容易重踩的坑：

1. 瑞数 challenge 类目标上大范围 Proxy 容易把代码拖慢或拖死
2. 有些字段不能靠“不定义”，而要显式设为 `undefined`
3. `document.createElement('div')` 返回值往往还要继续支持子方法调用
4. 从页面复制出来的 challenge 代码不要随手格式化，部分目标存在格式化检测

## Minimal Verifiable Facts

尽量写成可以快速复验的事实：

1. `window.ActiveXObject` 存在且值为 `undefined`
2. `document.createElement('div')` 会被调用
3. `document.getElementsByTagName('script')` 常被读取
4. challenge 文档里通常还能继续抽出外链 JS 或下一跳脚本地址
5. 首跳响应常会先带 `cookie_s`
6. `document.cookie` 最终应被写入动态 cookie，并出现 `cookie_t` 更新
7. 大范围代理开启后，运行可能明显变慢
8. `meta-content`、`$_ts.nsd`、`$_ts.cd` 这类动态参数需要原样提取后再调试
9. 某些页面只要求 `getElementsByTagName('i')` 返回最小 `{ length: 0 }` 结构即可继续执行

## Validation

记录最后怎么确认跑通：

1. challenge 响应里的 cookie 生成链能稳定复现
2. 携带生成后的 cookie 重放请求后能从 `412` / `202` / `204` challenge 进入 `200` 或真实业务响应
3. 重复请求时 cookie 链路稳定

## Notes

这个 case 更适合沉淀“challenge 文档到外链 JS 的入口、`cookie_s`/`cookie_t` 的更新关系、哪些宿主最先补、哪些字段必须显式 `undefined`、何时关闭代理”这类经验，而不是存一次性的 cookie 值。
