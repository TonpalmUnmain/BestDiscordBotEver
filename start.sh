#!/bin/bash
# Ubuntu/Linux startup script for BestDiscordBotEver

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run the bot
python "$SCRIPT_DIR/main.py"
