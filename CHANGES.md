# CHANGES.md —— 修改清单

原则：**原件零修改**。本仓库内的文件只有两类：原样复制，或是在本仓库内新建/改造的可移植副本。
原电脑上的任何源文件、DSH preset、MCP、浏览器均未被改动。

## 一、相对原件有改动（可移植改造）

### 1. `dsh-preset\web-reverse\agent.cordis.yml`（模板化，原件未动）
以原机 `C:\Users\zh158\.dsh\.agent-presets\web-reverse\agent.cordis.yml` 为底，仅替换 8 处绝对路径为占位符，其余逐字相同：

| 位置 | 原件 | 模板 |
|---|---|---|
| camoufox 行 args | `E:\最终mcp和skill\2026_6_1_webpack - 1\camoufox工具迁移\scripts\launch-camoufox-reverse-mcp.bat` | `{{REVERSE_ROOT}}\mcps\camoufox-toolchain\scripts\launch-camoufox-reverse-mcp.bat` |
| camoufox 行 env.PYTHON_EXE | `E:\python\python.exe` | `{{PYTHON_EXE}}` |
| cloakbrowser 行 args | `E:\BaiduNetdiskDownload\...\CloakBrowser\cloakbrowser-reverse-mcp\launch.bat` | `{{REVERSE_ROOT}}\mcps\CloakBrowser\cloakbrowser-reverse-mcp\launch.bat` |
| cloakbrowser 行 env.PYTHON_EXE | `E:\python\python.exe` | `{{PYTHON_EXE}}` |
| jsrev 行 cwd | `E:\最终mcp和skill\最终skills与mcps\mcps\js-reverse-mcp-local-cloak` | `{{REVERSE_ROOT}}\mcps\js-reverse-mcp` |
| frx 行 cwd | `E:\最终mcp和skill\最终skills与mcps\mcps\firefox-reverse-ai-mcp` | `{{REVERSE_ROOT}}\mcps\frx-director-mcp` |
| miniapp 行 command / cwd | `E:\python\python.exe` / `E:\...\miniapp-reverse-mcp` | `{{PYTHON_EXE}}` / `{{REVERSE_ROOT}}\mcps\miniapp-reverse-mcp` |
| skill-filesystem customSkillDirs | `C:\Users\zh158\.config\opencode\skills\reverse-engineering` | `{{REVERSE_ROOT}}\skills` |

