"""Main entry point for Canvas File Scraper."""

import sys
import os
import signal
import threading
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

from config import Config
from canvas_client import CanvasClient
from metadata_db import MetadataDB
from file_organizer import FileOrganizer
from filter_engine import FilterEngine
from download_manager import DownloadManager, DownloadTask
from course_manager import CourseManager
from report_generator import ReportGenerator
from email_notifier import EmailNotifier


# Global shutdown event for graceful termination
shutdown_event = threading.Event()


def _shutdown_handler(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    logger = logging.getLogger(__name__)
    logger.info(f"Received {sig_name}, shutting down gracefully...")
    shutdown_event.set()


# Register signal handlers (SIGTERM for Task Scheduler / timeout kills)
signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging.

    Args:
        verbose: Enable verbose logging

    Returns:
        Configured logger
    """
    log_dir = Config.get_project_root() / "logs"
    log_dir.mkdir(exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO

    # Format
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler
    file_handler = logging.FileHandler(log_dir / "scraper.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


def _is_wsl() -> bool:
    """Check if running in WSL (Windows Subsystem for Linux).

    Returns:
        True if running in WSL, False otherwise
    """
    try:
        with open("/proc/version", "r") as f:
            content = f.read().lower()
            return "microsoft" in content or "wsl" in content
    except (OSError, IOError):
        return False


def _wsl_to_windows_path(wsl_path: str) -> str:
    """Convert WSL path to Windows path.

    Args:
        wsl_path: Path in WSL format (e.g., /mnt/c/Users/...)

    Returns:
        Windows path (e.g., C:\\Users\\...)
    """
    import subprocess

    try:
        result = subprocess.run(
            ["wslpath", "-w", wsl_path], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass

    # Fallback manual conversion for /mnt/ paths
    if wsl_path.startswith("/mnt/"):
        # /mnt/c/Users/... -> C:\Users\...
        parts = wsl_path[5:].split("/", 1)
        if len(parts) == 2:
            drive_letter = parts[0].upper()
            path = parts[1].replace("/", "\\")
            return f"{drive_letter}:\\{path}"

    return wsl_path


def _windows_to_wsl_path(windows_path: str) -> str:
    """Convert Windows path to WSL path.

    Args:
        windows_path: Path in Windows format (e.g., C:\\Users\\...)

    Returns:
        WSL path (e.g., /mnt/c/Users/...)
    """
    import subprocess

    try:
        result = subprocess.run(
            ["wslpath", "-u", windows_path], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass

    # Fallback manual conversion
    # C:\Users\... -> /mnt/c/Users/...
    if len(windows_path) >= 3 and windows_path[1] == ":":
        drive_letter = windows_path[0].lower()
        path = windows_path[3:].replace("\\", "/")
        return f"/mnt/{drive_letter}/{path}"

    return windows_path


def _open_native_folder_dialog() -> str:
    """Open platform-native folder selection dialog.

    For WSL users, this opens the Windows native dialog and returns
    the path in WSL format (/mnt/c/...).

    Returns:
        Selected folder path or empty string if cancelled/unavailable
    """
    import platform
    import subprocess

    system = platform.system()
    is_wsl = _is_wsl()

    try:
        # WSL: Use Windows PowerShell dialog
        if is_wsl:
            ps_script = """
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
            $dialog.Description = "Select Download Location"
            $dialog.ShowNewFolderButton = $true
            if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
                Write-Output $dialog.SelectedPath
            }
            """

            # Call Windows PowerShell from WSL
            result = subprocess.run(
                ["powershell.exe", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0 and result.stdout.strip():
                windows_path = result.stdout.strip()
                # Convert Windows path to WSL path
                wsl_path = _windows_to_wsl_path(windows_path)
                return wsl_path
            return ""

        # Native Windows
        elif system == "Windows":
            ps_script = """
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
            $dialog.Description = "Select Download Location"
            $dialog.ShowNewFolderButton = $true
            if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
                Write-Output $dialog.SelectedPath
            }
            """
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.stdout.strip()

        # macOS
        elif system == "Darwin":
            script = (
                'POSIX path of (choose folder with prompt "Select Download Location")'
            )
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return ""

        # Native Linux (not WSL)
        else:
            # Try zenity first (GNOME)
            try:
                result = subprocess.run(
                    [
                        "zenity",
                        "--file-selection",
                        "--directory",
                        "--title=Select Download Location",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except FileNotFoundError:
                pass

            # Try kdialog (KDE)
            try:
                result = subprocess.run(
                    [
                        "kdialog",
                        "--getexistingdirectory",
                        str(Path.home()),
                        "--title",
                        "Select Download Location",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except FileNotFoundError:
                pass

            # Fallback to tkinter if available
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)

                folder = filedialog.askdirectory(
                    title="Select Download Location", initialdir=str(Path.home())
                )
                root.destroy()
                return folder or ""
            except:
                pass

    except (subprocess.SubprocessError, OSError, RuntimeError) as e:
        logging.getLogger(__name__).debug(f"Error opening folder dialog: {e}")

    return ""


def setup_wizard(config: Config):
    """Run first-time setup wizard.

    Args:
        config: Config instance
    """
    print("\n" + "=" * 60)
    print("Canvas Scraper - First-Time Setup")
    print("=" * 60 + "\n")

    # Canvas configuration
    print("Step 1: Canvas Configuration\n")

    default_base_url = "https://canvas.nus.edu.sg/"
    base_url = input(
        f"Enter your Canvas base URL (default: {default_base_url}): "
    ).strip()
    if not base_url:
        base_url = default_base_url

    config.set("canvas.base_url", base_url)

    api_token = input(
        "\nEnter your Canvas API token: (Go to Canvas -> Account -> Settings -> Approved Integrations -> New Access Token) "
    ).strip()
    config.set_env("CANVAS_API_TOKEN", api_token)

    # Test connection
    print("\nTesting Canvas connection...")
    try:
        canvas_client = CanvasClient(base_url, api_token)
        success, message = canvas_client.test_connection()
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
            print("Please check your credentials and try again.")
            return
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    # Download location
    print("\nStep 2: Download Location\n")

    # Set appropriate default based on environment
    is_wsl = _is_wsl()
    if is_wsl:
        default_path = "/mnt/c/Users/CanvasFiles"
        print("Note: Running in WSL. You can select folders from Windows filesystem.")
        print(
            "      Windows paths will be automatically converted to /mnt/c/... format."
        )
    else:
        default_path = "~/CanvasFiles"

    use_gui = (
        input("\nUse folder browser to select download location? [y/n]: ")
        .strip()
        .lower()
    )

    if use_gui == "y":
        if is_wsl:
            print("Opening Windows file browser...")
        else:
            print("Opening folder browser...")

        download_path = _open_native_folder_dialog()

        if not download_path:
            print("No folder selected or dialog unavailable.")
            if not is_wsl:
                print(
                    "(Tip: Install 'zenity' for better file picker on Linux: sudo apt install zenity)"
                )
            download_path = input(
                f"Enter path manually (default: {default_path}): "
            ).strip()
            if not download_path:
                download_path = default_path
        else:
            print(f"Selected: {download_path}")
    else:
        if is_wsl:
            print("Example paths:")
            print("  /mnt/c/Users/YourName/Documents/CanvasFiles  (Windows C: drive)")
            print("  /mnt/d/CanvasFiles                           (Windows D: drive)")
            print("  ~/CanvasFiles                                (Linux home)")

        download_path = input(
            f"\nWhere should files be downloaded? (default: {default_path}): "
        ).strip()
        if not download_path:
            download_path = default_path

    config.set("download.base_path", download_path)

    # Create directory
    Path(download_path).expanduser().mkdir(parents=True, exist_ok=True)
    print(f"✓ Created directory: {download_path}")

    # Course selection
    print("\nStep 3: Course Selection\n")
    print("Fetching your courses...")

    course_manager = CourseManager(canvas_client, config)
    all_courses = course_manager.get_active_courses()

    if not all_courses:
        print("No active courses found.")
        return

    selected_courses = course_manager.interactive_course_selection(all_courses)
    course_manager.add_courses_to_config(selected_courses)
    print(f"\n✓ Added {len(selected_courses)} courses to sync list")

    # Email configuration
    print("\nStep 4: Email Notifications\n")
    enable_email = input("Enable email notifications? [y/n]: ").strip().lower()

    if enable_email == "y":
        print(
            "\nFor Gmail, you need to use an App Password (not your regular password)."
        )
        print("Instructions: https://support.google.com/accounts/answer/185833")

        email_user = input("\nEnter your Gmail address: ").strip()
        config.set("notification.email.recipient", email_user)
        config.set_env("EMAIL_USERNAME", email_user)

        email_pass = input("Enter your Gmail App Password: ").strip()
        config.set_env("EMAIL_APP_PASSWORD", email_pass)

        # Test email
        print("\nTesting email connection...")
        try:
            email_notifier = EmailNotifier(config)
            success, message = email_notifier.test_connection()
            if success:
                print(f"✓ {message}")

                send_test = input("Send test email? [y/n]: ").strip().lower()
                if send_test == "y":
                    if email_notifier.send_test_email():
                        print("✓ Test email sent successfully")
                    else:
                        print("✗ Failed to send test email")
            else:
                print(f"✗ {message}")
        except Exception as e:
            print(f"✗ Email test failed: {e}")
    else:
        config.set("notification.email.enabled", False)

    # Save configuration
    config.save()
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"\nConfiguration saved to: {config.config_path}")
    print("\nRun your first sync:")
    print("  python src/main.py")
    print("\nSet up scheduled runs:")
    print("  bash setup_scheduler.sh  (Linux/Mac)")
    print("  powershell setup_scheduler.ps1  (Windows)")
    print()


def run_sync(config: Config, dry_run: bool = False, send_email: bool = True):
    """Run file synchronization.

    Args:
        config: Config instance
        dry_run: If True, don't actually download files
        send_email: If True, send email notification
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting Canvas file sync")
    logger.info("=" * 60)

    # Validate configuration
    is_valid, errors = config.validate()
    if not is_valid:
        logger.error("Configuration is invalid:")
        for error in errors:
            logger.error(f"  - {error}")
        return

    # Initialize components
    api_token = config.canvas_api_token or ""
    canvas_client = CanvasClient(config.canvas_base_url, api_token)
    db_path = config.project_root / "data" / "scraper.db"
    db_path.parent.mkdir(exist_ok=True)
    metadata_db = MetadataDB(db_path)
    file_organizer = FileOrganizer(config.download_path)
    filter_engine = FilterEngine(config.get("filters"))
    download_manager = DownloadManager(
        canvas_client,
        max_workers=config.get("download.concurrent_downloads", 3),
        shutdown_event=shutdown_event,
    )
    course_manager = CourseManager(canvas_client, config)
    report_generator = ReportGenerator(file_organizer)

    # Check for new courses
    all_courses = course_manager.get_active_courses()
    new_courses = course_manager.detect_new_courses(all_courses)

    if new_courses:
        logger.info(f"Detected {len(new_courses)} new courses")
        # TODO: Handle new courses (interactive vs cron mode)

    # Get synced courses
    synced_courses = course_manager.get_synced_courses(all_courses)
    logger.info(f"Syncing {len(synced_courses)} courses")

    # Track downloads and skips
    new_downloads = []
    updated_downloads = []
    failed_downloads = []
    total_files_checked = 0

    # Process each course
    for course in synced_courses:
        if shutdown_event.is_set():
            logger.info("Shutdown requested, stopping sync early...")
            break

        logger.info(f"\nProcessing course: {course['code']} - {course['name']}")

        # Get course directory
        course_dir = file_organizer.get_course_directory(
            course["code"], course["name"], course["term"]
        )

        # Get files from Canvas
        canvas_files = canvas_client.get_course_files(course["id"])
        logger.info(f"Found {len(canvas_files)} files on Canvas")
        total_files_checked += len(canvas_files)

        # Process each file
        download_tasks = []

        for file_metadata in canvas_files:
            file_id = str(file_metadata["id"])

            # Check if already downloaded
            existing_file = metadata_db.get_downloaded_file(file_id)

            if existing_file:
                # Check if Canvas file is newer
                canvas_modified = file_metadata["modified_at"]
                local_download = datetime.fromisoformat(existing_file["download_date"])

                # Ensure both datetimes are timezone-aware for comparison
                if local_download.tzinfo is None:
                    local_download = local_download.replace(tzinfo=timezone.utc)

                if canvas_modified <= local_download:
                    # File is up to date, skip
                    metadata_db.update_downloaded_file_seen(file_id)
                    continue

                # File needs update
                is_update = True
                logger.info(f"File needs update: {file_metadata['name']}")
            else:
                is_update = False

            # Apply filters
            should_download, reason = filter_engine.should_download(file_metadata)

            if not should_download:
                # Check if this is a new skipped file
                existing_skip = metadata_db.get_skipped_file(file_id)

                if existing_skip:
                    # Already know about this skipped file
                    metadata_db.update_skipped_file_seen(file_id)
                else:
                    # New skipped file - add to DB for email notification
                    folder_path = canvas_client.get_folder_path(
                        course["id"], file_metadata.get("folder_id")
                    )

                    metadata_db.add_skipped_file(
                        file_id=file_id,
                        course_id=str(course["id"]),
                        course_name=f"{course['code']} - {course['name']}",
                        filename=file_metadata["name"],
                        folder_path=folder_path,
                        size_bytes=file_metadata["size"],
                        canvas_url=file_metadata["canvas_url"],
                        skip_reason=reason,
                    )
                    logger.debug(
                        f"New skipped file: {file_metadata['name']} - {reason}"
                    )

                continue

            # File should be downloaded
            folder_path = canvas_client.get_folder_path(
                course["id"], file_metadata.get("folder_id")
            )

            destination = file_organizer.get_file_path(
                course_dir, folder_path, file_metadata["name"]
            )

            task = DownloadTask(
                file_id=file_id,
                file_url=file_metadata["url"],
                destination=destination,
                filename=file_metadata["name"],
                size_bytes=file_metadata["size"],
                course_name=f"{course['code']} - {course['name']}",
                is_update=is_update,
            )
            download_tasks.append(task)

        # Download files for this course
        if download_tasks and not dry_run:
            logger.info(f"Downloading {len(download_tasks)} files...")
            successful, failed = download_manager.download_files(download_tasks)

            # Update database
            for result in successful:
                task = result.task
                metadata_db.add_downloaded_file(
                    file_id=task.file_id,
                    course_id=str(course["id"]),
                    course_name=task.course_name,
                    filename=task.filename,
                    local_path=str(task.destination),
                    size_bytes=task.size_bytes,
                    canvas_modified_date=datetime.now(),
                )

                if task.is_update:
                    updated_downloads.append(result)
                else:
                    new_downloads.append(result)

            failed_downloads.extend(failed)

        elif download_tasks:
            logger.info(f"[DRY RUN] Would download {len(download_tasks)} files")

        # Fetch announcements for this course
        course_name_full = f"{course['code']} - {course['name']}"
        announcements = canvas_client.get_course_announcements(course["id"])
        for ann in announcements:
            ann_id = str(ann["id"])
            existing = metadata_db.get_announcement(ann_id)
            if not existing:
                metadata_db.add_announcement(
                    announcement_id=ann_id,
                    course_id=str(course["id"]),
                    course_name=course_name_full,
                    title=ann["title"],
                    message=ann["message"],
                    author=ann["author"],
                    posted_at=ann["posted_at"],
                    canvas_url=ann["canvas_url"],
                )
            else:
                metadata_db.update_announcement_seen(ann_id)

        # Fetch assignments for this course
        assignments = canvas_client.get_course_assignments(course["id"])
        now = datetime.now(timezone.utc)
        for assign in assignments:
            assign_id = str(assign["id"])

            # Only track upcoming assignments (future due date or no due date)
            due_at = assign["due_at"]
            if due_at is not None and due_at < now:
                continue  # Skip past assignments

            existing = metadata_db.get_assignment(assign_id)
            if not existing:
                metadata_db.add_assignment(
                    assignment_id=assign_id,
                    course_id=str(course["id"]),
                    course_name=course_name_full,
                    name=assign["name"],
                    description=assign["description"],
                    due_at=due_at,
                    points_possible=assign["points_possible"],
                    submission_types=assign["submission_types"],
                    canvas_url=assign["canvas_url"],
                )

                # Download assignment attachments
                for attachment in assign.get("attachments", []):
                    if not attachment.get("url"):
                        continue

                    att_id = str(attachment["id"])
                    # Check if we already have this file
                    if metadata_db.get_downloaded_file(att_id):
                        continue

                    # Apply filters to attachment
                    att_metadata = {
                        "id": attachment["id"],
                        "name": attachment["name"],
                        "size": attachment["size"],
                    }
                    should_download, reason = filter_engine.should_download(
                        att_metadata
                    )

                    if should_download:
                        destination = file_organizer.get_file_path(
                            course_dir, "Assignments", attachment["name"]
                        )
                        task = DownloadTask(
                            file_id=att_id,
                            file_url=attachment["url"],
                            destination=destination,
                            filename=attachment["name"],
                            size_bytes=attachment["size"],
                            course_name=course_name_full,
                            is_update=False,
                        )
                        # Add to download queue - process after files
                        if not dry_run:
                            results = download_manager.download_files([task])
                            successful, failed = results
                            for result in successful:
                                metadata_db.add_downloaded_file(
                                    file_id=task.file_id,
                                    course_id=str(course["id"]),
                                    course_name=task.course_name,
                                    filename=task.filename,
                                    local_path=str(task.destination),
                                    size_bytes=task.size_bytes,
                                    canvas_modified_date=datetime.now(),
                                )
                                new_downloads.append(result)
                            failed_downloads.extend(failed)
            else:
                metadata_db.update_assignment_seen(assign_id)

    # Get new skipped files for report
    new_skipped_files = metadata_db.get_new_skipped_files()

    # Get new announcements and upcoming assignments for report
    new_announcements = metadata_db.get_new_announcements()
    upcoming_assignments = metadata_db.get_upcoming_assignments()

    # Generate report
    report_data = report_generator.generate_report(
        new_downloads=new_downloads,
        updated_downloads=updated_downloads,
        skipped_files=new_skipped_files,
        failed_downloads=failed_downloads,
        new_courses=new_courses,
        new_announcements=new_announcements,
        upcoming_assignments=upcoming_assignments,
    )

    # Log summary
    logger.info("\n" + "=" * 60)
    logger.info("Sync Complete")
    logger.info("=" * 60)
    logger.info(f"Files checked: {total_files_checked}")
    logger.info(f"New files downloaded: {len(new_downloads)}")
    logger.info(f"Files updated: {len(updated_downloads)}")
    logger.info(f"New files skipped: {len(new_skipped_files)}")
    logger.info(f"Failed downloads: {len(failed_downloads)}")
    logger.info(f"New announcements: {len(new_announcements)}")
    logger.info(f"Upcoming assignments: {len(upcoming_assignments)}")

    # Send email notification
    if send_email and config.get("notification.email.enabled") and not dry_run:
        logger.info("\nSending email notification...")
        email_notifier = EmailNotifier(config)
        if email_notifier.send_report(report_data):
            # Mark skipped files, announcements, and assignments as notified
            metadata_db.mark_skipped_files_notified()
            metadata_db.mark_announcements_notified()
            metadata_db.mark_assignments_notified()
        else:
            logger.error("Failed to send email notification")

    # Add run history
    if not dry_run:
        total_size = sum(r.task.size_bytes for r in new_downloads + updated_downloads)
        metadata_db.add_run_history(
            files_downloaded=len(new_downloads),
            files_updated=len(updated_downloads),
            files_skipped=len(new_skipped_files),
            total_size_bytes=total_size,
            success=len(failed_downloads) == 0,
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Canvas File Scraper")

    # Setup & configuration
    parser.add_argument(
        "--setup", action="store_true", help="Run first-time setup wizard"
    )
    parser.add_argument(
        "--reselect-courses", action="store_true", help="Re-run course selection"
    )
    parser.add_argument(
        "--add-courses",
        action="store_true",
        help="Add new courses to existing selection",
    )
    parser.add_argument(
        "--remove-courses", action="store_true", help="Remove courses from sync list"
    )

    # Execution modes
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview what would be downloaded"
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Disable email notification for this run",
    )

    # Testing & utilities
    parser.add_argument("--test-email", action="store_true", help="Send test email")
    parser.add_argument(
        "--list-courses", action="store_true", help="List all active courses"
    )

    # Logging
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Load configuration
    config = Config()

    # Handle setup wizard
    if args.setup:
        setup_wizard(config)
        return


    # Handle other commands
    if args.test_email:
        email_notifier = EmailNotifier(config)
        if email_notifier.send_test_email():
            print("✓ Test email sent successfully")
        else:
            print("✗ Failed to send test email")
        return

    # Check if configured
    if not config.is_configured():
        print("Canvas Scraper is not configured yet. Starting setup wizard...")
        setup_wizard(config)


        if not config.is_configured():
            return

    # Run sync
    try:
        run_sync(config, dry_run=args.dry_run, send_email=not args.no_email)
    except KeyboardInterrupt:
        logger.info("\nSync interrupted by user")
        shutdown_event.set()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Sync failed with error: {e}", exc_info=True)
        sys.exit(1)

    if shutdown_event.is_set():
        logger.info("Sync ended early due to shutdown signal")
        sys.exit(0)


if __name__ == "__main__":
    main()
