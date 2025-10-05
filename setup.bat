@echo off
setlocal

python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment.
    exit /b 1
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install biopython scikit-bio pysam ete3 numpy pandas matplotlib plotly seaborn scikit-learn tensorflow pyqt6 pyinstaller
if errorlevel 1 (
    echo Dependency installation failed.
    exit /b 1
)

call build_cli.bat
if errorlevel 1 exit /b 1
call build_gui.bat
if errorlevel 1 exit /b 1

echo BioLang setup complete. Executables are in the dist folder.
