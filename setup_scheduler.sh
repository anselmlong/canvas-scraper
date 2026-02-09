#!/bin/bash
# Setup script for Mac (launchd) and Linux (cron) scheduler
# Automatically detects platform and uses the appropriate method

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get absolute path to project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
MAIN_SCRIPT="$PROJECT_DIR/src/main.py"
LOG_FILE="$PROJECT_DIR/logs/scraper.log"

# Launchd plist for Mac
PLIST_NAME="com.canvas-scraper.sync"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Parse arguments
UNINSTALL=false
RUN_NOW=false
TRIGGER="login"  # login, startup, or daily

while [[ $# -gt 0 ]]; do
    case $1 in
        --uninstall|-u)
            UNINSTALL=true
            shift
            ;;
        --run-now|-r)
            RUN_NOW=true
            shift
            ;;
        --trigger|-t)
            TRIGGER="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --trigger, -t  Set trigger type: login (default), daily"
            echo "  --uninstall, -u  Remove the scheduled task"
            echo "  --run-now, -r    Run the scraper immediately"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Detect platform
detect_platform() {
    case "$(uname -s)" in
        Darwin)
            echo "mac"
            ;;
        Linux)
            # Check if running in WSL
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

PLATFORM=$(detect_platform)

# Check if virtual environment exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo -e "${RED}Error: Python virtual environment not found at $PROJECT_DIR/venv${NC}"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# ============================================================================
# macOS: Use launchd
# ============================================================================
setup_mac() {
    echo -e "${CYAN}Canvas Scraper - macOS Scheduler Setup${NC}"
    echo "========================================"
    echo ""

    if $UNINSTALL; then
        if [ -f "$PLIST_PATH" ]; then
            launchctl unload "$PLIST_PATH" 2>/dev/null || true
            rm -f "$PLIST_PATH"
            echo -e "${GREEN}Launchd agent removed successfully.${NC}"
        else
            echo -e "${YELLOW}No launchd agent found.${NC}"
        fi
        return
    fi

    if $RUN_NOW; then
        if [ -f "$PLIST_PATH" ]; then
            launchctl start "$PLIST_NAME"
            echo -e "${GREEN}Task started. Check logs for output.${NC}"
        else
            echo -e "${RED}No launchd agent found. Run setup first.${NC}"
        fi
        return
    fi

    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$HOME/Library/LaunchAgents"

    # Build plist content
    if [ "$TRIGGER" = "daily" ]; then
        TRIGGER_XML="    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>17</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>"
        TRIGGER_DESC="daily at 5:00 PM"
    else
        TRIGGER_XML="    <key>RunAtLoad</key>
    <true/>"
        TRIGGER_DESC="at login"
    fi

    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$MAIN_SCRIPT</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
$TRIGGER_XML
    <key>StandardOutPath</key>
    <string>$LOG_FILE</string>
    <key>StandardErrorPath</key>
    <string>$LOG_FILE</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

    echo "Task Configuration:"
    echo "  Trigger: $TRIGGER_DESC"
    echo "  Execute: $PYTHON_BIN $MAIN_SCRIPT"
    echo "  Logs: $LOG_FILE"
    echo ""

    read -p "Install this launchd agent? [y/n]: " confirm

    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        # Unload existing agent if present
        launchctl unload "$PLIST_PATH" 2>/dev/null || true

        # Load new agent
        launchctl load "$PLIST_PATH"

        echo ""
        echo -e "${GREEN}Launchd agent installed successfully!${NC}"
        echo ""
        echo "The scraper will run $TRIGGER_DESC"
        echo ""
        echo -e "${CYAN}Useful commands:${NC}"
        echo "  Run now:    ./setup_scheduler.sh --run-now"
        echo "  Uninstall:  ./setup_scheduler.sh --uninstall"
        echo "  View logs:  tail -f $LOG_FILE"
        echo "  Status:     launchctl list | grep canvas"
    else
        rm -f "$PLIST_PATH"
        echo ""
        echo "Setup cancelled."
    fi
}

