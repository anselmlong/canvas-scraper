# TODOS

## CLI

### Implement --reselect-courses, --add-courses, --remove-courses
**Priority:** P1
The flags are defined in `src/main.py` argparse and documented in README/QUICKSTART, but never handled in `main()` — they silently fall through to a full sync. `--list-courses` was implemented in v1.3.0.0; these three still need wiring to `CourseManager.interactive_course_selection` / `add_courses_to_config`. Noticed on branch feat/cloud-sync-and-installer.

## Cloud Sync

### Digest email sent before rclone upload completes
**Priority:** P3
`run_sync` sends the email inside the sync step, but the upload to cloud storage happens in a later workflow step. If the upload fails, the recipient was already told "N new files downloaded" while nothing reached their Drive (self-heals next run, but the digest repeats). Reordering would require decoupling email sending from `run_sync`.

### Document Windows-style base_path behavior in CONFIG_YAML
**Priority:** P3
A `C:/Users/...` path pasted into the cloud `CONFIG_YAML` resolves relative to the runner workspace. Sync and upload happen to agree so it works, but it's fragile — worth a one-line warning in docs/CLOUD_SYNC.md.

## Completed

### Cloud sync via GitHub Actions + rclone, one-click installer, --non-interactive flag
**Completed:** v1.3.0.0 (2026-06-10)
