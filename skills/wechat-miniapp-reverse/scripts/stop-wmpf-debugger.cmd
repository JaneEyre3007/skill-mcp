@echo off
setlocal EnableExtensions

set "FOUND="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":62000 .*LISTENING"') do (
  if not "%%P"=="%FOUND%" (
    set "FOUND=%%P"
    taskkill /PID %%P /F > nul 2> nul
    if errorlevel 1 (
      echo Failed to stop WMPFDebugger pid %%P
    ) else (
      echo Stopped WMPFDebugger pid %%P
    )
  )
)

if "%FOUND%"=="" echo WMPFDebugger is not listening on 62000.
exit /b 0
