# Cases

`cases/` 是给 `env-patch` 用的本地经验库。

它的作用不是存“可直接复制运行的代码”，而是存：

1. 某类站点或某个站点的技术指纹
2. 这类目标应该优先走哪条路径
3. 已经踩过哪些坑
4. 哪些环境项必须补，哪些不用补
5. 一组最小可验证事实

## 为什么需要 cases

补环境最容易浪费时间的地方，不是写代码，而是：

1. 已经做过类似站点，但下次又从零开始
2. 知道以前踩过坑，但记不清到底卡在哪
3. 不确定该走最小环境、vm、jsdom 还是 WASM
4. 同一类站点每次都重复验证相同的宿主对象

`cases/` 就是把这些经验固定下来，避免重复劳动。

## 它记录什么

每个 case 建议记录：

1. 关键词
2. 反爬类型
3. 推荐路径
4. 关键入口
5. 必补环境项
6. 明确不用补的项
7. 关键踩坑记录
8. 最小可验证事实

## 它不记录什么

不建议把这些东西当作 case 的核心内容：

1. 过期 cookie
2. 直接可复用的最终签名值
3. 一次性的抓包结果
4. 依赖浏览器临时跑出来的最终答案

这些可以作为样本放在项目目录里，但不适合当长期经验库。

## 怎么用

开始一个新目标时：

1. 先看当前工作区有没有旧目录
2. 再看 `references/case-index.md`
3. 再看 `cases/README.md` 和已有 case 文件
4. 命中相似目标时，优先复用“路径选择”和“踩坑记录”

## 命名建议

case 文件优先用“技术特征”命名，而不是直接用域名。

推荐风格：

1. `ruishu-challenge-cookie-min-env.md`
2. `byted-sdk-xhr-sign-vm.md`
3. `jsvmp-env-diff-jsdom.md`
4. `wasm-sign-loader.md`

这样同类站点更容易复用。

## 当前建议优先沉淀的 4 类

1. 瑞数 / challenge / cookie 生成
2. 字节系 / SDK 拦截器 / `a_bogus` 类
3. 深度环境绑定 / jsdom 分级补丁类
4. WASM 加载与环境补丁类

## 新增 case 的方式

1. 复制 `_template.md`
2. 按实际情况填写
3. 尽量写“稳定特征”和“稳定结论”
4. 少写一次性数据，多写可复验事实
5. 如果是刚跑通的新站点，先用 `_retrospective-template.md` 做一次 3-5 分钟复盘，再回填到正式 case

模板里的空白位不是要求每项都写满，而是提醒只回填“已经被证据证明”的信息；如果某栏当前没有稳定结论，留空比硬猜更好。

## 当前内置起步案例

1. `ruishu-challenge-cookie-min-env.md` — 瑞数 / challenge / 动态 cookie / 显式 `undefined` / 代理收缩
2. `ruishu-python-node-cookie-template.md` — 瑞数 / `412` challenge / Python 调度 / Node 执行 / 结构化 cookie 输出
3. `byted-sdk-sign-min-env.md` — 字节系 SDK / 请求拦截器 / 签名字段 / 最小环境优先
4. `jsdom-env-diff-tiered.md` — 从最小环境升级到 jsdom 时的分级补丁案例
5. `wasm-sign-loader.md` — `.wasm` 加密或签名场景的起步案例

## 当前案例索引

| case | 适用场景 | 首选路径 | 关键关注点 |
|------|---------|---------|-----------|
| `ruishu-challenge-cookie-min-env.md` | 瑞数 / `412` `202` `204` challenge / 外链 JS / 动态 cookie | 最小环境 → vm | 显式 `undefined`、challenge 到 cookie 的写入链、代理收缩 |
| `ruishu-python-node-cookie-template.md` | 瑞数 / `412` challenge / Python 调度业务请求 / Node 执行动态 JS | 最小环境 → Python-Node 模板 | `412` 不直接判失败、按 `$_ts` 选脚本、`subprocess(node)`、结构化输出 |
| `byted-sdk-sign-min-env.md` | 字节系 SDK / 请求拦截器 / 签名字段 / `a_bogus` | 最小环境 → vm | `location` / `navigator` / `XMLHttpRequest` / 签名格式 |
| `jsdom-env-diff-tiered.md` | 最小环境已基本补齐但结果仍降级，准备升级到 jsdom | jsdom | 致命级补丁优先、差异分级、何时停手 |
| `wasm-sign-loader.md` | `.wasm` 参与签名或加密，JS 主要负责桥接和喂参数 | WASM → 最小环境 | 先看 `imports` / `exports`，再补最小宿主 |

## 配套模板

1. `_template.md` — 正式 case 模板
2. `_retrospective-template.md` — 跑通后的快速复盘模板

## 案例沉淀建议

当你完成一个新目标时，优先沉淀下面这些信息，而不是直接堆整段代码：

1. 它属于哪类反爬
2. 最终走了哪条路径
3. 第一个真正卡点是什么
4. 最终必须补的最少环境项是什么
5. 哪些看起来常见但其实不用补
6. 最后怎么验证通过
