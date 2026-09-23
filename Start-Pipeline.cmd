@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0" || exit /b 1

set "PIPELINE_PYTHON=%CD%\.runtime\windows-python\Scripts\python.exe"
if not exist "%PIPELINE_PYTHON%" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python fehlt. Bitte die Python-Laufzeit laut README.md einrichten.
    pause
    exit /b 1
  )
  set "PIPELINE_PYTHON=python"
)

"%PIPELINE_PYTHON%" "%CD%\start_pipeline.py"
if errorlevel 1 (
  echo Die Pipeline konnte nicht gestartet werden. Die Fehlermeldung steht oben.
  pause
  exit /b 1
)