# ============================================================================
# Linux: Use cron with @reboot
# ============================================================================
setup_linux() {
    echo -e "${CYAN}Canvas Scraper - Linux Scheduler Setup${NC}"
    echo "========================================"
    echo ""

    # Cron entries
    CRON_REBOOT="@reboot sleep 60 && cd $PROJECT_DIR && $PYTHON_BIN $MAIN_SCRIPT >> $LOG_FILE 2>&1"
    CRON_DAILY="0 17 * * * cd $PROJECT_DIR && $PYTHON_BIN $MAIN_SCRIPT >> $LOG_FILE 2>&1"

    if $UNINSTALL; then
        if crontab -l 2>/dev/null | grep -q "$MAIN_SCRIPT"; then
            crontab -l 2>/dev/null | grep -v "$MAIN_SCRIPT" | crontab -
            echo -e "${GREEN}Cron job removed successfully.${NC}"
        else
            echo -e "${YELLOW}No cron job found.${NC}"
        fi
        return
    fi

    if $RUN_NOW; then
        echo "Running scraper now..."
        cd "$PROJECT_DIR" && "$PYTHON_BIN" "$MAIN_SCRIPT"
        return
    fi

    # Select cron entry based on trigger
    if [ "$TRIGGER" = "daily" ]; then
        CRON_ENTRY="$CRON_DAILY"
        TRIGGER_DESC="daily at 5:00 PM"
    else
        CRON_ENTRY="$CRON_REBOOT"
        TRIGGER_DESC="at system startup (after 60s delay)"
    fi

    echo "Task Configuration:"
    echo "  Trigger: $TRIGGER_DESC"
    echo "  Cron entry: $CRON_ENTRY"
    echo ""

    read -p "Add this cron job? [y/n]: " confirm

    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        # Remove existing entry if present
        if crontab -l 2>/dev/null | grep -q "$MAIN_SCRIPT"; then
            echo -e "${YELLOW}Removing existing cron job...${NC}"
            crontab -l 2>/dev/null | grep -v "$MAIN_SCRIPT" | crontab -
        fi

        # Add new entry
        (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

        echo ""
        echo -e "${GREEN}Cron job added successfully!${NC}"
        echo ""
        echo "The scraper will run $TRIGGER_DESC"
        echo ""
        echo -e "${CYAN}Useful commands:${NC}"
        echo "  Run now:    ./setup_scheduler.sh --run-now"
        echo "  Uninstall:  ./setup_scheduler.sh --uninstall"
        echo "  View cron:  crontab -l"
        echo "  View logs:  tail -f $LOG_FILE"
    else
        echo ""
        echo "Cron job not added."
    fi
}

# ============================================================================
# WSL: Use Windows Task Scheduler via PowerShell
# ============================================================================
setup_wsl() {
    echo -e "${CYAN}Canvas Scraper - WSL Scheduler Setup${NC}"
    echo "======================================"
    echo ""
    echo -e "${YELLOW}Note: WSL requires Windows Task Scheduler for reliable startup tasks.${NC}"
    echo ""

    if $UNINSTALL; then
        powershell.exe -ExecutionPolicy Bypass -File "$PROJECT_DIR/setup_scheduler.ps1" -Uninstall
        return
    fi

    if $RUN_NOW; then
        powershell.exe -ExecutionPolicy Bypass -File "$PROJECT_DIR/setup_scheduler.ps1" -RunNow
        return
    fi

    echo "This will create a Windows scheduled task that runs the scraper via WSL."
    echo ""

    # Call PowerShell script
    powershell.exe -ExecutionPolicy Bypass -File "$PROJECT_DIR/setup_scheduler.ps1" -TriggerType "$TRIGGER"
}

# ============================================================================
# Main
# ============================================================================
echo ""

case $PLATFORM in
    mac)
        setup_mac
        ;;
    linux)
        setup_linux
        ;;
    wsl)
        setup_wsl
        ;;
    *)
        echo -e "${RED}Error: Unsupported platform${NC}"
        echo "This script supports macOS, Linux, and WSL."
        exit 1
        ;;
esac
