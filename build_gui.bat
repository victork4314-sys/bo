@echo off
setlocal

if exist "dist\\BioLangStudio.exe" del "dist\\BioLangStudio.exe"
pyinstaller --clean --noconfirm --windowed --name "BioLangStudio" --paths . --add-data "examples;examples" gui\biolang_studio.py
if errorlevel 1 (
    echo GUI build failed.
    exit /b 1
)

echo GUI build complete.
