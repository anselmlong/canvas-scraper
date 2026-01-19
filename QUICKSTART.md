# Canvas Scraper - Quick Start Guide

Get up and running in 5 minutes!

## Installation

```bash
# 1. Navigate to project directory
cd canvas-scraper

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\activate   # Windows

# 4. Install dependencies
pip install -r requirements.txt
```

## Setup

### Step 1: Run Setup Wizard

```bash
python src/main.py --setup
```

### Step 2: Get Canvas API Token

1. Log in to Canvas
2. Go to **Account** → **Settings**
3. Scroll to **"Approved Integrations"**
4. Click **"+ New Access Token"**
5. Give it a purpose (e.g., "File Scraper")
6. Click **"Generate Token"**
7. **Copy the token** (you won't see it again!)

Paste this token when the setup wizard asks for it.

### Step 3: Get Gmail App Password

1. Enable **2-Step Verification** on your Google account:
   - Go to https://myaccount.google.com/security
   - Enable 2-Step Verification

2. Generate App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select **"Mail"** as the app
   - Select **"Other"** as the device
   - Name it "Canvas Scraper"
   - Click **"Generate"**
   - **Copy the 16-character password**

Paste this when the setup wizard asks for your Gmail App Password.

### Step 4: Select Courses

The wizard will show all your active Canvas courses. You can:

- Type **"all"** to sync all courses
- Type course numbers: **"1,3,5"**
- Type course codes with fuzzy matching: **"cs, math"**

If multiple courses match, you'll be asked to choose which one.

### Step 5: Choose Download Location

Default: `~/CanvasFiles`

You can change this to any location like:
- `~/Documents/Canvas`
- `/mnt/storage/Canvas`
- `C:\Users\YourName\Canvas`

## First Run

After setup completes, run your first sync:

```bash
python src/main.py
```

You should see:
- Files being discovered from Canvas
- Downloads happening in real time
- A summary at the end
- An email with a detailed report

## Preview (Dry Run)

Want to see what would be downloaded without actually downloading?

```bash
python src/main.py --dry-run
```

This shows you exactly what files would be downloaded and which would be skipped.

## Schedule Automated Runs

Set up automatic syncing when you log in (recommended) or daily at noon.

### All Platforms (Auto-Detect)

```bash
./setup_scheduler.sh
```

This auto-detects your platform:
- **Windows/WSL**: Creates a Windows Task Scheduler task
- **macOS**: Creates a launchd agent
- **Linux**: Adds a cron @reboot job

### Options

```bash
# Run on login (default)
./setup_scheduler.sh

# Run daily at noon instead
./setup_scheduler.sh --trigger daily

# Run immediately
./setup_scheduler.sh --run-now

# Remove scheduled task
./setup_scheduler.sh --uninstall
```

### Windows / WSL (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
```

## Common Commands

```bash
# Normal sync
python src/main.py

# Preview without downloading
python src/main.py --dry-run

# Sync without email notification
python src/main.py --no-email

# Add newly detected courses
python src/main.py --add-courses

# Test email configuration
python src/main.py --test-email

# Verbose logging
python src/main.py --verbose

# View logs
tail -f logs/scraper.log
```

## What Gets Downloaded?

By default, the scraper downloads:
- ✓ PDFs under 30 MB
- ✓ Documents (.docx, .pptx, .xlsx)
- ✓ Code files (.py, .js, .java, etc.)
- ✓ Presentations
- ✓ Spreadsheets
- ✓ ZIP files

And skips:
- ✗ Videos (.mp4, .avi, .mov, etc.)
- ✗ Large files (>50 MB)
- ✗ Ebooks (.epub, .mobi)
- ✗ Files with "textbook" or "recording" in the name
- ✗ Large PDFs (>30 MB, likely textbooks)

## Understanding Email Reports

After each run, you'll get an email with:

1. **Summary** - Quick stats (5 new, 2 updated, 3 skipped)
2. **New Files** - What was downloaded
3. **Updated Files** - What was re-downloaded (changed on Canvas)
4. **Skipped Files** - Files that didn't pass filters with:
   - Why it was skipped
   - Direct link to download manually if you want it

Example skipped file:
```
Lecture_Recording_Week6.mp4
📏 Size: 485 MB
📂 Location: Lectures / Week 6
🚫 Reason: Video file (.mp4) - videos are blacklisted
🔗 View & Download on Canvas
```

Click the link if you decide you want it!

## Customizing Filters

Edit `config.yaml` to change what gets downloaded:

```yaml
filters:
  # Increase size limit to 100 MB
  max_file_size_mb: 100
  
  # Add more skip patterns
  name_patterns_to_skip:
    - draft
    - old version
    - archive
```

## Troubleshooting

### "Canvas API token not set"
- Run `python src/main.py --setup` again
- Make sure you copied the full token

### "Email authentication failed"
- You must use a Gmail **App Password**, not your regular password
- Make sure 2-Step Verification is enabled
- Generate a new app password if needed

### "No courses selected"
- Run `python src/main.py --add-courses`
- Select the courses you want to sync

### Files aren't downloading
- Check `config.yaml` filter settings
- Run `--dry-run` to see what would be downloaded
- Check `logs/scraper.log` for errors

## Getting Help

Check the full README.md for:
- Detailed configuration options
- Advanced usage
- Security information
- Complete troubleshooting guide

## Next Steps

1. **Run your first sync**: `python src/main.py`
2. **Check your email** for the report
3. **Review skipped files** and download manually if needed
4. **Set up scheduling** to run automatically: `./setup_scheduler.sh`
5. **Customize filters** in `config.yaml` if needed

That's it! Your Canvas files will now sync automatically every time you log in.
