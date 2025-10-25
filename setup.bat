@echo off
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
python -m venv venv

if not exist venv (
    echo Failed to create virtual environment.
    pause
    exit /b
)

echo Virtual environment created successfully.

:: Activate virtual environment
call venv\Scripts\activate

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

venv\Scripts\activate.bat

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
