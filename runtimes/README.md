# runtimes 目录说明

- `WMPFDebugger\` —— 由 restore.ps1 自动 `git clone https://github.com/evi0s/WMPFDebugger` 到此处
  （也可以用 -WmpfRoot 指定别处）。启动：`npx ts-node src/index.ts`，CDP 端口 62000。
- FireFox Reverse —— 不在本目录：默认解压到 `D:\develop_software\FireFox Reverse\`（可用 -FirefoxRoot 修改）。
  启动时必须带 `-marionette -remote-allow-system-access -profile <PROFILE>`，监听 127.0.0.1:2828。
