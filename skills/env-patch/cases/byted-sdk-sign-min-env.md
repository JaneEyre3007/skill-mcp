# 字节系 SDK 签名最小环境

## Summary

页面正常加载，签名多在 SDK 或请求拦截器内部追加，常见字段如 `a_bogus`、`X-Bogus`。优先走最小环境复现或 vm 沙箱，只有环境绑定明显时再升级 jsdom。

## Keywords

1. `a_bogus`
2. `X-Bogus`
3. `X-Gnarly`
4. `_sdkGlueInit`
5. `byted_acrawler`
6. `bdms`
7. `cacheOpts`

## Anti-Bot Type

1. 行为型

## Recommended Path

1. 最小环境复现
2. vm 沙箱
3. jsdom 环境伪装

## Entry Clues

记录最有效的入口线索：

1. 请求拦截器是否劫持 `XMLHttpRequest` 或 `fetch`
2. 是否导出签名函数到 `window`
3. `bdms` / `acrawler` / SDK 初始化函数
4. 目标请求路径和签名字段追加位置

## Required Environment Items

记录必补项：

1. `window`
2. `document`
3. `navigator`
4. `location`
5. `screen`
6. `XMLHttpRequest`
7. 必要时的 `document.all`

## Explicit Undefined Items

记录必须“存在但值为 undefined”的项：

1. 按浏览器对照结果补，常见是某些 SDK 占位字段

## Unnecessary Items

记录明确试过但当前目标不需要补的项：

1. 首轮不要直接上全量 jsdom 补丁
2. 不要默认把所有指纹 API 都补一遍

## Key Pitfalls

记录最容易重踩的坑：

1. 日志太多时会淹没真正关键的调用链
2. 先看 `ERRORS / UNDEFINED / CALLS`，再开定向代理更高效
3. 有些场景真正关键的是 `XMLHttpRequest.prototype` 或拦截器链，而不是整个 DOM
4. 结果必须先看签名格式是否一致，不能只看 HTTP 200

## Minimal Verifiable Facts

尽量写成可以快速复验的事实：

1. `location.href` / `pathname` 经常参与签名链
2. `navigator.userAgent`、`platform`、`language` 常被访问
3. `document.createElement` 往往会被调用
4. `XMLHttpRequest.open/setRequestHeader/send` 常是关键链路
5. 某些目标会读取 `document.all`

## Validation

记录最后怎么确认跑通：

1. 签名字段长度、前缀、结构与浏览器一致
2. 请求返回真实业务数据
3. 重复请求结果稳定

## Notes

这个 case 更适合沉淀“是函数导出型还是拦截器型”“哪些宿主对象最先补”“哪些字段只是噪音”这类经验。
