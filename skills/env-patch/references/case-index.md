# 案例索引与复用规则

这份文档用于把“先查已有经验再动手”的习惯固化下来，避免同站点、同类型问题反复从零开始。

## 第一原则

补环境前先查：

1. 当前工作区是否已有同站点目录
2. 是否已有旧版 `run.js` / `sign.js` / `mod.js`
3. 是否已有抓包样本、日志、请求参数样本
4. 是否已有近似站点案例

命中已有资料时：

1. 优先复用“踩坑记录”和“已验证事实”
2. 不直接照搬旧代码
3. 用当前样本重新验证入口、参数和环境依赖

## 工作区优先扫描

优先检查这些形态：

1. `site_<domain>/`
2. `<domain>_<date>/`
3. `env/`、`source/`、`python/` 结构目录
4. `mod.js`、`run.js`、`sign.js`、`cookie*.js`、`*_sample.json`

常见高价值文件：

1. `mod.js` — 最早的最小补环境样例
2. `run.js` — 已成型的加载顺序和补丁入口
3. `sign.js` — 最终导出函数接口
4. `cookies.txt` / `headers.json` / `params_sample.json` — 对照样本
5. `README.md` / `progress.md` — 旧方案的文字结论

## 站点指纹速查思路

看到下面这些特征时，先联想已有经验：

1. `a_bogus` / `_sdkGlueInit` / `byted_acrawler` / `bdms`
2. `X-Bogus` / `X-Gnarly` / `cacheOpts` / `webmssdk`
3. `412` / `202` / `204` / `NfBCSins2OywS` / `FSSBBIl1UgzbN7N` / `sdenv`
4. `_0x` 大量前缀 / `while-switch` / 超大单文件
5. `.wasm` / `WebAssembly.instantiate`

命中后要做的不是“复制代码”，而是：

1. 看旧方案到底走的是算法还原、最小环境、vm、jsdom 还是 WASM
2. 看旧方案最早卡在哪里
3. 看旧方案最后靠哪些宿主对象或补丁跑通

## 当前内置案例

| case | 适用场景 | 首选路径 | 关键关注点 |
|------|---------|---------|-----------|
| `ruishu-challenge-cookie-min-env.md` | 瑞数 / `412` `202` `204` challenge / 外链 JS / 动态 cookie | 最小环境 → vm | 显式 `undefined`、challenge 到 cookie 的写入链、代理收缩 |
| `ruishu-python-node-cookie-template.md` | 瑞数 / `412` challenge / Python 调度业务请求 / Node 执行动态 JS | 最小环境 → Python-Node 模板 | `412` 不直接判失败、按 `$_ts` 选脚本、`subprocess(node)`、结构化输出 |
| `byted-sdk-sign-min-env.md` | 字节系 SDK / 请求拦截器 / 签名字段 / `a_bogus` | 最小环境 → vm | `location` / `navigator` / `XMLHttpRequest` / 签名格式 |
| `jsdom-env-diff-tiered.md` | 最小环境已基本补齐但结果仍降级，准备升级到 jsdom | jsdom | 致命级补丁优先、差异分级、何时停手 |
| `wasm-sign-loader.md` | `.wasm` 参与签名或加密，JS 主要负责桥接和喂参数 | WASM → 最小环境 | 先看 `imports` / `exports`，再补最小宿主 |

## 快速命中边界

优先看 `ruishu-challenge-cookie-min-env.md`：

1. 首屏或前置请求直接进入瑞数 challenge，常见是 `412` 文档，也可能是 `202`、`204` 或两次请求流程
2. challenge 文档里的内联 JS 或外链 JS 会继续生成动态 cookie
3. 响应里能拿到 `$_ts.nsd` / `$_ts.cd` / meta-content 一类动态参数，或首跳响应直接设置 `cookie_s`
4. 重点是继续生成或更新 `cookie_t`
5. 带 cookie 重放后才进入 `200` 或真实业务响应
6. 看到 `NfBCSins2OywS`、`FSSBBIl1UgzbN7N`、`sdenv`、`ActiveXObject`

优先看 `ruishu-python-node-cookie-template.md`：

1. 首页 challenge 最终要由 Python `requests` 重放业务接口
2. Node 只负责执行动态 JS、产出 cookie 或 sign
3. 你不想让 `execjs.call()` 直接承受 stdout 日志和诊断报告
4. 需要把 challenge HTML、内联脚本、外链脚本、Node stdout/stderr 留档复盘

优先看 `byted-sdk-sign-min-env.md`：

1. 参数或请求头里出现 `a_bogus`、`X-Bogus`、`X-Gnarly`
2. 线索集中在 SDK、拦截器、`XMLHttpRequest` 或 `fetch`
3. 页面能正常加载，但签名在请求发出前被追加

优先看 `jsdom-env-diff-tiered.md`：

1. 最小环境里的 `ERRORS / UNDEFINED` 已基本收敛
2. 请求仍然空 body、静默拒绝或签名持续降级
3. 目标明显反复读取 `navigator.plugins`、`webdriver`、布局值、`Function.prototype.toString`

优先看 `wasm-sign-loader.md`：

1. JS 里明确出现 `WebAssembly.instantiate` / `instantiateStreaming`
2. 网络层能拿到 `.wasm` 文件
3. 关键问题集中在 `imports`、导出函数、内存写入或编码桥接

## 建议沉淀的内容

每完成一个站点或一个稳定类型，建议保留：

1. 站点或类型关键词
2. 反爬类型判断
3. 最终采用的路径
4. 必补环境项
5. 明确不必补的项
6. 关键踩坑记录
7. 一组最小可验证事实

## 最小可验证事实示例

建议记录成这种风格：

1. `navigator.webdriver` 必须显式为 `false`
2. `window.ActiveXObject` 必须显式存在且值为 `undefined`
3. `document.createElement('div')` 需要返回可继续 `getElementsByTagName('i')` 的对象
4. `document.cookie` 必须可写且最终可读
5. `document.hasFocus()` 在该站点会被读取
6. `navigator.plugins.length` 在该站点参与检测

## 复用的正确方式

正确复用：

1. 复用结论
2. 复用补丁顺序
3. 复用样本结构
4. 复用踩坑记录

不正确复用：

1. 直接把旧 cookie、旧 token、旧 sign 写进新代码
2. 看到旧方案用了浏览器，就把浏览器当最终依赖
3. 不重新验证当前版本是否改了入口和关键字段
