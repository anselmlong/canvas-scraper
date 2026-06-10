# Changelog

All notable changes to canvas-scraper are documented here.
Versions follow `MAJOR.MINOR.PATCH.MICRO`. History before 1.3.0.0 predates this file.

## [1.3.0.0] - 2026-06-10

**Your laptop can nap too. The daily sync now runs in the cloud, and the files land on your iPad.**

Until now the scraper only worked "as long as your computer is running." This release removes that caveat: a GitHub Actions workflow runs the daily sync on GitHub's servers and delivers files straight to Google Drive, Dropbox, or OneDrive — which the iPad Files app reads natively. The email digest keeps arriving wherever your email lives. Setup is about ten minutes, once: see [docs/CLOUD_SYNC.md](docs/CLOUD_SYNC.md).

### Added

- **Cloud mode** (`.github/workflows/sync.yml`): daily sync on GitHub Actions with config from a `CONFIG_YAML` secret, incremental-sync database persisted between runs via the Actions cache, and optional rclone upload to cloud storage. The cache is only saved when the upload succeeded, so a failed upload self-heals on the next run instead of leaving permanent gaps. Uses `rclone copy` (never `sync`) so nothing in your cloud storage is ever deleted.
- **One-line install**: `bash -c "$(curl -fsSL https://raw.githubusercontent.com/anselmlong/canvas-scraper/master/install.sh)"` clones, sets up the venv, installs dependencies, and launches the setup wizard. Safe to re-run; refuses to touch a directory that belongs to a different repo; truncation-safe for flaky connections.
- **`--non-interactive` flag**: scheduled runs can never hang waiting for keyboard input again. When unconfigured, the scraper exits with a clear error instead of silently blocking on the setup wizard — this also activates automatically whenever stdin is not a terminal (cron, Task Scheduler, CI). All scheduler setup scripts now pass it explicitly.
- **`--list-courses` now works**: prints your active Canvas courses with IDs and marks the ones in your sync whitelist. (Previously the flag was accepted but silently ran a full sync instead.)
- **iPad guide in the README**: the zero-code option (point `download.base_path` at a cloud-synced folder) and the cloud option, laziest first.
- **CI tests** (`.github/workflows/test.yml`): the pytest suite runs on every push and pull request.

### Changed

- Sync failures are now loud: invalid configuration and failed digest emails exit non-zero, so cron and the cloud workflow show red instead of green-but-dead.
- The setup wizard refuses to start without an interactive terminal instead of hanging on `input()`.

### Fixed

- Scheduled runs on a machine with missing/broken config no longer hang forever on an invisible setup-wizard prompt.
