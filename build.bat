@echo off
chcp 65001 > nul
setlocal

:: GG Archive Build Script (Windows)

set APP_NAME=GG_Archive
set MAIN_SCRIPT=main.py
set ICON_PATH=resources\icons\gg_icon.ico

echo === GG Archive Build Start ===

:: Clean previous build
echo Cleaning previous build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

:: Check PyInstaller installation
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Run build
echo Building...
pyinstaller --onefile --windowed --name %APP_NAME% ^
    --add-data "resources;resources" ^
    --add-data "alembic;alembic" ^
    --add-data "alembic.ini;." ^
    --add-data "licenses;licenses" ^
    --icon %ICON_PATH% ^
    --collect-all PySide6 ^
    --collect-all watchdog ^
    --hidden-import watchdog.observers.read_directory_changes ^
    --hidden-import watchdog.observers.winapi ^
    --hidden-import watchdog.observers.polling ^
    --exclude-module tests ^
    --exclude-module pytest ^
    --exclude-module _pytest ^
    --exclude-module unittest ^
    --exclude-module test ^
    %MAIN_SCRIPT%

echo.
echo === Build Complete! ===
echo Executable location: dist\%APP_NAME%.exe
echo.
echo dist\ folder contents:
echo   - %APP_NAME%.exe  (executable)

endlocal
:: CI 환경에서는 pause 하지 않음
if "%CI%"=="" pause
