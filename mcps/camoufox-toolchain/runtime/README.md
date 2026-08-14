# 本目录会在新电脑恢复时被以下内容填充（不进 git，由 restore.ps1 或手动放置）

- `Camoufox\` —— 官方 Camoufox 浏览器（restore.ps1 用 `python -m camoufox fetch` 自动下载后放到这里，
  必须保证 `Camoufox\camoufox.exe` 存在；`launch-camoufox-reverse-mcp.bat` 依赖这个相对布局）
- `Camoufox-reverse\` —— 定制版 Camoufox-reverse（从 GitHub Release 的
  `camoufox-reverse-135.0.1-beta.24.zip` 解压到这里，zip 内容即该目录内容）