新电脑上由 `restore.ps1` 替换占位符后写入 `~\.dsh\.agent-presets\web-reverse\`。

### 2. 恢复时由 restore.ps1 改写的 2 个 skill 配置（仓库内保持原件）
- `skills\ai-browser-reverse\config\browser-root.json`：`rootPath`/`firefoxExe` 改为新机 Firefox 路径（默认 `D:\develop_software\FireFox Reverse\firefox\firefox.exe`）。
- `skills\wechat-miniapp-reverse\local.config.json`：`wmpfDebuggerRoot` 改为新机 WMPFDebugger 路径。

## 二、新建文件（原件中不存在）
- `README.md`、`CHANGES.md`、`.gitignore`
- `restore\restore.ps1`（一键恢复脚本，英文消息避免编码问题）
- `docs\requirements-python.txt`（pip 精确版本：camoufox[geoip]==0.5.4、cdp-use==1.4.5、esprima==4.0.1、mcp==1.29.0、playwright==1.60.0、setuptools==76.0.0）
- `dsh-preset\web-reverse\preset.yml`（与原机同名文件内容一致）
- `mcps\camoufox-toolchain\runtime\README.md`、`runtimes\README.md`（占位说明）

## 二补、副本内被改动的 .gitignore（原件未动，仅备份副本）
- `mcps\js-reverse-mcp\.gitignore`：注释掉 `build/` 一行 —— 原项目忽略 build 产物，但备份需要把
  预编译入口 `build\src\index.js`（含打包进 build 的 DevTools 前端，5.3MB）一起入库，新机免 `npm run build`。
- `mcps\frx-director-mcp\.gitignore`：注释掉 `dist/` 一行 —— 同理，把预编译入口 `dist\index.js` 入库。

## 三、原样复制（未做任何改动）
| 备份位置 | 来源 |
|---|---|
| `skills\`（13 个） | `C:\Users\zh158\.config\opencode\skills\reverse-engineering\`（robocopy 全量） |
| `skills\web-reverse-intel\` | `C:\Users\zh158\.dsh\skills\web-reverse-intel\` |
| `mcps\js-reverse-mcp\` | `E:\最终mcp和skill\最终skills与mcps\mcps\js-reverse-mcp-local-cloak\`（排除 node_modules、两个 profile 目录） |
| `mcps\frx-director-mcp\` | `E:\最终mcp和skill\最终skills与mcps\mcps\firefox-reverse-ai-mcp\`（排除 node_modules、.git、.frx-director-mcp 状态目录） |
| `mcps\miniapp-reverse-mcp\` | `E:\最终mcp和skill\最终skills与mcps\mcps\miniapp-reverse-mcp\`（新版 25 工具，排除 __pycache__） |
| `mcps\camoufox-toolchain\scripts\`、`config-templates\` | `E:\最终mcp和skill\2026_6_1_webpack - 1\camoufox工具迁移\` 同名目录 |
| `mcps\camoufox-toolchain\packages\camoufox-reverse-mcp-main\` | 迁移包 `packages\camoufox-reverse-mcp-main\`（排除 camoufox-data 缓存、.pytest_cache） |
| `mcps\CloakBrowser\cloakbrowser-reverse-mcp\` | `E:\BaiduNetdiskDownload\...\CloakBrowser\cloakbrowser-reverse-mcp\` |
| `release-assets\camoufox-reverse-135.0.1-beta.24.zip` | 迁移包 `runtime\Camoufox-reverse\camoufox-reverse.zip`（原样复制，503 条目） |
| `release-assets\CloakBrowser-146.0.7680.177.zip` | CloakBrowser 目录打包（排除 `profiles\` 216MB 运行时档案、`.cloakbrowser-reverse\`），zip 根 = CloakBrowser 根，保证解压后 `chrome.exe` 与 `cloakbrowser-reverse-mcp\` 的绑定布局不变 |
| `release-assets\FireFox-Reverse.zip` | `D:\develop_software\FireFox Reverse\` 整体打包（zip 内含顶层 `FireFox Reverse\` 目录） |

布局说明：camoufox-toolchain 与 CloakBrowser 保持了**与原机相同的相对目录结构**，因此两个 launch.bat
（`%~dp0` 相对定位）和 cloakbrowser 的 `parents[3]` 找 chrome.exe 规则在新机上**无需修改即可运行**。

## 四、有意排除的内容（可再生，不备份）
| 内容 | 大小 | 理由 |
|---|---|---|
| 4 份浏览器 Cache（camoufox-data\Cache ×4） | ~3.5 GB | 运行时缓存，首启自动重建 |
| js-reverse `chrome-reverse-profile`(591MB) + `cloak-reverse-profile`(31MB) | ~622 MB | 运行时浏览器档案，首启自动重建 |
| CloakBrowser `profiles\` | 216 MB | 同上 |
| 官方 Camoufox 浏览器本体（runtime\Camoufox） | ~850 MB | pip 包从 GitHub Releases 自动下载（repos.yml：daijro/camoufox 等） |
| 各 MCP 的 node_modules | ~250 MB | `npm install` 重建（package-lock 已备份） |
| .git / .frx-director-mcp / __pycache__ | ~2 MB | 仓库元数据/运行时状态 |

## 五、需要你知晓的两点
1. 本仓库所在盘（E:）根目录存在一个 git 仓库（`E:\.git`）。备份文件夹本身会 `git init` 成独立仓库，
   **请勿在 `E:\` 根目录执行 `git add -A`**，否则可能把备份内容误加进那个大仓库。
2. 3 个大 zip 走 GitHub Release（普通 git 有 100MB 单文件限制），上传后 `release-assets\` 目录随备份文件夹一起删除。
