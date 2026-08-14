param(
  [Parameter(Mandatory = $true)]
  [string]$Root
)

$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path

$tsNode = Join-Path $rootPath 'node_modules\.bin\ts-node.cmd'
if (Test-Path -LiteralPath $tsNode) {
  $runner = 'call "node_modules\.bin\ts-node.cmd"'
} else {
  $runner = 'npx --no-install ts-node'
}

$escapedRoot = $rootPath.Replace("'", "''")
$escapedRunner = $runner.Replace("'", "''")
$hiddenScript = "Set-Location -LiteralPath '$escapedRoot'; & `$env:ComSpec /d /c '$escapedRunner src/index.ts >> wmpf-debugger.log 2>&1'"
Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-Command', $hiddenScript) -WorkingDirectory $rootPath -WindowStyle Hidden
