@echo off
setlocal
cd /d "%~dp0"

echo Creating icon...
python make_icon.py
if errorlevel 1 goto :fail

echo Building gxfr_utilA.exe...
python -m PyInstaller --noconfirm --windowed --onefile --name gxfr_utilA --icon gxfr_utilA.ico --add-data "gxfr_utilA.ico;." xfr_utilA.py
if errorlevel 1 goto :fail
copy /Y dist\gxfr_utilA.exe gxfr_utilA.exe >nul

echo Building gxfr_utilA_Setup.exe...
python -m PyInstaller --noconfirm --windowed --onefile --name gxfr_utilA_Setup --icon gxfr_utilA.ico --add-data "gxfr_utilA.exe;." --add-data "gxfr_utilA.ico;." install_gxfr_utilA.py
if errorlevel 1 goto :fail
copy /Y dist\gxfr_utilA_Setup.exe gxfr_utilA_Setup.exe >nul

echo.
echo Done:
echo   gxfr_utilA.exe
echo   gxfr_utilA_Setup.exe
if not "%~1"=="/nopause" pause
exit /b 0

:fail
echo Build failed.
if not "%~1"=="/nopause" pause
exit /b 1
