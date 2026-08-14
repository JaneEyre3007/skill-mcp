# ============================================================================
# web-reverse-backup restore script
# Turns a fresh clone of this repository into a fully working web-reverse
# setup: Python/Node deps, browsers, WMPFDebugger, and the DSH agent preset.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File restore\restore.ps1
#
# Options (all optional):
#   -RepoRoot <dir>      repo root (default: parent of this script)
#   -PythonExe <path>    python 3.10+ exe (default: auto-detect)
#   -DshHome <dir>       DSH home (default: %USERPROFILE%\.dsh)
#   -FirefoxRoot <dir>   FireFox Reverse extraction root (default: D:\develop_software)
#   -WmpfRoot <dir>      WMPFDebugger clone location (default: <RepoRoot>\runtimes\WMPFDebugger)
#   -ReleaseBaseUrl <url> base URL of GitHub release assets, e.g.
#                         https://github.com/<OWNER>/<REPO>/releases/download/<TAG>
#                        (default: use local release-assets\ folder when present)
#   -SkipNpm / -SkipPip / -SkipFetch / -SkipZips / -SkipClone / -SkipPreset
# ============================================================================

param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$PythonExe = '',
    [string]$DshHome = (Join-Path $env:USERPROFILE '.dsh'),
    [string]$FirefoxRoot = 'D:\develop_software',
    [string]$WmpfRoot = '',
    [string]$ReleaseBaseUrl = '',
    [switch]$SkipNpm, [switch]$SkipPip, [switch]$SkipFetch,
    [switch]$SkipZips, [switch]$SkipClone, [switch]$SkipPreset
)

$ErrorActionPreference = 'Stop'

function Step($name) { Write-Host "`n== $name ==" -ForegroundColor Cyan }
function OK($msg) { Write-Host "   OK: $msg" -ForegroundColor Green }
function Warn($msg) { Write-Warning $msg }

function Extract-Zip([string]$zip, [string]$dest) {
    New-Item -ItemType Directory -Force $dest | Out-Null
    $tar = Get-Command tar.exe -ErrorAction SilentlyContinue
    if ($tar) {
        & $tar.Source -xf $zip -C $dest
        if ($LASTEXITCODE -eq 0) { return }
        Warn "tar extraction failed, falling back to Expand-Archive"
    }
    Expand-Archive -Path $zip -DestinationPath $dest -Force
}

function Get-Zip([string]$name) {
    if ($ReleaseBaseUrl) {
        $out = Join-Path $env:TEMP $name
        Invoke-WebRequest -Uri "$ReleaseBaseUrl/$name" -OutFile $out
        return $out
    }
    $local = Join-Path $RepoRoot "release-assets\$name"
    if (Test-Path $local) { return $local }
    return $null
}

# ── 1. Python ────────────────────────────────────────────────────────────────
Step "Locate Python (>= 3.10)"
if (-not $PythonExe) {
    $c = @()
    foreach ($v in '3.13','3.12','3.11','3.10','3') {
        try { $r = (py -$v -c "import sys;print(sys.executable)" 2>$null | Select-Object -Last 1).Trim(); if ($r) { $c += $r } } catch {}
    }
    try { $p = (Get-Command python -ErrorAction SilentlyContinue).Source; if ($p) { $c += $p } } catch {}
    $c = $c | Where-Object { $_ } | Select-Object -Unique
    if (-not $c) { throw "No Python found. Install Python 3.13+ (tick 'Add python to PATH'), then re-run." }
    $PythonExe = $c[0]
}
$ver = (& $PythonExe -c "import sys;print('%d.%d' % sys.version_info[:2])" | Select-Object -Last 1).Trim()
if ([version]$ver -lt [version]'3.10') { throw "Python $ver is too old (need >= 3.10): $PythonExe" }
OK "$PythonExe  (Python $ver)"

if (-not $SkipPip) {
    Step "Install Python deps (pinned versions)"
    & $PythonExe -m pip install -r (Join-Path $RepoRoot 'docs\requirements-python.txt')
    OK "pip deps installed"
}

if (-not $SkipFetch) {
    Step "Fetch official Camoufox browser"
    & $PythonExe -m camoufox fetch
    $target = Join-Path $RepoRoot 'mcps\camoufox-toolchain\runtime\Camoufox'
    New-Item -ItemType Directory -Force $target | Out-Null
    $found = $null
    $roots = @(
        (Join-Path $env:LOCALAPPDATA 'camoufox'),
        (Join-Path $env:USERPROFILE '.camoufox'),
        (Join-Path $env:LOCALAPPDATA 'Camoufox')
    )
    foreach ($r in $roots) {
        if (Test-Path $r) {
            $found = Get-ChildItem $r -Recurse -Filter camoufox.exe -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { break }
        }
    }
    if (-not $found) {
        $found = Get-ChildItem $env:LOCALAPPDATA -Recurse -Filter camoufox.exe -Depth 4 -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match 'camoufox' } | Select-Object -First 1
    }
    if ($found) {
        robocopy (Split-Path $found.FullName) $target /E /NFL /NDL /NJH /NJS /NP | Out-Null
        OK "official Camoufox placed at $target"
    } else {
        Warn "camoufox.exe not located automatically. Manually copy an official Camoufox browser into:"
        Warn "  $target"
        Warn "(camoufox.exe must sit directly in that folder)"
    }
}

