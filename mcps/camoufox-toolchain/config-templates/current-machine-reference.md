# 当前机器 MCP 参考记录

## Opencode

当前文件：

`C:\Users\poppies\.config\opencode\opencode.json`

当前 Camoufox MCP 配置项：

```json
"camoufox-reverse-mcp": {
  "type": "local",
  "command": [
    "cmd",
    "/c",
    "D:\\develop_software\\Camoufox\\camoufox-reverse-mcp-main\\launch.bat"
  ],
  "enabled": true
}
```

说明：

1. 这个配置绑定了旧的 `D:` 盘绝对路径。
2. 它默认假设当前 Python 环境里已经安装过 `camoufox_reverse_mcp`。
3. 本迁移包已经改成使用 `scripts\launch-camoufox-reverse-mcp.bat` 作为新的可移植入口。

## Trae

当前文件：

`C:\Users\poppies\AppData\Roaming\Trae CN\User\mcp.json`

当前状态：

1. 已存在 `Chrome DevTools MCP`
2. 已存在 `JS-Reverse-MCP`
3. 还没有 `camoufox-reverse-mcp` 配置项

## Python

当前用于导入 `camoufox_reverse_mcp` 的 Python：

`D:\develop_software\Miniconda3\python.exe`

这个路径是当前机器专用路径，不建议在迁移时直接硬编码。
