@echo off
rem --- Ensure Python 3.12 is installed (Windows) ---
setlocal enabledelayedexpansion
set REQUIRED_MAJOR=3
set REQUIRED_MINOR=12
rem Change this installer version if you want a different 3.12.x build
set PYTHON_INSTALLER=python-3.12.0-amd64.exe
set PYTHON_URL=https://www.python.org/ftp/python/3.12.0/%PYTHON_INSTALLER%

echo Checking for Python installation...
set PY_VER=
for /f "delims=" %%v in ('python -c "import sys; print(f\"%s.%s\" % (sys.version_info[0], sys.version_info[1]))" 2^>^&1') do set PY_VER=%%v

if defined PY_VER (
    echo Found Python %PY_VER%
    for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
        set MAJ=%%a
        set MIN=%%b
    )
    if defined MAJ if defined MIN (
        if "%MAJ%"=="%REQUIRED_MAJOR%" if "%MIN%"=="%REQUIRED_MINOR%" (
            echo Required Python %REQUIRED_MAJOR%.%REQUIRED_MINOR% is already installed.
            goto :python_ok
        )
    )
) else (
    echo Python not found on PATH.
)

:install_python
echo Installing Python %REQUIRED_MAJOR%.%REQUIRED_MINOR%...
echo Downloading %PYTHON_URL%
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%~dp0%PYTHON_INSTALLER%' -UseBasicParsing -ErrorAction Stop } catch { exit 1 }"
if not exist "%~dp0%PYTHON_INSTALLER%" (
    echo Failed to download Python installer.
    echo You can manually install Python 3.12 from https://www.python.org/downloads/release/python-3120/
    goto :python_ok
)

echo Running Python installer (silent)...
"%~dp0%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
if %ERRORLEVEL% NEQ 0 (
    echo Python installer returned error %ERRORLEVEL%.
    echo Try running the installer manually: %~dp0%PYTHON_INSTALLER%
) else (
    echo Python installed.
)
del "%~dp0%PYTHON_INSTALLER%" >nul 2>&1

:python_ok
setlocal & endlocal

setlocal

echo ======================================
echo Setting up Python environment...
echo ======================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python and make sure it's in your PATH.
    pause
    exit /b
)

:: Create virtual environment
python -m venv .venv

if not exist .venv (
    echo Failed to create virtual environment.
    pause
    exit /b
)

echo Virtual environment created successfully.

:: Activate virtual environment
call .venv\Scripts\activate

echo ======================================
echo Installing FFmpeg...
echo ======================================

:: Create a temporary directory for ffmpeg
set "FFMPEG_DIR=%cd%\ffmpeg"
if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"

:: Download FFmpeg using PowerShell
powershell -Command "Invoke-WebRequest https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip -OutFile ffmpeg.zip"

:: Unzip FFmpeg
powershell -Command "Expand-Archive ffmpeg.zip -DestinationPath '%FFMPEG_DIR%'"

:: Find ffmpeg.exe and add to PATH for this session
for /r "%FFMPEG_DIR%" %%f in (ffmpeg.exe) do set "FFMPEG_BIN=%%~dpf"
setx PATH "%PATH%;%FFMPEG_BIN%"
echo FFmpeg installed and added to PATH.

:: Clean up
del ffmpeg.zip >nul 2>&1

echo ======================================
echo Installing Python requirements...
echo ======================================

.venv\Scripts\activate.bat

pip install --upgrade pip
pip install -r requirements.txt

echo ======================================
echo Setup complete!
echo To activate the environment later, run:
echo     call venv\Scripts\activate
echo ======================================
echo *
echo A discord bot, not intended to be used in other servers.
echo Under GNU General Public License Version 3.0, 29 June 2007.
echo © 2025 Warat Thongsuwan (TonpalmUnmain)


pause
