@echo off
setlocal enabledelayedexpansion

set ROOT=%~dp0
pushd "%ROOT%"

python -m compileall biospeak_core cli gui || goto :error
python cli\biospeak_cli.py verify || goto :error

call build_web.bat || goto :error

set BUILD_DIR=build\windows
set PAYLOAD=%BUILD_DIR%\payload

if exist "%BUILD_DIR%" rd /s /q "%BUILD_DIR%"
if not exist "dist" mkdir "dist"
mkdir "%PAYLOAD%"
mkdir "%PAYLOAD%\browser"
mkdir "%PAYLOAD%\desktop"
mkdir "%PAYLOAD%\terminal"
mkdir "%PAYLOAD%\launcher"
mkdir "%PAYLOAD%\biospeak_core"

pyinstaller --noconfirm --clean --onefile cli\biospeak_cli.py --name biospeak --distpath "%BUILD_DIR%\pyi" --workpath "%BUILD_DIR%\build" || goto :error
pyinstaller --noconfirm --clean --onefile gui\biospeak_studio.py --name BioSpeak --windowed --distpath "%BUILD_DIR%\pyi" --workpath "%BUILD_DIR%\build" --add-data "biospeak_core;biospeak_core" --add-data "web;web" || goto :error
pyinstaller --noconfirm --clean installer\welcome_launcher.py --name BioSpeakWelcome --windowed --distpath "%BUILD_DIR%\pyi" --workpath "%BUILD_DIR%\build" || goto :error

copy "%BUILD_DIR%\pyi\biospeak.exe" "%PAYLOAD%\terminal\biospeak.exe" >nul || goto :error
copy "%BUILD_DIR%\pyi\BioSpeak.exe" "%PAYLOAD%\desktop\BioSpeak.exe" >nul || goto :error
copy "%BUILD_DIR%\pyi\BioSpeakWelcome.exe" "%PAYLOAD%\launcher\BioSpeakWelcome.exe" >nul || goto :error

xcopy dist "%PAYLOAD%\browser" /E /I /Y >nul || goto :error
xcopy biospeak_core "%PAYLOAD%\biospeak_core" /E /I /Y >nul || goto :error
copy "%BUILD_DIR%\pyi\BioSpeak.exe" "dist\BioSpeak.exe" >nul || goto :error
copy "%BUILD_DIR%\pyi\biospeak.exe" "dist\biospeak.exe" >nul || goto :error
xcopy examples "%PAYLOAD%\examples" /E /I /Y >nul || goto :error

copy README.md "%PAYLOAD%" >nul

makensis /DOUTPUT_DIR="dist" /DPAYLOAD_DIR="%PAYLOAD%" installer\windows_installer.nsi || goto :error

echo Build complete -- Windows installer written to dist\BioSpeakInstaller.exe
popd
exit /b 0

:error
echo Installer build failed.
popd
exit /b 1
