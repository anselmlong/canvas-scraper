# Canvas File Scraper (v1.1.0)

Lazy to click buttons? Me too.

Introducing an automated file synchronization tool for Canvas LMS that intelligently downloads course files to your local machine while filtering out large or unwanted content. This tool also checks for new announcements/assignments daily, and emails you an update as long as your computer is running.

Drop me a star if you use this!

> **Note for WSL users**: v1.1.0 fixes a critical bug where the scraper could cause WSL to hang during shutdown by ensuring graceful termination of all download threads.

## New in v1.1.0
- **WSL Stability Fix**: Improved signal handling to prevent `wsl --shutdown` from hanging.
- **Standalone Packaging**: Instructions for creating a single executable for non-technical users.
- **Improved Versioning**: Formal version tracking for better update management.

## Features

- **Smart Filtering**: Skip large files (>50 MB), videos, and textbooks automatically
- **Course Selection**: Interactive course selection with fuzzy matching (type "cs" to match "CS 101")
- **Auto-Detection**: Automatically detects new courses each run and prompts you to add them
- **Incremental Sync**: Only downloads new or updated files
- **Email Reports**: Detailed HTML email reports after each run showing what was downloaded and what was skipped
- **Skipped File Review**: Email includes links to skipped files so you can manually download what you need
- **Organized Storage**: Files organized by course and folder structure, mirroring Canvas layout
- **Scheduled Runs**: Set up automated daily runs (noon by default) using cron/Task Scheduler
- **Retry Logic**: Automatically retries failed downloads (3 attempts with exponential backoff)
- **Graceful Shutdown**: Handles SIGTERM/SIGINT signals cleanly, cancelling in-progress downloads and cleaning up partial files so `wsl --shutdown` doesn't hang
- **Database Tracking**: SQLite database tracks all downloads and skipped files

## Standalone Executable (For Non-Technical Users)

If you don't want to deal with Python, you can download a pre-built executable for your platform from the **[GitHub Releases](https://github.com/anselmlong/canvas-scraper/releases)** page.

### 1. Download & Run
- Download the version for your OS (e.g., `canvas-scraper-windows.exe`).
- Copy it to a new folder where you want the app to live.
- Double-click to run it!

### 2. GUI Setup
If it's your first time running the app, it will automatically launch a **GUI Setup Wizard** (no terminal typing required!) to help you:
1. Connect to Canvas (API Token).
2. Choose where to save your files.
3. Select which courses to synchronize.

### 3. Automated Sync
Once set up, the app will run its first sync. You can then use the provided scripts to schedule it to run daily at your preferred time.

---

## Developer: Building the Executable

If you've modified the code and want to build your own executable:

1. **Install Build Tools**:
   ```bash
   pip install pyinstaller
   ```

2. **Build**:
   ```bash
   python build_exe.py
   ```
   The executable will be in the `dist/` folder.

## Requirements

- Python 3.9 or higher
- Canvas LMS account with API access
- Gmail account with App Password (for email notifications)

## Installation

1. **Clone or download this repository**

```bash
cd ~/Projects
git clone <repo-url> canvas-scraper
cd canvas-scraper
```

2. **Create virtual environment and install dependencies**

```bash
python -m venv venv

# Linux/Mac:
source venv/bin/activate

# Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Setup

### Quick Start

Run the interactive setup wizard:

```bash
python src/main.py --setup
```

The wizard will guide you through:
1. Canvas API configuration
2. Download location selection
3. Course selection (with fuzzy matching)
4. Email notification setup

### Manual Configuration

If you prefer to configure manually:

1. **Get your Canvas API token**:
   - Log in to Canvas
   - Go to Account → Settings
   - Scroll to "Approved Integrations"
   - Click "+ New Access Token"
   - Enter a purpose (e.g., "canvas-scraper") and optional expiry date
   - Copy the generated token immediately (Canvas won’t show it again)

2. **Get Gmail App Password**:
   - Enable 2-Step Verification on your Google account
   - Go to https://myaccount.google.com/apppasswords
   - Generate an app password for "Mail"
   - Copy the 16-character password

3. **Create `.env` file**:

```bash
cp .env.example .env
# Edit .env and add your credentials
```

4. **Create `config.yaml`**:

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
# For NUS, set: canvas.base_url: "https://canvas.nus.edu.sg/"
```

## Usage

### First Sync

After setup, run your first sync:

```bash
python src/main.py
```

This will:
- Check all selected courses for files
- Download new files that pass filters
- Send an email report with results

```

## Scheduling Automated Runs

The scraper can run daily at 5pm, or a time of your choice.

### Quick Setup (All Platforms)

```bash
./setup_scheduler.sh
```

The script auto-detects your platform and uses the appropriate method:

| Platform | Method | Trigger |
|----------|--------|---------|
| **Windows** | Task Scheduler | At login |
| **WSL** | Task Scheduler (via Windows) | At login |
| **macOS** | launchd | At login |
| **Linux** | cron @reboot | At startup |

### Options

```bash
# Run on login (default, recommended)
./setup_scheduler.sh

# Run daily at 5pm
./setup_scheduler.sh --trigger daily

