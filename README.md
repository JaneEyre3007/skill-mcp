# web-reverse-backup —— 网站逆向全套便携备份

一套**自包含、可移植**的网站逆向环境备份：6 个逆向 MCP 服务器、14 个逆向 skills、3 套反检测浏览器、
1 个小程序调试器，以及对应的 DeepSeek Harness（DSH）「网站逆向」agent preset 和一键恢复脚本。

**新电脑上：clone 本仓库 + 下载 3 个 Release 压缩包 + 跑一次 `restore\restore.ps1` = 直接可用。**
原电脑上的任何东西都**没有被改动**（备份全程只读原文件）。

---

## 目录结构

```
web-reverse-backup/
├─ README.md                 ← 本文件（恢复手册）
├─ CHANGES.md                ← 修改清单（哪些文件相对原件有改动、改了什么）
├─ .gitignore
├─ restore/
│  └─ restore.ps1            ← 一键恢复脚本（装依赖/解压/生成 preset/修补配置）
├─ docs/
│  ├─ requirements-python.txt← Python 依赖（精确版本锚定）
│  └─ ...
├─ dsh-preset/web-reverse/   ← DSH agent preset【模板，含 {{REVERSE_ROOT}} 占位符】
├─ skills/                   ← 14 个逆向 skills（13 个 opencode 逆向类 + web-reverse-intel）
├─ mcps/
│  ├─ camoufox-toolchain/    ← Camoufox MCP 启动链（scripts + packages，布局与原件一致）
│  ├─ CloakBrowser/          ← cloakbrowser-reverse-mcp 源码（浏览器本体从 Release zip 解压到这里）
│  ├─ js-reverse-mcp/        ← 源码 + 编译产物（node_modules 由 npm install 重建）
│  ├─ frx-director-mcp/      ← 源码 + dist（node_modules 由 npm install 重建）
│  └─ miniapp-reverse-mcp/   ← 新版（25 工具）完整源码
├─ runtimes/                 ← WMPFDebugger clone 到这里（restore 自动）
└─ release-assets/           ← 【不进 git】3 个大压缩包，上传到 GitHub Release 后本目录删除
```

## 版本锚点

| 组件 | 版本 |
|---|---|
| Python | 3.13（原机 `E:\python\python.exe`），要求 ≥3.10 |
| Node | 22 LTS（原机 v22.23.1） |
| 官方 Camoufox 浏览器 | 135.0.1 beta.24（`camoufox==0.5.4` 自动从 GitHub Releases 下载） |
| Camoufox-reverse 定制版 | 135.0.1 beta.24（Release zip，无公开下载源） |
| CloakBrowser | 146.0.7680.177（Release zip，无公开下载源） |
| FireFox Reverse | 定制版（Release zip，无公开下载源，Marionette 端口 2828） |
| WMPFDebugger | 公开仓库 `evi0s/WMPFDebugger`（clone），CDP 端口 62000 |
| Python MCP 依赖 | camoufox[geoip]==0.5.4 / cdp-use==1.4.5 / esprima==4.0.1 / mcp==1.29.0 / playwright==1.60.0 |
| DSH | `npm i -g @deepseek-ai/dsh`（原机 0.1.0-rc.6） |

## 新电脑从零恢复（完整步骤）

> 全程只有两处需要人点一下：装软件时的 **UAC 确认框**、`git clone` 时的 **GitHub 登录窗口**。
> 其余全部由脚本自动完成——也可以直接让一个带 Shell 能力的 AI（DSH / Claude Code / Codex / opencode）
> 读本 README 替你执行下面所有命令。

### 第 1 步：克隆仓库（唯一一次登录）
```powershell
git clone https://github.com/JaneEyre3007/skill-mcp.git web-reverse
cd web-reverse
```
私有仓库首次 clone 会弹出 GitHub 登录窗口，浏览器授权一次即可（凭据会被记住，后面自动复用）。

