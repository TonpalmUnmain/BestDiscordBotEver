#!/bin/bash
# Ubuntu/Linux setup script for BestDiscordBotEver

set -e  # Exit on error

echo "======================================"
echo "Setting up Python environment..."
echo "======================================"

# Check if Python 3.12 is installed
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ -z "$PYTHON_VERSION" ]; then
    echo "Python 3 not found. Please install Python 3.12 or later."
    echo "On Ubuntu/Debian, run: sudo apt-get install python3.12 python3.12-venv"
    exit 1
fi

echo "Found Python $PYTHON_VERSION"

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 12 ]); then
    echo "Warning: Python 3.12+ is recommended. Current version is $PYTHON_VERSION"
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Virtual environment created successfully."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source .venv/bin/activate

echo "======================================"
echo "Installing FFmpeg..."
echo "======================================"

# Check if FFmpeg is already installed
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is already installed."
else
    echo "Installing FFmpeg..."
    sudo apt-get update
    sudo apt-get install -y ffmpeg
    echo "FFmpeg installed successfully."
fi

echo "======================================"
echo "Installing Python requirements..."
echo "======================================"

pip install --upgrade pip
pip install -r requirements.txt

echo "======================================"
echo "Setup complete!"
echo "======================================"
echo "To activate the environment, run:"
echo "    source .venv/bin/activate"
echo "======================================"
echo ""
echo "A discord bot, not intended to be used in other servers."
echo "Under GNU General Public License Version 3.0, 29 June 2007."
echo "© 2025 Warat Thongsuwan (TonpalmUnmain)"
