@echo off
setlocal DisableDelayedExpansion
title Hermes MTP Lab v0.3.3 - publish full repository
chcp 65001 >nul
echo.
echo Publishing complete Hermes MTP Lab v0.3.3 source to GitHub...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Publish-Hermes-MTP-Lab.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Publish failed with code %RC%.
pause
exit /b %RC%