# ── 2. Release zips (browsers) ───────────────────────────────────────────────
if (-not $SkipZips) {
    Step "Extract release zips"
    $names = @{
        'camoufox-reverse-135.0.1-beta.24.zip' = 'mcps\camoufox-toolchain\runtime\Camoufox-reverse'
        'CloakBrowser-146.0.7680.177.zip'      = 'mcps\CloakBrowser'
        'FireFox-Reverse.zip'                  = $FirefoxRoot
    }
    foreach ($n in $names.Keys) {
        $z = Get-Zip $n
        if ($z) {
            Extract-Zip $z (Join-Path $RepoRoot $names[$n])
            OK "$n extracted"
        } else {
            Warn "zip not found: $n (supply -ReleaseBaseUrl, or place it in release-assets\)"
        }
    }
}

# ── 3. WMPFDebugger ──────────────────────────────────────────────────────────
if (-not $SkipClone) {
    Step "Clone WMPFDebugger"
    if (-not $WmpfRoot) { $WmpfRoot = Join-Path $RepoRoot 'runtimes\WMPFDebugger' }
    if (-not (Test-Path (Join-Path $WmpfRoot 'package.json'))) {
        git clone https://github.com/evi0s/WMPFDebugger.git $WmpfRoot
    }
    if (-not $SkipNpm) {
        Push-Location $WmpfRoot
        try { npm install } finally { Pop-Location }
    }
    OK "WMPFDebugger -> $WmpfRoot (run with: npx ts-node src/index.ts)"
}

# ── 4. Node MCP deps ─────────────────────────────────────────────────────────
if (-not $SkipNpm) {
    Step "npm install for Node MCPs"
    foreach ($d in 'mcps\js-reverse-mcp','mcps\frx-director-mcp') {
        $p = Join-Path $RepoRoot $d
        if (-not (Test-Path (Join-Path $p 'node_modules'))) {
            Push-Location $p
            try { npm install } finally { Pop-Location }
        }
    }
    OK "node deps installed"
}

# ── 5. Patch skill config files (machine-specific paths) ─────────────────────
Step "Patch skill config files"
$firefoxExe = Join-Path $FirefoxRoot 'FireFox Reverse\firefox\firefox.exe'
$aib = Join-Path $RepoRoot 'skills\ai-browser-reverse\config\browser-root.json'
if (Test-Path $aib) {
    $j = Get-Content $aib -Raw | ConvertFrom-Json
    $j.rootPath = (Split-Path $firefoxExe -Parent)
    $j.firefoxExe = $firefoxExe
    $j.marionettePort = 2828
    $j | ConvertTo-Json -Depth 3 | Set-Content -Path $aib -Encoding UTF8
    OK "browser-root.json -> $firefoxExe"
}
$wmc = Join-Path $RepoRoot 'skills\wechat-miniapp-reverse\local.config.json'
if (Test-Path $wmc) {
    $j = Get-Content $wmc -Raw | ConvertFrom-Json
    $j.wmpfDebuggerRoot = $WmpfRoot
    $j | ConvertTo-Json -Depth 3 | Set-Content -Path $wmc -Encoding UTF8
    OK "local.config.json -> $WmpfRoot"
}

# ── 6. Generate DSH preset ───────────────────────────────────────────────────
if (-not $SkipPreset) {
    Step "Generate DSH agent preset"
    $tpl = Join-Path $RepoRoot 'dsh-preset\web-reverse\agent.cordis.yml'
    $body = Get-Content $tpl -Raw
    $body = $body.Replace('{{REVERSE_ROOT}}', $RepoRoot).Replace('{{PYTHON_EXE}}', $PythonExe)
    $presetDir = Join-Path $DshHome '.agent-presets\web-reverse'
    New-Item -ItemType Directory -Force $presetDir | Out-Null
    Set-Content -Path (Join-Path $presetDir 'agent.cordis.yml') -Value $body -Encoding UTF8
    Copy-Item (Join-Path $RepoRoot 'dsh-preset\web-reverse\preset.yml') (Join-Path $presetDir 'preset.yml') -Force
    OK "preset -> $presetDir"
}

# ── 7. Final report ──────────────────────────────────────────────────────────
Step "Restore complete - remaining manual steps"
Write-Host @"

  [1] Start Firefox Reverse with Marionette (needed by mcp__frx__*):
        "$firefoxExe" -marionette -remote-allow-system-access -profile "<profile dir>"
      It listens on 127.0.0.1:2828.

  [2] Start WMPFDebugger (needed by mcp__miniapp__*):
        cd "$WmpfRoot"  then  npx ts-node src/index.ts
      It listens on port 62000.

  [3] Open DeepSeek Harness, create a new session and pick the
      "网站逆向" preset. Ask the agent to list its mcp__* tools.

  [4] First launch of js-reverse / cloaked browsers downloads their
      runtime profiles and any missing chromium automatically.

  Full details: see README.md
"@
