@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0" || exit /b 1

set "PIPELINE_PYTHON=%CD%\.runtime\windows-python\Scripts\python.exe"
if not exist "%PIPELINE_PYTHON%" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python fehlt. Die Pipeline konnte nicht gezielt gestoppt werden.
    exit /b 1
  )
  set "PIPELINE_PYTHON=python"
)

"%PIPELINE_PYTHON%" "%CD%\stop_pipeline.py" %*
exit /b %errorlevel%
