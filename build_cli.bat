@echo off
setlocal

if exist "dist\\biospeak.exe" del "dist\\biospeak.exe"
pyinstaller --clean --noconfirm --onefile --name biospeak --paths . --add-data "examples;examples" cli\biospeak_cli.py
if errorlevel 1 (
    echo CLI build failed.
    exit /b 1
)

echo CLI build complete.
