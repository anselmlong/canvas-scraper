#!/usr/bin/env bash
# Canvas Scraper one-click installer.
#
# Run it like this (keeps your terminal interactive so the setup wizard works):
#
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/anselmlong/canvas-scraper/master/install.sh)"
#
# What it does: checks Python, clones the repo to ~/canvas-scraper (or pulls
# if already there), creates a venv, installs dependencies, then launches the
# setup wizard. Re-running it is safe.

set -euo pipefail

REPO_URL="https://github.com/anselmlong/canvas-scraper.git"
INSTALL_DIR="${CANVAS_SCRAPER_DIR:-$HOME/canvas-scraper}"

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
fail() {
    printf '\033[1;31mError:\033[0m %s\n' "$1" >&2
    exit 1
}

# Everything runs through main() so a truncated download parses but executes
# nothing (the call is the last line of the script)
main() {

# --- Python 3.9+ ---
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
        "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[ -n "$PYTHON" ] || fail "Python 3.9+ is required. Install it from https://www.python.org/downloads/ and re-run."

command -v git >/dev/null 2>&1 || fail "git is required. Install it and re-run."

# --- Clone or update ---
if [ -d "$INSTALL_DIR/.git" ]; then
    _remote=$(git -C "$INSTALL_DIR" remote get-url origin 2>/dev/null || echo "")
    case "$_remote" in
        *anselmlong/canvas-scraper*) ;;
        *) fail "$INSTALL_DIR is a different git repo ($_remote). Move it or set CANVAS_SCRAPER_DIR to another path." ;;
    esac
    info "Existing install found at $INSTALL_DIR, updating..."
    git -C "$INSTALL_DIR" pull --ff-only || info "Could not fast-forward (local changes?), continuing with current version."
elif [ -e "$INSTALL_DIR" ]; then
    fail "$INSTALL_DIR exists but is not a canvas-scraper checkout. Move it or set CANVAS_SCRAPER_DIR to another path."
else
    info "Cloning canvas-scraper to $INSTALL_DIR..."
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# --- Virtual environment + dependencies ---
if [ ! -f venv/bin/activate ]; then
    info "Creating virtual environment..."
    "$PYTHON" -m venv venv
fi

info "Installing dependencies..."
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

# --- Setup wizard ---
if [ -f config.yaml ]; then
    info "Already configured (config.yaml exists)."
    echo
    echo "Run a sync with:"
    echo "  cd $INSTALL_DIR && venv/bin/python src/main.py"
elif [ -t 0 ]; then
    info "Launching setup wizard..."
    venv/bin/python src/main.py --setup
else
    # stdin is not a terminal (e.g. curl | bash) - the wizard can't prompt
    info "Install complete. Finish setup from a terminal with:"
    echo "  cd $INSTALL_DIR && venv/bin/python src/main.py --setup"
fi

echo
info "To schedule daily runs: cd $INSTALL_DIR && ./setup_scheduler.sh"
info "To sync without your computer on (and read files on iPad): see docs/CLOUD_SYNC.md"
}

main "$@"
