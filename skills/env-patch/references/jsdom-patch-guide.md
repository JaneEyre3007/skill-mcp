# jsdom 补丁指南

这份文档给 `env-patch` 的 jsdom 路径提供一个更聚焦的补丁顺序。目标不是“一次补全所有浏览器 API”，而是按风险和收益补最少的东西。

## 适用时机

只有在这些情况出现时再进入 jsdom 路径：

1. 最小环境复现始终失败
2. 目标是 JSVMP、SDK 拦截器、深度环境绑定
3. 环境值明显参与签名或请求链路

## 补丁顺序

### 第一层：致命级

先检查并优先修复：

1. `Function.prototype.toString`
2. `navigator.webdriver`
3. `navigator.plugins` / `mimeTypes`
4. `document.hasFocus()`
5. DOM 布局值：`offsetHeight`、`offsetWidth`、`getBoundingClientRect`

这些项没修好时，继续补其他 API 的收益通常很低。

### 第二层：高危级

在实际命中后再修：

1. `Symbol.toStringTag`
2. `Object.prototype.toString.call(...)`
3. `window.chrome`
4. `performance.timing` / `performance.navigation`
5. `navigator.userAgentData`
6. `navigator.connection`

### 第三层：中危级

仅在日志或调用链确认后再加：

1. `Notification`
2. `Worker` / `SharedWorker`
3. `RTCPeerConnection`
4. `matchMedia`
5. `indexedDB`
6. `caches`
7. `visualViewport`

## toString 修复原则

如果走 jsdom，`Function.prototype.toString` 往往是第一杀手。

建议原则：

1. 只 patch 一次
2. 先标记已知宿主函数
3. 再做少量兜底规则
4. 不要重复叠加多个版本的 toString patch

## 插件与 mimeTypes

`navigator.plugins` 不是只补 `length` 就够。常见需要：

1. `item()`
2. `namedItem()`
3. `Symbol.toStringTag`
4. `plugins[i]`
5. `mimeTypes[i]`

如果站点只读 `length`，就不要过度搭完整树。

## 布局属性

jsdom 没渲染引擎，默认布局值常常全是 0。

常见做法：

1. 让带尺寸 style 的元素返回非零 `offsetHeight/offsetWidth`
2. `getBoundingClientRect()` 返回结构完整的矩形对象
3. 不追求精确像浏览器，只要不触发明显异常检测

## UA 自洽原则

补环境时保持自洽：

1. 如果声明的是 Chrome 风格 UA，就不要缺 `window.chrome`
2. 如果声明的是不支持某特性的旧环境，就不要反而补出新接口
3. `userAgent`、`platform`、`vendor`、`screen`、`connection` 要尽量能互相说得通

## 明确存在但值为 undefined

某些字段不能靠“不定义”代替，典型如：

1. `window.ActiveXObject`
2. 某些站点会检测的 `chrome`
3. 某些宿主字段的占位属性

这时要区分：

1. 属性不存在
2. 属性存在，但值是 `undefined`

## 何时停止继续补

出现这些情况时，先不要继续往下堆：

1. 还没验证致命级是否修好
2. 还没确认某个高危字段真的被访问
3. 代理日志已经开始严重影响运行
4. 签名格式已经对了，只剩请求链路问题

## 一个推荐节奏

1. 先最小环境复现
2. 不通再进入 jsdom
3. 先修致命级
4. 再看 `monitor()` / `wrapFunc()` 命中的高危项
5. 逐项验证
6. 签名格式稳定后停止继续堆补丁
