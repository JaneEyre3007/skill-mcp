@echo off
setlocal

set "ROOT=%~dp0.."
set "MCP_ROOT=%ROOT%\packages\camoufox-reverse-mcp-main"

if defined PYTHON_EXE (
  set "PYTHON_BIN=%PYTHON_EXE%"
) else (
  set "PYTHON_BIN=python"
)

if not exist "%MCP_ROOT%\pyproject.toml" (
  echo [ERROR] pyproject.toml not found: %MCP_ROOT%\pyproject.toml
  exit /b 1
)

%PYTHON_BIN% --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python is not available. Install Python 3.10+ and add it to PATH,
  echo or set PYTHON_EXE to the full python.exe path before running this script.
  exit /b 1
)

%PYTHON_BIN% -m pip install -U pip
if errorlevel 1 exit /b 1

%PYTHON_BIN% -m pip install -e "%MCP_ROOT%"
if errorlevel 1 exit /b 1

echo [OK] camoufox-reverse-mcp dependencies installed.
