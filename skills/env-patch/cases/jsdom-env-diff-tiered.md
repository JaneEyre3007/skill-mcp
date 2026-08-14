# jsdom 环境差异分级

## Summary

当目标 JS 在最小环境中始终跑不通，且环境值明显参与签名、cookie 或请求链路时，进入 jsdom 路径。这个 case 用来记录“先修哪一层、什么时候停手”。

## Keywords

1. `jsdom`
2. `Function.prototype.toString`
3. `navigator.plugins`
4. `navigator.webdriver`
5. `document.hasFocus`
6. `offsetHeight`
7. `Symbol.toStringTag`

## Anti-Bot Type

1. 行为型
2. 签名型

## Recommended Path

1. jsdom 环境伪装

## Entry Clues

记录最有效的入口线索：

1. 最小环境已补到核心宿主，但结果仍然降级
2. HTTP 200 但空 body / 静默拒绝
3. 日志显示目标反复读取宿主对象外形相关字段
4. `toString`、布局值、plugins、webdriver 相关检测明显存在

## Required Environment Items

记录必补项：

1. `Function.prototype.toString`
2. `navigator.webdriver`
3. `navigator.plugins` / `mimeTypes`
4. `document.hasFocus()`
5. DOM 布局值：`offsetHeight` / `offsetWidth` / `getBoundingClientRect`

## Explicit Undefined Items

记录必须“存在但值为 undefined”的项：

1. `window.ActiveXObject`（命中时）
2. 某些站点检测的占位属性

## Unnecessary Items

记录明确试过但当前目标不需要补的项：

1. 没有命中时不要先补全 `window` 全家桶
2. 没有命中时不要先补 `Notification`、`Worker`、`caches` 等中危 API
3. 没有命中时不要先造完整指纹生态

## Key Pitfalls

记录最容易重踩的坑：

1. `toString` patch 重复叠加，反而更假
2. `plugins` 只补了 `length`，但目标还会读 `item()`、`namedItem()`、`toStringTag`
3. 布局值全是 0，会直接暴露没有渲染环境
4. 还没验证致命级，就开始堆高危级和中危级
5. 补丁顺序晚于目标脚本加载，导致 patch 实际没生效

## Minimal Verifiable Facts

尽量写成可以快速复验的事实：

1. `document.createElement.toString()` 需要呈现 native 外形
2. `navigator.webdriver` 在目标里被读取
3. `navigator.plugins.length` 在目标里被读取
4. `document.hasFocus()` 在目标里被读取
5. 某类目标对 DOM 布局值是否为 0 很敏感

## Validation

记录最后怎么确认跑通：

1. 致命级补丁完成后，签名格式开始收敛
2. 高危级补丁只针对真实访问项追加
3. 请求返回不再是静默拒绝或空 body

## Notes

这个 case 不是给某个特定站点用的，而是给所有“需要从最小环境升级到 jsdom”的目标沉淀通用经验。
