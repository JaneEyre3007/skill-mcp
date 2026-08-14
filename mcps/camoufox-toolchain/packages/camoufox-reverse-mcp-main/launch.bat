@echo off
set CAMOUFOX_EXECUTABLE_PATH=%~dp0..\camoufox.exe
set CAMOUFOX_DATA_DIR=%~dp0..\camoufox-data
python -m camoufox_reverse_mcp
