@echo off
title GabAI: Mental Health Monitoring Platform
cd /d "%~dp0"

REM Instant check if MariaDB is running (avoids slow network socket scanning)
tasklist /fi "imagename eq mysqld.exe" 2>nul | findstr /i "mysqld.exe" >nul
if %errorlevel% neq 0 (
    start "" /b "C:\xampp\mysql\bin\mysqld.exe" --bind-address=127.0.0.1 --port=3307
)

REM Immediately open GabAI in default web browser
start "" "http://localhost:8000/"

REM Launch Django server instantly (skip auto-reloader sub-process and duplicate system checks)
python manage.py runserver 0.0.0.0:8000 --noreload --skip-checks
pause
