@echo off
setlocal enabledelayedexpansion

set "UI_DIR=%~dp0"
set "PYTHON_DIR=%~dp0"
set "OUTPUT_TS=%~dp0i18n/ChineseAiAssistant_zh-Hans.ts"

:: find all ui files in current directory only (non-recursive)
set "UI_FILES="
for %%i in ("%UI_DIR%*.ui") do (
    set "UI_FILES=!UI_FILES! "%%i""
)

:: find all python files in current directory only (non-recursive)
set "PYTHON_FILES="
for %%i in ("%PYTHON_DIR%*.py") do (
    set "PYTHON_FILES=!PYTHON_FILES! "%%i""
)

echo UI Files: %UI_FILES%
echo Python Files: !PYTHON_FILES!

:: exec pylupdate5
pylupdate5 %PYTHON_FILES% %UI_FILES% -ts "%OUTPUT_TS%"

endlocal