@echo off
setlocal

if exist "dist\\biolang.exe" del "dist\\biolang.exe"
pyinstaller --clean --noconfirm --onefile --name biolang --paths . --add-data "examples;examples" cli\biolang_cli.py
if errorlevel 1 (
    echo CLI build failed.
    exit /b 1
)

echo CLI build complete.
