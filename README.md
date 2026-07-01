# Canvas File Scraper (v1.3.0.0)

Lazy to click buttons? Me too.

Downloads course files from Canvas, skips the junk (videos, 500MB lecture recordings, textbooks), and emails you a daily digest of what's new. Runs on your laptop **or** in the cloud so your iPad gets your files while you nap.

[![Tests](https://github.com/anselmlong/canvas-scraper/actions/workflows/test.yml/badge.svg)](https://github.com/anselmlong/canvas-scraper/actions/workflows/test.yml)

---

## Quickest path — no laptop needed (iPad-friendly)

Use this repo as a **GitHub template**, and GitHub Actions runs the scraper daily for free. Files land in your Google Drive / Dropbox / OneDrive, which the iPad Files app reads natively. Your computer never needs to be on.

```
1. Click "Use this template" → you get your own repo
2. Add 4 secrets to your repo (Settings → Secrets → Actions):
   • CANVAS_API_TOKEN — from Canvas → Account → Settings → New Access Token
   • CONFIG_YAML — your config (run `python src/main.py --export-config`)
   • EMAIL_USERNAME — your Gmail address
   • EMAIL_APP_PASSWORD — 16-char Gmail App Password
3. Go to Actions tab → enable workflows → done
```

It runs daily at 12:00 SGT. You get an email digest and your files appear in cloud storage. Full walkthrough: **[docs/CLOUD_SYNC.md](docs/CLOUD_SYNC.md)**.

> **Can't run Python on your machine?** Use the `--export-config` flag from any machine with Python installed to generate your `CONFIG_YAML`:
> ```bash
> pip install canvasapi pyyaml python-dotenv
> python src/main.py --export-config
> # Paste the output into your CONFIG_YAML secret
> ```

---

## Local install (laptop / desktop)

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/anselmlong/canvas-scraper/master/install.sh)"
```

This clones the repo, sets up Python, and walks you through the setup wizard. Prefer to do it by hand? See [Manual installation](#manual-installation).

Once installed, schedule it to run daily:
```bash
./setup_scheduler.sh
```

---

## What you get

| Feature | Local | Cloud (iPad) |
|---------|-------|-------------|
| Smart filtering (skip videos, textbooks, >50MB files) | ✅ | ✅ |
| Course selection with fuzzy matching | ✅ | ✅ |
| Incremental sync (only new/changed files) | ✅ | ✅ |
| Daily email digest (new files, announcements, assignments) | ✅ | ✅ |
| Files organized by course on your machine | ✅ | — |
| Files in Google Drive / iCloud / Dropbox (iPad-ready) | ✅ (if download folder is synced) | ✅ |
| Works without your computer on | ❌ | ✅ |
| Works on an iPad | ❌ | ✅ |

---

## Manual installation

### Prerequisites

- Python 3.9+
- Canvas API token (Account → Settings → New Access Token)
- Gmail account with App Password ([instructions](https://support.google.com/accounts/answer/185833))

### Steps

```bash
git clone https://github.com/anselmlong/canvas-scraper.git
cd canvas-scraper
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py --setup   # Interactive setup wizard
```

### Run

```bash
python src/main.py           # Full sync
python src/main.py --dry-run # Preview only
python src/main.py --list-courses  # See your courses and their IDs
```

### Configuration

Create `.env` with your secrets:
```bash
CANVAS_API_TOKEN=your_token_here
```

Edit `config.yaml` to control filtering, download paths, and email settings — see the full [Configuration reference](#configuration) below.

---

## Cloud Sync (iPad mode)

Two paths:

**Path 1: Run locally, sync to cloud** — Point `download.base_path` to your iCloud/Google Drive/Dropbox folder. Files appear on your iPad automatically. Your computer needs to be on.

**Path 2: Run on GitHub Actions (recommended)** — The scraper runs on GitHub's servers daily. No laptop needed. Setup guide: **[docs/CLOUD_SYNC.md](docs/CLOUD_SYNC.md)**.

For the GitHub Actions path, you'll need the `--export-config` flag to generate your `CONFIG_YAML`:
```bash
python src/main.py --export-config
```

---

## Configuration

### Filter Settings

```yaml
filters:
  max_file_size_mb: 50
  extension_blacklist:
    - .mp4
    - .avi
    - .mov
    - .epub
    - .mobi
  name_patterns_to_skip:
    - textbook
    - ebook
    - recording
  pdf_max_size_mb: 30
```

### Download Settings

```yaml
download:
  base_path: "~/CanvasFiles"
  max_file_size_mb: 50
  concurrent_downloads: 3
```

### Email Settings

```yaml
notification:
  email:
    enabled: true
    recipient: "you@gmail.com"
    smtp_server: "smtp.gmail.com"
    smtp_port: 587  # Use 465 if your network blocks STARTTLS
```

---

## File Organization

```
~/CanvasFiles/
├── CS1101S - Intro to Computer Science (2026)/
│   ├── Lectures/
│   ├── Assignments/
│   └── Resources/
└── MA1522 - Linear Algebra (2026)/
    └── Problem_Sets/
```

---

## Email Reports

After each run you get an HTML email with:
- New, updated, and skipped file counts (by course)
- New announcements and upcoming assignments
- Links to skipped files so you can grab what you need manually

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Authentication failed" | Check your Canvas API token in `.env` — generate a new one if expired |
| Email auth failed | Use a Gmail App Password, not your regular password. Enable 2FA first |
| Connection refused (email) | Switch `smtp_port` to 465 — some networks block port 587's STARTTLS |
| Files not downloading | Run `--dry-run` to see what would be downloaded; check filter settings |
| WSL shutdown hangs | The scraper catches SIGTERM. If it still hangs, `taskkill /F /IM wsl.exe` |
| Cron not running (Linux) | Check `crontab -l`; look for errors in `/var/log/syslog` \| `grep CRON` |

Full troubleshooting: see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) *(coming soon)*.

---

## Database

SQLite at `data/scraper.db`. Tracks downloads, skipped files, and run history.
```bash
rm data/scraper.db  # Start fresh
```

---

## Project Status

**Active.** Built for my own NUS workflow, shared because it saves other people the same clicking. Works with any Canvas LMS instance — just change `base_url` in config.

**v1.3.0.0** — cloud sync, one-click installer, non-interactive mode, `--export-config` flag.

---

MIT License. Drop a star if this saves you time.