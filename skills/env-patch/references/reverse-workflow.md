# 逆向工作流

这份文档吸收了外部逆向 skill 的方法论，但全部改写为当前 `env-patch` 可执行的版本，不依赖 `camoufox-reverse MCP`。

## 1. 先分类型

开始补环境前，先判断目标更接近哪一类：

### A. 签名型反爬

特征：

1. 首屏就进入 challenge 流程，常见现象是 `412`、`202`、`204`、`302`、挑战页或动态 cookie
2. 主要难点在 challenge cookie 生成链，而不是业务参数本身
3. 典型如瑞数、Akamai 一类

优先策略：

1. 先确认是不是 challenge 文档、外链 JS、动态参数、cookie 生成这条链路
2. 优先走最小环境、vm 沙箱、sdenv 类思路
3. 代理日志必须收缩，避免卡死
4. 如果首跳 challenge 文档每次都会变，先固定一份样本再调试，避免在动态返回上来回追偏差

### B. 行为型反爬

特征：

1. 页面能正常加载，业务请求里带 `a_bogus`、`X-Bogus`、`token`、`sign` 这类字段
2. 目标 JS 可能劫持 XHR/fetch 或导出签名函数
3. 常见于字节系、SDK 型签名

优先策略：

1. 先确认是“函数导出”还是“请求拦截器追加签名”
2. 优先走算法还原、最小环境复现、vm 沙箱
3. 环境伪装只在算法难拆时升级使用

### C. 纯混淆

特征：

1. 主要问题是 `_0x`、控制流平坦化、eval 打包、webpack 壳
2. 没有明显环境依赖
3. 没有复杂 challenge cookie / 签名链

优先策略：

1. 先做混淆还原和入口定位
2. 再决定是否需要补环境

## 2. 路径选择

### 路径 1：纯算法还原

适用：

1. 加密逻辑已拆出来
2. 可以直接用 Node.js / Python 复现

补环境只做：

1. 辅助确认中间值
2. 验证是否还有隐形环境依赖

### 路径 2：最小环境复现

适用：

1. 只依赖少量 `window/document/navigator/location`
2. 目标 JS 可直接在 Node 中 require 执行

这是当前 `env-patch` 的默认路径。

### 路径 3：vm 沙箱

适用：

1. 目标 JS 动态下发
2. eval 首包 / challenge 文档 / 动态 cookie / 预热脚本
3. 不值得完全手拆
4. 动态文本要先原样保存，确认是否存在格式化检测，再决定后续如何调试

### 路径 4：jsdom 环境伪装

适用：

1. JSVMP 深度依赖环境
2. 环境值参与签名或请求链路
3. 最小环境始终跑不通

### 路径 5：WASM 加载

适用：

1. 逻辑在 `.wasm`
2. JS 只负责桥接和喂参数

## 3. 环境差异分级

### 致命级

优先修这些：

1. `Function.prototype.toString`
2. `navigator.webdriver`
3. `navigator.plugins` / `mimeTypes`
4. `document.hasFocus()`
5. DOM 布局值如 `offsetHeight` / `offsetWidth`

### 高危级

视实际访问决定：

1. `Symbol.toStringTag`
2. `Object.prototype.toString.call(...)`
3. `window.chrome`
4. `performance.timing` / `performance.navigation`
5. `navigator.userAgentData`
6. `navigator.connection`

### 中危级

只在实际读到时补：

1. `Notification`
2. `Worker` / `SharedWorker`
3. `RTCPeerConnection`
4. `matchMedia`
5. `indexedDB`
6. `caches`

## 4. 请求失败排查顺序

脚本返回异常时，按这个顺序排：

1. `cookie_s` / `cookie_t` / Session 是否过期、缺失或顺序不对
2. 是否漏了首跳 challenge 请求、预热请求、配置请求
3. 时间戳精度和取值时机是否一致
4. Header / Referer / Origin / Accept / 自定义头是否缺失
5. 环境值是否真的参与最终请求或签名
6. 是否存在频率限制、HTTP/2、TLS 指纹等协议层问题

## 5. 签名不一致排查链

从前往后逐项对：

1. 原始入参
2. 参数排序与拼接字符串
3. 时间戳
4. 随机串
5. 密钥 / 盐 / IV
6. 中间摘要
7. 最终编码输出

原则：找到**第一个偏差点**，不要同时改 5 个地方。

## 6. 降级梯度

卡住时按这个梯度走：

### 梯度 0：先看已有经验

1. 工作区是否已有同站点目录
2. 是否已有老脚本、老样例、老日志
3. 是否已有近似站点案例

### 梯度 1：用好手头证据

1. 重新读已有抓包、样例、请求参数
2. 重新看 `env.report()` 的 `ERRORS / UNDEFINED / CALLS`
3. 检查是不是高频缺项还没真正补到位

### 梯度 2：收缩或切换监控方式

1. 从全局递归代理切到单对象 `monitor()`
2. 从对象级日志切到方法级 `wrapFunc()`
3. 瑞数 challenge 类站点卡死时直接减少 Proxy 覆盖面

### 梯度 3：点对点补关键宿主

1. 只补 `document.createElement`
2. 只补 `XMLHttpRequest.prototype.send`
3. 只补 `navigator.plugins`
4. 只补 `document.cookie` / `localStorage`

### 梯度 4：升级路径

1. 从最小环境升级到 vm 沙箱
2. 从最小环境升级到 jsdom 环境伪装
3. 从普通 JS 升级到 WASM 路径

### 梯度 5：合法停点

如果仍然卡住，输出：

1. 卡在哪
2. 已确认哪些事实
3. 下一步最需要什么信息

不要用“临时浏览器跑一遍、把结果硬编码”来伪装成完成。

## 7. 最终验证要求

补环境不是“单次跑通就结束”，至少确认：

1. 签名长度和格式稳定
2. 重复多次请求结果一致
3. 关键 cookie / token 不是人工硬编码产物
4. `cookie_s` / `cookie_t` 更新关系或 challenge 到业务响应的链路可复现
5. 当前脚本脱离浏览器常驻依赖后仍可运行
