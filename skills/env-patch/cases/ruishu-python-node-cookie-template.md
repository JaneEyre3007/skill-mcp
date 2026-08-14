# 瑞数 Python-Node Cookie 模板

## Summary

当目标是瑞数 challenge 动态 cookie，且最终业务调度层在 Python 时，优先使用“三层模板”：Python 调度层负责抓首跳和回放接口，Node 运行层负责执行动态 JS，`browser_env.js` 负责最小补环境。这个路径特别适合“首页返回 `412`，但响应体里仍然内联了 `$_ts` 脚本并继续下发外链 JS”的站点。该模式的核心价值不是把 Python 和 JS 混在一起跑，而是把“抓页面、提资源、回放业务请求”和“补环境、执行动态脚本”分层，避免 `execjs.call()` 被 stdout 日志、诊断报告和非 JSON 输出污染。

## Keywords

1. `412`
2. `$_ts`
3. `subprocess`
4. `node_runtime_template.js`
5. `browser_env.js`
6. `main.py`
7. `__NODE_RESULT__`
8. `document.cookie`

## Anti-Bot Type

1. 瑞数 challenge / 动态 cookie

## Recommended Path

1. 最小环境复现
2. Python 调度 + Node 执行模板
3. 必要时再收缩代理或升级 vm

## Good Fit

下面这些情况优先走这个模板：

1. 首页首跳虽然不是 `200`，但响应体里还能继续提 challenge 脚本；实际命中过 `412` 和 `202`
2. 业务请求最终要由 Python `requests` / 其他后端 HTTP 客户端发送
3. 动态 JS 本身已经能在 Node 跑，只差补环境
4. 你需要保留 challenge HTML、内联脚本、外链脚本、Node stdout/stderr 作为复盘材料

## Not a Good Fit

下面这些情况不要默认走这个模板：

1. 用户只想定位 sign/token/header 的生成入口
2. 用户只想看内联脚本里哪一段是 `$_ts`，还不需要执行动态 JS
3. 用户只要一个纯 Python 的 HTML / script 提取脚手架，不涉及 `window/document` 补环境
4. 目标已经明显进入 jsdom / 深度宿主伪装阶段，最小环境不再是主矛盾

## Entry Clues

1. 首页虽然返回 `412` 或 `202`，但响应体仍有 challenge 脚本
2. 内联脚本通常包含 `$_ts` / `$_ts.cd` / `if(!$_ts)`
3. 第二个脚本常是外链 challenge JS
4. `meta[id][content][r='m']` 值得优先保留，某些站点会通过 `document.getElementById(meta_id)` 参与 challenge
5. `document.cookie` 是最终写入点
6. `document.createElement` / `getElementsByTagName` / `getElementById` 是常见首批依赖
7. 业务接口在 Python 里重放时，只要 cookie 正确，通常可以直接拿到 JSON 或让首页从 challenge 进入 `200`

## Required Environment Items

1. `window.$_ts` 预先存在
2. `document.cookie` 可写可读
3. `document.createElement`
4. `document.getElementsByTagName`
5. `document.getElementById`
6. `location.*`
7. `navigator.userAgent`
8. `localStorage` / `sessionStorage`
9. `meta` 节点和 `currentScript` 节点的最小返回值
10. 临时容器节点要能承接 `innerHTML / firstChild / removeChild` 这类最小 DOM 链

## First Fixes to Try

如果是首次起步，优先按下面顺序补，而不是一次性堆很多对象：

1. `window.$_ts`
2. `document.cookie`
3. `document.createElement`
4. `document.getElementsByTagName`
5. `document.getElementById`
6. `location.*`
7. `navigator.userAgent`
8. `localStorage` / `sessionStorage`
9. `meta` 节点和 `currentScript` 节点的最小返回值
10. `createElement('div')` 返回值的最小 DOM 容器链

## Explicit Undefined Items

1. `window.ActiveXObject`
2. `window.execScript`
3. `window.CollectGarbage`
4. `window.DOMParser`
5. `navigator.connection`（若仅为探测，可先保持 `undefined`）

补充判断：

1. `ActiveXObject` 不是永远都该补成 `undefined`
2. 如果诊断报告里已经出现 `new ActiveXObject(...)` 或构造调用，再升级成“最小可构造对象”

## Python Integration Notes

1. 不要在首页 `412` 后直接 `raise_for_status()`；先判断响应体里是否仍有 challenge 脚本
2. 提取内联脚本时，优先按 `$_ts` 特征选择，不要默认取第一个 `script`
3. 多个候选都命中 `$_ts` 时，优先选更长的一段，而不是只取第一条
4. 外链脚本 URL 优先用 `urljoin()` 处理，而不是手工字符串拼接
5. 对接 Node 时优先 `subprocess.run(['node', runtime.js])`，不要默认 `execjs.call()`
6. Node 输出建议使用 `__NODE_RESULT__` 前缀 + JSON，避免 stdout 日志污染结果提取
7. 推荐把首页 HTML、内联脚本、外链脚本、运行时 JS、Node stdout/stderr、最终接口响应统一落盘到按时间戳分目录的 `_debug_artifacts/<timestamp>/`
8. 如果首页里的 challenge `meta` 会参与后续逻辑，建议把 `meta id/content` 也一并落盘并注入运行时环境

## Key Pitfalls

1. 旧案例的极简环境不能直接平移到新的还原代码，容易改变控制流
2. 全量代理 `window` 可能导致 OOM、极慢或卡死
3. 某些字段即使真实值是 `undefined`，也要显式补成“存在但值为 `undefined`”
4. `execjs.call()` 容易被 `console.log` 和诊断报告破坏 JSON 结果
5. 首页 challenge 文档里可能先出现 IE 兼容脚本或短脚本片段，不能据此误判内联入口
6. `createElement('div')` 返回值如果不能承接 `innerHTML / firstChild / removeChild`，脚本可能在写 cookie 之前就中断
7. “已经能生成 cookie”不等于“已经跑通”；回放仍然返回 `400` / challenge 时，优先怀疑是假 cookie，而不是继续盲目堆全量宿主对象

## Minimal Verifiable Facts

1. `node main.js` 能输出动态 cookie
2. `python main.py` 能抓 `412` 或 `202` challenge 页面并继续提取脚本
3. `main.py` 调 Node 后能拿到结构化 cookie 结果
4. 将 cookie 回灌到 `requests.Session()` 后，业务接口可返回 JSON
5. 每次运行都能生成独立的 `_debug_artifacts/<timestamp>/` 复盘目录
6. 对某些站点，成功标准不是“有 cookie”，而是“首页从 challenge 进入 `200`”

## Validation

1. 运行 `python main.py`
2. 观察是否输出 `source_cookie -> [...]`
3. 观察后续业务接口是否返回 JSON，或首页是否从 challenge 进入 `200`
4. 观察是否输出 `debug_artifacts_dir -> ...`

## Notes

这类 case 的重点不是保存一次性的 cookie 值，而是沉淀：`412` 页面不要直接判死、内联脚本按 `$_ts` 选取、Python-Node 三层模板、Node 结构化输出、按批次落盘复盘材料、以及哪些宿主只需要最小补齐。对于瑞数这类目标，这个模板最值得复用的不是某个固定的 `browser_env.js` 内容，而是“首页继续提脚本 -> Node 产出结构化结果 -> Python 回灌 cookie -> 再发业务请求”这条稳定路径。
