@echo off
setlocal

set "ROOT=%~dp0.."
set "MCP_ROOT=%ROOT%\packages\camoufox-reverse-mcp-main"
set "CAMOUFOX_ROOT=%ROOT%\runtime\Camoufox"

if defined PYTHON_EXE (
  set "PYTHON_BIN=%PYTHON_EXE%"
) else (
  set "PYTHON_BIN=python"
)

if not exist "%MCP_ROOT%\src\camoufox_reverse_mcp\__main__.py" (
  echo [ERROR] MCP source not found: %MCP_ROOT%
  exit /b 1
)

if not exist "%CAMOUFOX_ROOT%\camoufox.exe" (
  echo [ERROR] Camoufox executable not found: %CAMOUFOX_ROOT%\camoufox.exe
  exit /b 1
)

set "PYTHONPATH=%MCP_ROOT%\src;%PYTHONPATH%"
set "CAMOUFOX_EXECUTABLE_PATH=%CAMOUFOX_ROOT%\camoufox.exe"

if exist "%CAMOUFOX_ROOT%\camoufox-data\" (
  set "CAMOUFOX_DATA_DIR=%CAMOUFOX_ROOT%\camoufox-data"
) else (
  set "CAMOUFOX_DATA_DIR=%CAMOUFOX_ROOT%"
)

%PYTHON_BIN% -c "import mcp, camoufox, playwright, esprima" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python dependencies are missing.
  echo [HINT] Run: "%ROOT%\scripts\install-camoufox-reverse-mcp-deps.bat"
  exit /b 1
)

%PYTHON_BIN% -m camoufox_reverse_mcp %*
