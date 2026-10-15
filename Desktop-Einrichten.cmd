@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0" || exit /b 1
echo Richtet Python und Electron nur in diesem Projekt ein. Kein Autostart, keine Firewallfreigabe.
set "DESKTOP_ARCH=x64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "DESKTOP_ARCH=arm64"
set "PIPELINE_PYTHON=%CD%\.runtime\python\win32-%DESKTOP_ARCH%\Scripts\python.exe"
if not exist "%PIPELINE_PYTHON%" set "PIPELINE_PYTHON=%CD%\.runtime\pipeline-python\Scripts\python.exe"
if not exist "%PIPELINE_PYTHON%" set "PIPELINE_PYTHON=%CD%\.runtime\windows-python\Scripts\python.exe"
if not exist "%PIPELINE_PYTHON%" set "PIPELINE_PYTHON=python"
"%PIPELINE_PYTHON%" "%CD%\setup_pipeline.py" --desktop
if errorlevel 1 goto failed
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js LTS ab 22.12 fehlt. Download: https://nodejs.org/en/download
  goto failed
)
"%PIPELINE_PYTHON%" "%CD%\desktop\install_runtime.py"
if errorlevel 1 goto failed
echo Fertig. Starte jetzt Start-Desktop.cmd. Modelle und Konten stehen unter Einstellungen.
pause
exit /b 0
:failed
echo Einrichtung fehlgeschlagen. Beachte die Meldung oben.
pause
exit /b 1
