#!/bin/bash
# Wrapper script that runs the canvas scraper with a timeout.
# Sends SIGTERM after 15 minutes, then SIGKILL after 30 more seconds.
# This ensures the process doesn't block WSL shutdown indefinitely.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure logs directory exists
mkdir -p logs

# Detect Python interpreter (support both venv and .venv)
if [ -x "./venv/bin/python" ]; then
    PYTHON="./venv/bin/python"
elif [ -x "./.venv/bin/python" ]; then
    PYTHON="./.venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
else
    echo "Error: No Python interpreter found (checked ./venv/bin/python, ./.venv/bin/python, python3)" >> logs/scraper.log
    exit 1
fi

# Log start of run with timestamp
echo "=== Canvas Scraper started at $(date) ===" >> logs/scraper.log

timeout --signal=TERM --kill-after=30 900 \
    $PYTHON src/main.py "$@" >> logs/scraper.log 2>&1
