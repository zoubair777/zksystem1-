@echo off
rem ZK system - build ONE file: "ZK system.exe" (onefile) into Desktop\ZK system
rem Data lives next to it in "ZK system\ZK_data" (database, backups, logs) and is never touched here.
rem To move the system to another computer: close it, copy the whole "ZK system" folder.
setlocal
cd /d "%~dp0"

tasklist /FI "IMAGENAME eq ZK system.exe" | find /I "ZK system.exe" >nul
if not errorlevel 1 (
    echo [!] ZK system is running. Close the program first, then run this again.
    pause
    exit /b 1
)

set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=py"
set "VENV=%LOCALAPPDATA%\ZG_ERP_build\venv"
set "OUT=%LOCALAPPDATA%\ZG_ERP_build\out"
set "TARGET=%USERPROFILE%\Desktop\ZK system"

if not exist "%VENV%\Scripts\python.exe" (
    echo Creating build environment...
    "%PY%" -m venv "%VENV%" || goto :fail
)
"%VENV%\Scripts\python.exe" -m pip install -q -r requirements.txt -r requirements-desktop.txt pyinstaller || goto :fail

echo Building...
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "ZK system" ^
    --icon "%CD%\static\zk.ico" ^
    --add-data "%CD%\templates;templates" --add-data "%CD%\static;static" ^
    --distpath "%OUT%\dist" --workpath "%OUT%\work" --specpath "%OUT%" "%CD%\desktop_launcher.py" || goto :fail

if not exist "%TARGET%" mkdir "%TARGET%"
copy /Y "%OUT%\dist\ZK system.exe" "%TARGET%\ZK system.exe" >nul || goto :fail

echo.
echo Done: %TARGET%\ZK system.exe
pause
exit /b 0

:fail
echo.
echo [!] Build failed. No data was changed.
pause
exit /b 1
