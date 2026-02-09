#!/bin/bash
# Wrapper script that runs the canvas scraper with a timeout.
# Sends SIGTERM after 15 minutes, then SIGKILL after 30 more seconds.
# This ensures the process doesn't block WSL shutdown indefinitely.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure logs directory exists
mkdir -p logs

timeout --signal=TERM --kill-after=30 900 \
    ./venv/bin/python src/main.py "$@" >> logs/scraper.log 2>&1