# Remove scheduled task
./setup_scheduler.sh --uninstall
```

On WSL, the scheduled task uses `run_with_timeout.sh` which wraps the scraper with a 15-minute timeout and signal handling, so `wsl --shutdown` won't hang.

## Configuration

### Filter Settings

Edit `config.yaml` to customize filtering:

```yaml
filters:
  # Maximum file size (MB)
  max_file_size_mb: 50
  
  # File extensions to always skip
  extension_blacklist:
    - .mp4  # Videos
    - .avi
    - .mov
    - .epub # Ebooks
    - .mobi
  
  # Skip files with these words in the name
  name_patterns_to_skip:
    - textbook
    - ebook
    - recording
  
  # Flag PDFs larger than this as likely textbooks
  pdf_max_size_mb: 30
```

### Download Settings

```yaml
download:
  base_path: "~/CanvasFiles"  # Where to save files
  max_file_size_mb: 50        # Maximum file size
  concurrent_downloads: 3      # Parallel downloads
```

### Email Settings

```yaml
notification:
  email:
    enabled: true
    recipient: "your_email@example.com"
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
```

## File Organization

Files are organized by course structure:

```
~/CanvasFiles/
├── CS1101S - Intro to Computer Science (2026)/
│   ├── Lectures/
│   │   ├── Week_1_Introduction.pdf
│   │   └── Week_2_Variables.pptx
│   ├── Assignments/
│   │   └── HW1.docx
│   └── Resources/
└── MA1522 - Linear Algebra (2026)/
    ├── Problem_Sets/
    └── Syllabus.pdf
```

## Email Reports

After each run, you'll receive an HTML email report containing:

- **Summary**: Counts of new, updated, and skipped files
- **New Files**: List of files downloaded grouped by course
- **Updated Files**: Files that were re-downloaded due to changes
- **Skipped Files**: NEW skipped files with:
  - File name and size
  - Reason for skipping
  - Folder location on Canvas
  - Direct link to download manually
- **New Courses**: Newly detected courses you can add
- **New Announcements**: Never miss out!
- **New Assignments**: Stay on top!

### Skipped File Example

If a file is skipped, you'll see:

```
CS 101 - Introduction to Computer Science
  
  Lecture_Recording_Week6.mp4
  📏 Size: 485 MB
  📂 Location: Lectures / Week 6
  🚫 Reason: Video file (.mp4) - videos are blacklisted
  🔗 View & Download on Canvas
```

Click the link to decide if you want to download it manually.

## Logs

Logs are written to `logs/scraper.log`:

```bash
# View recent logs
tail -f logs/scraper.log

# View last run
tail -n 100 logs/scraper.log
```

## Troubleshooting

### Canvas API Token Issues

**Error: "Authentication failed"**
- Verify your API token in `.env`
- Generate a new token from Canvas if needed
- Check that token hasn't expired

### Email Issues

**Error: "Email authentication failed"**
- Make sure you're using a Gmail **App Password**, not your regular password
- Verify 2-Step Verification is enabled on your Google account
- Check credentials in `.env`

**Error: "Connection refused"**
- Check your internet connection
- Verify SMTP settings in `config.yaml`

### Download Issues

**Files aren't downloading**
- Check filter settings in `config.yaml`
- Run with `--dry-run` to see what would be downloaded
- Check logs for specific errors

**"Permission denied" errors**
- Ensure download path exists and is writable
- Check file permissions on the download directory

### WSL: `wsl --shutdown` Hangs

The scheduled task runs the scraper inside WSL. If `wsl --shutdown` hangs, the scraper may still be running.

The scraper handles this automatically via layered timeouts:
1. **Signal handling** - WSL sends SIGTERM on shutdown; the scraper catches it and exits within seconds
2. **`run_with_timeout.sh`** - Kills the process after 15 minutes as a safety net
3. **Task Scheduler limit** - Terminates the task after 20 minutes as a final backstop

If you still experience issues:
```powershell
# Force-kill and re-register the task
taskkill /F /IM wsl.exe
wsl --shutdown
.\setup_scheduler.ps1 -Uninstall
.\setup_scheduler.ps1
```

### Cron Job Not Running

**Linux/Mac**:
```bash
# Check if cron job exists
crontab -l

# Check system logs
grep CRON /var/log/syslog
```

**Windows**:
```powershell
# Check if task exists
Get-ScheduledTask -TaskName CanvasScraper

# View task history
Get-ScheduledTask -TaskName CanvasScraper | Get-ScheduledTaskInfo
```

## Database

The scraper uses SQLite to track downloads and skipped files:

- **Location**: `data/scraper.db`
- **Tables**:
  - `downloaded_files`: Tracks all downloaded files
  - `skipped_files`: Tracks files that didn't pass filters
  - `run_history`: History of sync runs

**Reset database** (start fresh):
```bash
rm data/scraper.db
```

## Advanced Usage

### Custom Download Location

During setup, specify any path:
```
Where should files be downloaded? (default: ~/CanvasFiles): /mnt/storage/Canvas
```

### Modify Filters

Edit `config.yaml` to customize what gets downloaded:

**Allow specific video formats**:
Remove `.mp4` from `extension_blacklist`

**Increase size limit**:
```yaml
max_file_size_mb: 100  # Allow up to 100 MB
```

**Add custom skip patterns**:
```yaml
name_patterns_to_skip:
  - draft
  - old version
  - archive
```

## Security

- **API tokens** are stored in `.env` (never committed to git)
- **Email passwords** use App Passwords (can be revoked without changing main password)
- **.env file** should have restricted permissions: `chmod 600 .env`
- **Database** contains file metadata only, not actual file content

## Contributing

Found a bug or have a feature request? Please open an issue!

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [canvasapi](https://github.com/ucfopen/canvasapi) for Canvas LMS integration
- Uses [thefuzz](https://github.com/seatgeek/thefuzz) for fuzzy course matching
