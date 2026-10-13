@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0" || exit /b 1

set "PIPELINE_PYTHON=%CD%\.runtime\windows-python\Scripts\python.exe"
if not exist "%PIPELINE_PYTHON%" (
  set "PIPELINE_PYTHON=%CD%\.runtime\pipeline-python\Scripts\python.exe"
)
if not exist "%PIPELINE_PYTHON%" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python fehlt. Installiere Python 3.12 von https://www.python.org/downloads/ und starte erneut.
    pause
    exit /b 1
  )
  set "PIPELINE_PYTHON=python"
)

"%PIPELINE_PYTHON%" "%CD%\setup_pipeline.py"
if errorlevel 1 (
  echo Die Pipeline konnte nicht gestartet werden. Die Fehlermeldung steht oben.
  pause
  exit /b 1
)
