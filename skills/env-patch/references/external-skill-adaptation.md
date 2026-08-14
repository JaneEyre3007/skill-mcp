# 外部 Skill 适配说明

这份文档记录从外部逆向 skill 中吸收了哪些内容，以及为什么不能原样搬进当前 `env-patch`。

## 结论

外部 skill 整体**不能原样复用**，原因是它围绕 `camoufox-reverse MCP` 组织工作流，而当前 `env-patch` 的工具条件不同。

但其中有 3 类内容非常值得吸收：

1. 反爬类型分档
2. 路径选择与降级梯度
3. 反模式与经验沉淀机制

## 不可直接吸收

以下内容是工具硬绑定，当前 skill 不直接使用：

1. `check_environment()`、`launch_browser()`、`navigate()` 这类专有 MCP API
2. `hook_function()`、`inject_hook_preset()`、`instrumentation()` 这类专有 Hook / 插桩接口
3. `compare_env()`、`analyze_cookie_sources()`、`verify_signer_offline()` 等专有能力
4. 以 Camoufox 作为默认分析中心的 Checklist 和阶段动作

原因：这些步骤写进当前 skill 后会变成“看起来很强，但实际不可执行”。

## 已吸收并改写

### 1. 反爬类型三分法

已改写进 `references/reverse-workflow.md`：

1. 签名型反爬
2. 行为型反爬
3. 纯混淆

用途：在补环境前先判断应该走哪条路径，而不是一上来就全量补。

### 2. 路径选择

已改写进 `SKILL.md` 的 Step 2.5：

1. 纯算法还原
2. 最小环境复现
3. vm 沙箱
4. jsdom 环境伪装
5. WASM 加载

### 3. 降级梯度

已改写进 `references/reverse-workflow.md`：

1. 重新检查已有证据和旧方案
2. 换日志粒度 / 缩小监控面
3. 点对点追踪方法或单对象补丁
4. 从最小环境升级到 jsdom / vm / WASM 对应路径
5. 最后才承认当前路径受阻，并输出卡点报告

### 4. 环境差异分级

已吸收为当前 skill 的 `Step 3.2`：

1. 致命级
2. 高危级
3. 中危级

### 5. 反模式清单

已抽取并去除 Camoufox 绑定，整理为 `references/reverse-antipatterns.md`。

### 6. 经验库思路

原项目的 `cases/README.md` 很有价值，它强调：

1. 先查已有样例、已有目录、已有旧代码
2. 命中已有经验时不要从零重做
3. 站点案例更适合作为“踩坑记录”，而不是直接复用代码

这部分已改写进当前 `SKILL.md` 的“启动检查”，并扩展为 `references/case-index.md`。

## 有价值但仅作参考

以下内容保留为思路，不直接移植代码：

1. `references/jsdom-env-patches.md` 中关于 jsdom 差异分级的结构
2. `references/troubleshooting.md` 中的请求失败排查顺序
3. `references/common-pitfalls.md` 中关于避免浏览器兜底、避免硬编码 cookie、避免跳过经验库的约束
4. `cases/README.md` 中的案例索引与关键词匹配思路

## 当前 skill 的立场

当前 `env-patch` 现在吸收的是：

1. 方法论
2. 判定框架
3. 失败约束
4. 经验沉淀意识

没有吸收的是：

1. Camoufox 专有 API
2. 依赖专有 MCP 的操作细节
3. 浏览器作为最终运行依赖的思路

一句话总结：

**吸收了脑子，没有照搬手脚。**
