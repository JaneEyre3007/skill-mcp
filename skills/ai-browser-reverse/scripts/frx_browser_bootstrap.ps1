param(
  [string]$RootPath,
  [string]$ConnectionDir,
  [int]$Port = 2828
)

$ErrorActionPreference = "Stop"

function Write-JsonResult($Object) {
  $Object | ConvertTo-Json -Depth 6 -Compress
}

function Test-PortOpen([string]$HostName, [int]$PortNumber) {
  try {
    $client = [System.Net.Sockets.TcpClient]::new()
    $async = $client.BeginConnect($HostName, $PortNumber, $null, $null)
    $ok = $async.AsyncWaitHandle.WaitOne(500)
    if ($ok) {
      $client.EndConnect($async)
    }
    $client.Close()
    return $ok
  } catch {
    return $false
  }
}

function Read-RootConfig([string]$ConfigPath, [string]$SourceName) {
  if (-not $ConfigPath -or -not (Test-Path $ConfigPath)) {
    return $null
  }

  try {
    $saved = Get-Content -Raw -Path $ConfigPath | ConvertFrom-Json
    if ($saved.rootPath) {
      return [pscustomobject]@{
        ok = $true
        rootPath = [string]$saved.rootPath
        source = $SourceName
        configPath = $ConfigPath
      }
    }

    return [pscustomobject]@{
      ok = $false
      source = $SourceName
      configPath = $ConfigPath
      error = "Saved config does not contain rootPath."
    }
  } catch {
    return [pscustomobject]@{
      ok = $false
      source = $SourceName
      configPath = $ConfigPath
      error = "Saved config is invalid: $($_.Exception.Message)"
    }
  }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillRoot = Split-Path -Parent $scriptDir
$configDir = Join-Path $skillRoot "config"
$skillConfig = Join-Path $configDir "browser-root.json"
$rootSource = "none"
$browserConfigRead = $null

if ($RootPath) {
  $rootSource = "argument"
}

if (-not $RootPath -and $ConnectionDir) {
  try {
    $resolvedConnectionDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ConnectionDir)
    $connectionConfig = if ((Split-Path -Leaf $resolvedConnectionDir) -eq "config.json") { $resolvedConnectionDir } else { Join-Path $resolvedConnectionDir "config.json" }
    $loaded = Read-RootConfig $connectionConfig "browserConnection"
    if ($loaded -and -not $loaded.ok) {
      Write-JsonResult @{ ok = $false; needRootPath = $true; rootSource = $loaded.source; browserConfigRead = $loaded.configPath; skillConfig = $skillConfig; error = $loaded.error }
      exit 0
    }
    if ($loaded) {
      $RootPath = $loaded.rootPath
      $rootSource = $loaded.source
      $browserConfigRead = $loaded.configPath
    }
  } catch {
    Write-JsonResult @{ ok = $false; needRootPath = $true; connectionDir = $ConnectionDir; skillConfig = $skillConfig; error = "Could not read browser connection config: $($_.Exception.Message)" }
    exit 0
  }
}

if (-not $RootPath -and (Test-Path $skillConfig)) {
  $loaded = Read-RootConfig $skillConfig "skillIndex"
  if ($loaded -and -not $loaded.ok) {
    Write-JsonResult @{ ok = $false; needRootPath = $true; configExists = $true; rootSource = $loaded.source; skillConfig = $skillConfig; error = $loaded.error }
    exit 0
  }
  if ($loaded) {
    $RootPath = $loaded.rootPath
    $rootSource = $loaded.source
  }
}

if ($RootPath -and $rootSource -eq "skillIndex") {
  try {
    $indexRoot = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($RootPath)
    $candidateBrowserConfig = Join-Path (Join-Path (Join-Path $indexRoot "firefox-reverse-ai-mcp") "browser-connection") "config.json"
    $loaded = Read-RootConfig $candidateBrowserConfig "browserConnection"
    if ($loaded -and -not $loaded.ok) {
      Write-JsonResult @{ ok = $false; needRootPath = $true; rootSource = $loaded.source; browserConfigRead = $loaded.configPath; skillConfig = $skillConfig; error = $loaded.error }
      exit 0
    }
    if ($loaded) {
      $RootPath = $loaded.rootPath
      $rootSource = $loaded.source
      $browserConfigRead = $loaded.configPath
    }
  } catch {
    Write-JsonResult @{ ok = $false; needRootPath = $true; rootPath = $RootPath; rootSource = $rootSource; skillConfig = $skillConfig; error = "Could not locate browser connection config from skill index: $($_.Exception.Message)" }
    exit 0
  }
}

