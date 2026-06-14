# Cloud Sync — your laptop can nap too

By default the scraper runs on your computer, which means your computer has
to be on. This guide moves the daily sync to GitHub Actions (free) and pushes
the files to cloud storage (Google Drive, Dropbox, or OneDrive), so:

- **Nothing needs to run at home.** GitHub's servers do the clicking.
- **It works on iPad.** Files land in cloud storage, which shows up in the
  iPad Files app. The daily email digest arrives wherever your email does.

Setup takes about ten minutes, once, ever.

## 1. Get your own copy of the repo

Fork this repository on GitHub (or import it into a **private** repo if you
prefer — Settings aren't shared, your secrets are yours either way).

## 2. Add your secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | Value |
|---|---|
| `CANVAS_API_TOKEN` | Canvas → Account → Settings → New Access Token |
| `EMAIL_USERNAME` | Your Gmail address |
| `EMAIL_APP_PASSWORD` | 16-character Gmail App Password ([instructions](https://support.google.com/accounts/answer/185833)) |
| `CONFIG_YAML` | The full contents of your `config.yaml` (see below) |

For `CONFIG_YAML`, paste a complete config. Easiest path: run the setup
wizard locally once (`python src/main.py --setup`) and paste the resulting
`config.yaml`. Any `download.base_path` works — the workflow reads it from
the config to know what to upload. A minimal example:

```yaml
canvas:
  base_url: "https://canvas.nus.edu.sg/"
download:
  base_path: "~/CanvasFiles"
  max_file_size_mb: 50
  concurrent_downloads: 3
courses:
  sync_mode: "whitelist"
  whitelist:
    - 12345   # course IDs from `python src/main.py --list-courses`
notification:
  email:
    enabled: true
    recipient: "you@gmail.com"
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    from_name: "Canvas Scraper"
```

At this point the daily email digest already works. If that's all you want
(announcements + assignments on your iPad via email), you're done — skip to
step 4.

## 3. Connect cloud storage (the iPad part)

The workflow uses [rclone](https://rclone.org/) to upload downloaded files.
On any computer (just once, to generate credentials):

```bash
# Install rclone, then create a remote named e.g. "gdrive"
rclone config
# Follow the prompts: choose Google Drive / Dropbox / OneDrive, authorize in browser

# Print the resulting config
cat ~/.config/rclone/rclone.conf
```

Then in your GitHub repo:

1. **New repository secret** `RCLONE_CONF` → paste the entire `rclone.conf` contents.
2. **Settings → Secrets and variables → Actions → Variables → New repository variable**
   `RCLONE_REMOTE` → where files should go, e.g. `gdrive:CanvasFiles`. Required
   whenever `RCLONE_CONF` is set — the workflow fails with a clear error if it's missing.

> **Token expiry caveat:** the workflow recreates `rclone.conf` from the secret on
> every run, so token refreshes rclone performs are thrown away with the runner.
> Google Drive refresh tokens are long-lived and generally fine. OneDrive and
> Dropbox rotate refresh tokens, so uploads may start failing after weeks or months —
> the fix is re-running `rclone config reconnect <remote>:` locally and re-pasting
> the secret. If you have the choice, Google Drive is the low-maintenance option.

On your iPad, open the **Files** app → enable the Google Drive / Dropbox /
OneDrive provider. Your course files appear there after each run, organized
by course, same as the local layout.

## 4. Turn it on

1. Go to the **Actions** tab of your repo and enable workflows (GitHub
   disables them on forks until you click the button).
2. Run it once manually: **Actions → Canvas Sync → Run workflow**.
3. Check the logs, then check your email and your cloud storage.

It now runs daily at 12:00 SGT. To change the time, edit the `cron` line in
`.github/workflows/sync.yml` (note: it's in UTC).

## How it stays incremental

The scraper tracks downloads in a SQLite database (`data/scraper.db`). The
workflow persists it between runs with GitHub's cache. Two consequences:

- GitHub evicts caches unused for 7 days. A daily schedule keeps it warm; if
  it ever gets evicted, the next run re-downloads everything once and
  re-uploads it (harmless, but expect one very enthusiastic email).
- The upload step uses `rclone copy`, never `sync` — old files in your cloud
  storage are never deleted by the workflow.

## Notes

- **Scheduled workflows on forks pause after 60 days without commits.**
  GitHub emails you first; one click re-enables it. (Or push any commit.)
- **Costs nothing.** A sync run takes a minute or two; public repos have
  unlimited Actions minutes, and private repos get 2,000 free per month.
- **New courses** are detected automatically and mentioned in the email
  digest. To start syncing one, add its ID to the `whitelist` in your
  `CONFIG_YAML` secret.
