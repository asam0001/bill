@echo off
title Create MediTrack Desktop Shortcut
echo Creating desktop shortcut for MediTrack...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"
echo.
pause
