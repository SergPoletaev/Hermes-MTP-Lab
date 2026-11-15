@echo off
setlocal DisableDelayedExpansion
title Hermes MTP Lab - installer v0.3.3
chcp 65001 >nul
echo ==============================================
echo  HERMES MTP LAB v0.3.3 - PLUGIN INSTALLER
echo ==============================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Hermes-MTP-Lab.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
    echo Installation failed, exit code: %RC%
) else (
    echo Installer finished. Check the result above.
)
echo.
pause
exit /b %RC%
