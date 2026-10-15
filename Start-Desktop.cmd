@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0" || exit /b 1
set "DESKTOP_ARCH=x64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "DESKTOP_ARCH=arm64"
set "PIPELINE_PYTHONW=%CD%\.runtime\python\win32-%DESKTOP_ARCH%\Scripts\pythonw.exe"
if not exist "%PIPELINE_PYTHONW%" set "PIPELINE_PYTHONW=%CD%\.runtime\pipeline-python\Scripts\pythonw.exe"
if not exist "%PIPELINE_PYTHONW%" set "PIPELINE_PYTHONW=%CD%\.runtime\windows-python\Scripts\pythonw.exe"
if not exist "%PIPELINE_PYTHONW%" (
  echo Bitte zuerst Desktop-Einrichten.cmd starten.
  pause
  exit /b 1
)
start "" "%PIPELINE_PYTHONW%" "%CD%\desktop\launcher.py"
