@echo off
title MediTrack ERP - Medical Shop Management System
echo ============================================================
echo   MediTrack ERP - Offline-First Medical Shop Management
echo ============================================================

REM 1. If standalone binary exists in dist\MediTrack, prioritize it for instant launch
if exist "dist\MediTrack\MediTrack.exe" (
    echo [INFO] Standalone desktop build found. Launching MediTrack.exe...
    start "" "dist\MediTrack\MediTrack.exe"
    exit /b 0
)

REM 2. Discover best available Python executable
set PYTHON_CMD=
where python >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
)
if "%PYTHON_CMD%"=="" (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py -3
    )
)
if "%PYTHON_CMD%"=="" (
    if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
        set PYTHON_CMD="%LOCALAPPDATA%\Python\bin\python.exe"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3 was not detected on your system!
    echo Please install Python 3.10+ from https://www.python.org/
    echo or build the standalone executable with build_desktop.py
    pause
    exit /b 1
)

REM 3. Seed baseline pharmacy database if not present
if not exist "medical_shop.db" (
    echo [INFO] First-time setup detected. Seeding baseline pharmacy database...
    %PYTHON_CMD% seed_data.py
)

REM 4. Launch desktop application
echo [INFO] Launching MediTrack with %PYTHON_CMD%...
%PYTHON_CMD% main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%.
    pause
)
