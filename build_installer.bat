@echo off
setlocal enabledelayedexpansion

set ROOT=%~dp0
pushd "%ROOT%"

python -m compileall core cli gui || goto :error
python cli\biospeak_cli.py verify || goto :error

call build_web.bat || goto :error

set BUILD_DIR=build\windows
set PAYLOAD=%BUILD_DIR%\payload

if exist "%BUILD_DIR%" rd /s /q "%BUILD_DIR%"
mkdir "%PAYLOAD%"
mkdir "%PAYLOAD%\browser"
mkdir "%PAYLOAD%\desktop"
mkdir "%PAYLOAD%\terminal"
mkdir "%PAYLOAD%\launcher"

pyinstaller --noconfirm --clean --onefile cli\biospeak_cli.py --name biospeak --distpath "%BUILD_DIR%\pyi" --workpath "%BUILD_DIR%\build" || goto :error
pyinstaller --noconfirm --clean gui\biospeak_studio.py --name BioSpeakStudio --windowed --distpath "%BUILD_DIR%\pyi" --workpath "%BUILD_DIR%\build" --add-data "core;core" --add-data "web;web" || goto :error
pyinstaller --noconfirm --clean installer\welcome_launcher.py --name BioSpeakWelcome --windowed --distpath "%BUILD_DIR%\pyi" --workpath "%BUILD_DIR%\build" || goto :error

copy "%BUILD_DIR%\pyi\biospeak.exe" "%PAYLOAD%\terminal\biospeak.exe" >nul || goto :error
xcopy "%BUILD_DIR%\pyi\BioSpeakStudio" "%PAYLOAD%\desktop\BioSpeakStudio" /E /I /Y >nul || goto :error
copy "%BUILD_DIR%\pyi\BioSpeakWelcome.exe" "%PAYLOAD%\launcher\BioSpeakWelcome.exe" >nul || goto :error

xcopy dist "%PAYLOAD%\browser" /E /I /Y >nul || goto :error
xcopy core "%PAYLOAD%\core" /E /I /Y >nul || goto :error
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
