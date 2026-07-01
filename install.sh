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
info "To sync without your computer on (iPad/cloud): see docs/CLOUD_SYNC.md"

# --- Optional: set up GitHub Actions cloud sync ---
echo
echo "─────────────────────────────────────────────"
echo "  Want iPad/cloud access too?"
echo ""
echo "  I can create a GitHub repo, push this install,"
echo "  and tell you exactly what secrets to add."
echo "─────────────────────────────────────────────"
echo -n "Set up cloud sync? (y/N) "
read -r CLOUD_CHOICE </dev/tty
case "$CLOUD_CHOICE" in
    [yY]|[yY][eE][sS])
        CLOUD_SETUP=1
        ;;
    *)
        CLOUD_SETUP=0
        ;;
esac

if [ "$CLOUD_SETUP" = "1" ]; then
    if command -v gh >/dev/null 2>&1; then
        # gh is available — try authenticated path
        if gh auth status 2>/dev/null; then
            echo
            info "GitHub CLI authenticated. Creating a repo..."
            echo -n "Repo name (default: canvas-scraper): "
            read -r REPO_NAME </dev/tty
            REPO_NAME="${REPO_NAME:-canvas-scraper}"

            # Create private repo and push
            gh repo create "$REPO_NAME" --private --source="$INSTALL_DIR" --remote=origin --push 2>&1 && {
                echo
                info "Repo created: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo 'your-account/$REPO_NAME')"
                echo
                echo "Now add these secrets (all are required except RCLONE_CONF):"
                echo "  https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/settings/secrets/actions"
                echo
                info "Secrets checklist:"
                echo "  1. CANVAS_API_TOKEN — your Canvas API token"
                echo "  2. CONFIG_YAML — run 'venv/bin/python src/main.py --export-config' to generate"
                echo "  3. EMAIL_USERNAME — your Gmail address"
                echo "  4. EMAIL_APP_PASSWORD — 16-char Gmail App Password"
                echo "  5. RCLONE_CONF — (optional) run 'rclone config' locally, paste rclone.conf"
                echo ""
                echo "Then go to Actions → enable workflows. Done."
            } || {
                echo
                info "Could not create repo. Try manually:"
                _print_cloud_instructions
            }
        else
            echo
            info "gh is installed but not authenticated."
            echo -n "Log in with 'gh auth login' first, or use the template approach."
            _print_cloud_instructions
        fi
    else
        echo
        info "gh (GitHub CLI) not found."
        _print_cloud_instructions
    fi
fi
}

_print_cloud_instructions() {
    echo ""
    echo "─────────────────────────────────"
    echo "  Cloud sync setup (2 minutes)"
    echo "─────────────────────────────────"
    echo ""
    echo "  1. Go to https://github.com/anselmlong/canvas-scraper"
    echo "  2. Click 'Use this template' → create your own repo"
    echo "  3. Add these secrets:"
    echo "     • CANVAS_API_TOKEN"
    echo "     • CONFIG_YAML      (run --export-config)"  
    echo "     • EMAIL_USERNAME"
    echo "     • EMAIL_APP_PASSWORD"
    echo "  4. Enable Actions → done"
    echo ""
    echo "  Full guide: docs/CLOUD_SYNC.md"
}

main "$@"
