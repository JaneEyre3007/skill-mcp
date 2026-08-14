@echo off
set CLOAKBROWSER_REVERSE_ROOT=%~dp0
set PYTHONPATH=%~dp0src;%PYTHONPATH%
if defined PYTHON_EXE (
  set "PYTHON_BIN=%PYTHON_EXE%"
) else (
  set "PYTHON_BIN=python"
)
%PYTHON_BIN% -m cloakbrowser_reverse_mcp %*