if (-not $RootPath) {
  Write-JsonResult @{ ok = $false; needRootPath = $true; configExists = $false; skillConfig = $skillConfig; message = "Firefox Reverse root path is not configured. Ask the user for the browser root path, then rerun this script with -RootPath to save it before startup." }
  exit 0
}

try {
  $resolvedRoot = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($RootPath)
} catch {
  Write-JsonResult @{ ok = $false; needRootPath = $true; rootPath = $RootPath; rootSource = $rootSource; browserConfigRead = $browserConfigRead; skillConfig = $skillConfig; error = "Could not normalize Firefox Reverse root path: $($_.Exception.Message)" }
  exit 0
}

$firefoxExe = Join-Path $resolvedRoot "firefox.exe"

if (-not (Test-Path $firefoxExe)) {
  Write-JsonResult @{ ok = $false; needRootPath = $true; rootPath = $resolvedRoot; rootSource = $rootSource; browserConfigRead = $browserConfigRead; skillConfig = $skillConfig; error = "firefox.exe was not found under the provided root path." }
  exit 0
}

New-Item -ItemType Directory -Force -Path $configDir | Out-Null

$now = (Get-Date).ToUniversalTime().ToString("o")
$config = [ordered]@{
  rootPath = $resolvedRoot
  firefoxExe = $firefoxExe
  marionettePort = $Port
  updatedAt = $now
}

$config | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $skillConfig
$browserMcpDir = Join-Path $resolvedRoot "firefox-reverse-ai-mcp"
$browserConfigDir = Join-Path $browserMcpDir "browser-connection"
$rootMarker = Join-Path $browserConfigDir "config.json"
New-Item -ItemType Directory -Force -Path $browserConfigDir | Out-Null
$config | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $rootMarker

$legacyRootMarker = Join-Path $resolvedRoot ".ai-browser-reverse.json"
if (Test-Path $legacyRootMarker) {
  Remove-Item -Force -Path $legacyRootMarker
}

$legacyConfig = Join-Path (Join-Path $resolvedRoot "ai-browser-reverse") "config.json"
if (Test-Path $legacyConfig) {
  Remove-Item -Force -Path $legacyConfig
}

if (Test-PortOpen "127.0.0.1" $Port) {
  Write-JsonResult @{
    ok = $true
    needRootPath = $false
    alreadyConnected = $true
    rootPath = $resolvedRoot
    rootSource = $rootSource
    firefoxExe = $firefoxExe
    marionettePort = $Port
    portOpen = $true
    configSaved = $true
    browserConfigRead = $browserConfigRead
    skillConfig = $skillConfig
    browserConfig = $rootMarker
  }
  exit 0
}

$started = $null
try {
  $started = Start-Process -FilePath $firefoxExe -ArgumentList "-marionette", "-remote-allow-system-access" -PassThru
} catch {
  Write-JsonResult @{ ok = $false; needRootPath = $false; rootPath = $resolvedRoot; rootSource = $rootSource; firefoxExe = $firefoxExe; browserConfigRead = $browserConfigRead; skillConfig = $skillConfig; error = "Failed to start firefox.exe: $($_.Exception.Message)" }
  exit 0
}

$portOpen = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 500
  if (Test-PortOpen "127.0.0.1" $Port) {
    $portOpen = $true
    break
  }
}

Write-JsonResult @{
  ok = $true
  needRootPath = $false
  rootPath = $resolvedRoot
  rootSource = $rootSource
  firefoxExe = $firefoxExe
  processId = $started.Id
  marionettePort = $Port
  portOpen = $portOpen
  configSaved = $true
  browserConfigRead = $browserConfigRead
  skillConfig = $skillConfig
  browserConfig = $rootMarker
}