### 第 2 步：一条命令装到底
```powershell
powershell -ExecutionPolicy Bypass -File restore\restore.ps1 -InstallBase
```
`-InstallBase` 会先自动补齐基础软件：检测并用 **winget 装 Git / Python 3.13 / Node LTS**（缺啥装啥，
弹 UAC 点"是"），再用 **npm 装 DSH**。随后自动完成：定位 Python → `pip install` 依赖（精确版本）→
`python -m camoufox fetch` 拉官方 Camoufox 并放入 `mcps\camoufox-toolchain\runtime\Camoufox\` →
**复用刚才的 git 登录凭据走 API 自动下载 3 个 Release 包并解压到位** → clone WMPFDebugger 并 `npm install`
→ 给 js-reverse / frx 补 `npm install` → 修补两个 skill 的路径配置 → 生成 DSH preset 到
`%USERPROFILE%\.dsh\.agent-presets\web-reverse\`（模板占位符自动替换成真实路径）。

> **备选方式**（不装基础软件 / 不自动下载大文件时用）：
> - 跳过基础软件：直接跑 `restore.ps1`（不加 `-InstallBase`），前提是已装好 Git/Python/Node/DSH。
> - 手动下载 3 个 zip：浏览器登录 GitHub 打开 <https://github.com/JaneEyre3007/skill-mcp/releases/tag/v1.0.0>，
>   把 camoufox-reverse-135.0.1-beta.24.zip / CloakBrowser-146.0.7680.177.zip / FireFox-Reverse.zip
>   放进 `release-assets\`，脚本会优先用本地文件。
> - 显式 token：`restore.ps1 -GhToken "<你的token>"`（classic PAT 勾 `repo`，或 fine-grained Contents=Read）。
> - 其它可选参数见脚本头部注释（`-PythonExe`、`-FirefoxRoot`、`-WmpfRoot`、`-DshHome`、`-Skip*` 系列）。

### 第 3 步：启动两个"常驻服务"
- **FireFox Reverse**（`mcp__frx__*` 依赖）：
  ```powershell
  & "D:\develop_software\FireFox Reverse\firefox\firefox.exe" -marionette -remote-allow-system-access -profile "<PROFILE路径>"
  ```
  监听 `127.0.0.1:2828`。profile 可先用任意空目录。
- **WMPFDebugger**（`mcp__miniapp__*` 依赖）：
  ```powershell
  cd runtimes\WMPFDebugger
  npx ts-node src/index.ts
  ```
  监听端口 `62000`，配合微信开发者工具/WMPF 使用。

其余按需自动：js-reverse / cloaked 首次启动时自动下载 chromium 和创建浏览器 profile；
`npx chrome-devtools-mcp@latest` 首次运行自动拉包。

### 第 4 步：验证
新建 DSH 会话选择「网站逆向」preset，让它执行：
> 列出全部 mcp__* 工具数量；加载 web-reverse-intel 与 camoufox-js-reverse skill 各说一句用途；调用 mcp__devtools 的一个只读工具。

预期：6 组 MCP 工具齐全（jsrev 90 / cloakbrowser 69 / camoufox 35 / miniapp 25 / frx 11 / devtools 官方），
14 个 skills 可见。frx 提示 2828 不可达 = 没开 Firefox Reverse，正常。

## 路径映射（模板占位符 → 新机实际路径）

`restore.ps1` 只做两处替换，其余一切照模板生成：

| 占位符 | 新机上的实际值 |
|---|---|
| `{{REVERSE_ROOT}}` | 本仓库 clone 后的根目录 |
| `{{PYTHON_EXE}}` | 自动探测到的 python.exe 完整路径 |

涉及的文件：`dsh-preset\web-reverse\agent.cordis.yml`（8 处路径）、
`skills\ai-browser-reverse\config\browser-root.json`（Firefox 路径，默认 `D:\develop_software`）、
`skills\wechat-miniapp-reverse\local.config.json`（WMPFDebugger 根目录）。

## 原电脑本地环境不受影响

- 备份阶段只对原文件做**读取**；所有复制/改动都在备份目录里。
- 本地 DSH preset、skills、MCP、浏览器全部保持原样、继续可用。
- 备份目录推送验证完成后整体删除，不占用原机空间。

## 常见问题

- **frx 工具在但调用失败**：Firefox Reverse 没开或没带 `-marionette -remote-allow-system-access` 参数。
- **miniapp 工具在但连不上**：WMPFDebugger 没启动（端口 62000），或微信开发者工具未打开小程序调试。
- **camoufox 启动报缺浏览器**：确认 `mcps\camoufox-toolchain\runtime\Camoufox\camoufox.exe` 与
  `runtime\Camoufox-reverse\camoufox.exe` 存在（restore 第 2 步负责放好）。
- **浏览器缓存缺失**：正常。原机上的 4 份 browser Cache（共约 3.5 GB）是运行时缓存，有意不备份，
  首次启动自动重建。
- **改仓库路径后要重生成 preset**：重跑 restore.ps1（它会覆盖 `~\.dsh\.agent-presets\web-reverse\`）。
