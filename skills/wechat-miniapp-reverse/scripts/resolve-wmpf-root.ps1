param(
  [Parameter(Mandatory = $true)]
  [string]$SkillDir
)

$ErrorActionPreference = 'SilentlyContinue'

function Test-WmpfRoot {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
  return (Test-Path -LiteralPath (Join-Path $Path 'package.json')) -and
    (Test-Path -LiteralPath (Join-Path $Path 'src\index.ts')) -and
    (Test-Path -LiteralPath (Join-Path $Path 'node_modules'))
}

$skillPath = (Resolve-Path -LiteralPath $SkillDir).Path
$configPath = Join-Path $skillPath 'local.config.json'
if (Test-Path -LiteralPath $configPath) {
  try {
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if (Test-WmpfRoot $config.wmpfDebuggerRoot) {
      Write-Output ((Resolve-Path -LiteralPath $config.wmpfDebuggerRoot).Path)
      exit 0
    }
  } catch {}
}

$cwd = (Get-Location).Path
if (Test-WmpfRoot $cwd) {
  Write-Output ((Resolve-Path -LiteralPath $cwd).Path)
  exit 0
}

$parent = Split-Path -Parent $cwd
if (Test-WmpfRoot $parent) {
  Write-Output ((Resolve-Path -LiteralPath $parent).Path)
  exit 0
}

$sibling = Join-Path $parent 'WMPFDebugger'
if (Test-WmpfRoot $sibling) {
  Write-Output ((Resolve-Path -LiteralPath $sibling).Path)
  exit 0
}

exit 3
