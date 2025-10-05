@echo off
setlocal

if exist "dist\\Bio Speak Studio.exe" del "dist\\Bio Speak Studio.exe"
pyinstaller --clean --noconfirm --windowed --name "Bio Speak Studio" --paths . --add-data "examples;examples" gui\biospeak_studio.py
if errorlevel 1 (
    echo GUI build failed.
    exit /b 1
)

echo GUI build complete.
