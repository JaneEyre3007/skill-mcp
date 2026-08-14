param(
  [string]$OutputPath
)

$ErrorActionPreference = "Stop"

function Write-JsonResult($Object) {
  $Object | ConvertTo-Json -Depth 6 -Compress
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = Join-Path (Get-Location).Path "object"
}

try {
  $resolvedOutputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
} catch {
  Write-JsonResult @{ ok = $false; outputPath = $OutputPath; error = "Invalid output path: $($_.Exception.Message)" }
  exit 0
}

try {
  New-Item -ItemType Directory -Force -Path $resolvedOutputPath | Out-Null
  $cacheDir = Join-Path $resolvedOutputPath "js_reverse_cache"
  $samplesDir = Join-Path $resolvedOutputPath "samples"
  New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
  New-Item -ItemType Directory -Force -Path $samplesDir | Out-Null

  $manifestPath = Join-Path $resolvedOutputPath "ai-browser-reverse-output.json"
  $manifest = [ordered]@{
    outputPath = $resolvedOutputPath
    cacheDir = $cacheDir
    samplesDir = $samplesDir
    createdAt = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "AI Browser Reverse code landing directory"
  }
  $manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $manifestPath

  Write-JsonResult @{
    ok = $true
    outputPath = $resolvedOutputPath
    cacheDir = $cacheDir
    samplesDir = $samplesDir
    manifestPath = $manifestPath
  }
} catch {
  Write-JsonResult @{ ok = $false; outputPath = $resolvedOutputPath; error = "Failed to prepare output directory: $($_.Exception.Message)" }
  exit 0
}
