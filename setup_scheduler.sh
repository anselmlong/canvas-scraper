#!/bin/bash
# Setup script for Linux/Mac cron scheduler

# Get absolute path to project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
MAIN_SCRIPT="$PROJECT_DIR/src/main.py"
LOG_FILE="$PROJECT_DIR/logs/scraper.log"

# Check if virtual environment exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Error: Python virtual environment not found at $PROJECT_DIR/venv"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Cron entry (daily at noon)
CRON_ENTRY="0 12 * * * cd $PROJECT_DIR && $PYTHON_BIN $MAIN_SCRIPT >> $LOG_FILE 2>&1"

echo "Canvas Scraper - Scheduler Setup"
echo "=================================="
echo ""
echo "This will add a cron job to run the scraper daily at 12:00 PM (noon)"
echo ""
echo "Cron entry:"
echo "$CRON_ENTRY"
echo ""

read -p "Add this cron job? [y/n]: " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # Check if entry already exists
    if crontab -l 2>/dev/null | grep -q "$MAIN_SCRIPT"; then
        echo "Cron job already exists. Removing old entry..."
        crontab -l 2>/dev/null | grep -v "$MAIN_SCRIPT" | crontab -
    fi
    
    # Add new entry
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    
    echo ""
    echo "✓ Cron job added successfully!"
    echo ""
    echo "The scraper will run daily at 12:00 PM"
    echo ""
    echo "Useful commands:"
    echo "  View crontab: crontab -l"
    echo "  Edit crontab: crontab -e"
    echo "  View logs: tail -f $LOG_FILE"
else
    echo ""
    echo "Cron job not added."
    echo "You can manually add it later with: crontab -e"
fi
