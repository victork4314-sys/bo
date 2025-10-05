@echo off
setlocal enabledelayedexpansion

if "%PYODIDE_VERSION%"=="" (
  set "PYODIDE_VERSION=0.24.1"
)
set "DIST=dist"
set "PYODIDE_ZIP=pyodide-%PYODIDE_VERSION%.zip"
set "PYODIDE_URL=https://github.com/pyodide/pyodide/releases/download/%PYODIDE_VERSION%/%PYODIDE_ZIP%"

if exist "%DIST%" rd /s /q "%DIST%"
mkdir "%DIST%"

python -m compileall core >nul

python - <<PY
import json
import sys
from pathlib import Path

sys.path.append(str(Path('core').resolve()))
from biospeak_core.filemap import generate_file_map

output = Path('dist/file-map.json')
output.write_text(json.dumps(generate_file_map(Path('.')), indent=2), encoding='utf-8')
PY

xcopy web "%DIST%" /E /I /Y >nul
xcopy core "%DIST%\core" /E /I /Y >nul

if not exist "%PYODIDE_ZIP%" (
  powershell -Command "Invoke-WebRequest -UseBasicParsing -Uri '%PYODIDE_URL%' -OutFile '%PYODIDE_ZIP%'"
)
if exist "dist\pyodide_tmp" rd /s /q "dist\pyodide_tmp"
powershell -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('%PYODIDE_ZIP%', 'dist\\pyodide_tmp')"
if not exist "dist\pyodide" mkdir "dist\pyodide"
xcopy "dist\pyodide_tmp\pyodide-%PYODIDE_VERSION%" "dist\pyodide" /E /I /Y >nul
rd /s /q "dist\pyodide_tmp"

echo.
echo Build complete — web version operational
