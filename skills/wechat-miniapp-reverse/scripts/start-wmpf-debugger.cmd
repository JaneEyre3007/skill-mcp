@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "SKILL_DIR=%SCRIPT_DIR%.."
set "ROOT=%~1"

if not "%ROOT%"=="" goto validate_root

for /f "usebackq delims=" %%R in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%resolve-wmpf-root.ps1" -SkillDir "%SKILL_DIR%"`) do set "ROOT=%%R"

:validate_root

if "%ROOT%"=="" (
  echo WMPFDebugger root not found. Ask the user for WMPFDebugger root path.
  exit /b 3
)

if not exist "%ROOT%\package.json" (
  echo Missing package.json: %ROOT%
  exit /b 2
)

if not exist "%ROOT%\src\index.ts" (
  echo Missing src\index.ts: %ROOT%
  exit /b 2
)

if not exist "%ROOT%\node_modules\" (
  echo Missing node_modules: %ROOT%
  exit /b 2
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$skill=(Resolve-Path -LiteralPath '%SKILL_DIR%').Path; $root=(Resolve-Path -LiteralPath '%ROOT%').Path; @{ wmpfDebuggerRoot = $root } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $skill 'local.config.json') -Encoding UTF8" > nul 2> nul

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":62000 .*LISTENING"') do (
  echo WMPFDebugger already listening on 62000, pid %%P
  exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-wmpf-debugger.ps1" -Root "%ROOT%" || exit /b 1

echo WMPFDebugger spawn requested; check "%ROOT%\wmpf-debugger.log".
exit /b 0
