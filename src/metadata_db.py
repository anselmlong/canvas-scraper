"""SQLite database for tracking downloaded and skipped files."""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager


logger = logging.getLogger(__name__)


class MetadataDB:
    """SQLite database manager for file metadata."""

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_schema()
        logger.info(f"Initialized metadata database at {db_path}")

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Downloaded files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloaded_files (
                    file_id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    canvas_modified_date TEXT NOT NULL,
                    download_date TEXT NOT NULL,
                    last_seen_date TEXT NOT NULL,
                    checksum TEXT
                )
            """)

            # Skipped files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skipped_files (
                    file_id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    folder_path TEXT,
                    size_bytes INTEGER NOT NULL,
                    canvas_url TEXT NOT NULL,
                    skip_reason TEXT NOT NULL,
                    first_seen_date TEXT NOT NULL,
                    last_seen_date TEXT NOT NULL,
                    notified INTEGER DEFAULT 0
                )
            """)

            # Run history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date TEXT NOT NULL,
                    files_downloaded INTEGER DEFAULT 0,
                    files_updated INTEGER DEFAULT 0,
                    files_skipped INTEGER DEFAULT 0,
                    total_size_bytes INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 1,
                    error_message TEXT
                )
            """)

            # Announcements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS announcements (
                    id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT,
                    author TEXT,
                    posted_at TEXT,
                    canvas_url TEXT NOT NULL,
                    first_seen_date TEXT NOT NULL,
                    last_seen_date TEXT NOT NULL,
                    notified INTEGER DEFAULT 0
                )
            """)

            # Assignments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    due_at TEXT,
                    points_possible REAL,
                    submission_types TEXT,
                    canvas_url TEXT NOT NULL,
                    first_seen_date TEXT NOT NULL,
                    last_seen_date TEXT NOT NULL,
                    notified INTEGER DEFAULT 0
                )
            """)

            conn.commit()
            logger.debug("Database schema initialized")

    # Downloaded files methods

    def get_downloaded_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get downloaded file record by ID.

        Args:
            file_id: Canvas file ID

        Returns:
            File record dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM downloaded_files WHERE file_id = ?", (file_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_downloaded_file(
        self,
        file_id: str,
        course_id: str,
        course_name: str,
        filename: str,
        local_path: str,
        size_bytes: int,
        canvas_modified_date: datetime,
        checksum: Optional[str] = None,
    ):
        """Add a downloaded file record.

        Args:
            file_id: Canvas file ID
            course_id: Canvas course ID
            course_name: Course name
            filename: Original filename
            local_path: Local file path
            size_bytes: File size in bytes
            canvas_modified_date: Last modified date on Canvas
            checksum: Optional file checksum
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO downloaded_files
                (file_id, course_id, course_name, filename, local_path, size_bytes,
                 canvas_modified_date, download_date, last_seen_date, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    file_id,
                    course_id,
                    course_name,
                    filename,
                    local_path,
                    size_bytes,
                    canvas_modified_date.isoformat(),
                    now,
                    now,
                    checksum,
                ),
            )

        logger.debug(f"Added downloaded file record: {filename}")

    def update_downloaded_file_seen(self, file_id: str):
        """Update last_seen_date for a downloaded file.

        Args:
            file_id: Canvas file ID
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE downloaded_files SET last_seen_date = ? WHERE file_id = ?",
                (now, file_id),
            )

    def delete_downloaded_file(self, file_id: str):
        """Delete a downloaded file record.

        Args:
            file_id: Canvas file ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloaded_files WHERE file_id = ?", (file_id,))

    def get_downloaded_files_by_course(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all downloaded files for a course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of file record dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM downloaded_files WHERE course_id = ?", (course_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # Skipped files methods

    def get_skipped_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get skipped file record by ID.

        Args:
            file_id: Canvas file ID

        Returns:
            File record dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM skipped_files WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_skipped_file(
        self,
        file_id: str,
        course_id: str,
        course_name: str,
        filename: str,
        folder_path: str,
        size_bytes: int,
        canvas_url: str,
        skip_reason: str,
    ):
        """Add a skipped file record.

        Args:
            file_id: Canvas file ID
            course_id: Canvas course ID
            course_name: Course name
            filename: Original filename
            folder_path: Folder path on Canvas
            size_bytes: File size in bytes
            canvas_url: Direct URL to file on Canvas
            skip_reason: Reason for skipping
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO skipped_files
                (file_id, course_id, course_name, filename, folder_path, size_bytes,
                 canvas_url, skip_reason, first_seen_date, last_seen_date, notified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
                (
                    file_id,
                    course_id,
                    course_name,
                    filename,
                    folder_path,
                    size_bytes,
                    canvas_url,
                    skip_reason,
                    now,
                    now,
                ),
            )

        logger.debug(f"Added skipped file record: {filename} - {skip_reason}")

    def update_skipped_file_seen(self, file_id: str):
        """Update last_seen_date for a skipped file.

        Args:
            file_id: Canvas file ID
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE skipped_files SET last_seen_date = ? WHERE file_id = ?",
                (now, file_id),
            )

    def get_new_skipped_files(self) -> List[Dict[str, Any]]:
        """Get skipped files that haven't been notified about.

        Returns:
            List of skipped file records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM skipped_files WHERE notified = 0 ORDER BY course_name, filename"
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_skipped_files_notified(self):
        """Mark all new skipped files as notified."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE skipped_files SET notified = 1 WHERE notified = 0")

        logger.debug("Marked skipped files as notified")

    def delete_skipped_file(self, file_id: str):
        """Delete a skipped file record.

        Args:
            file_id: Canvas file ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM skipped_files WHERE file_id = ?", (file_id,))

    # Run history methods

    def add_run_history(
        self,
        files_downloaded: int,
        files_updated: int,
        files_skipped: int,
        total_size_bytes: int,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> int:
        """Add a run history record.

        Args:
            files_downloaded: Number of new files downloaded
            files_updated: Number of files updated
            files_skipped: Number of files skipped
            total_size_bytes: Total bytes downloaded
            success: Whether run was successful
            error_message: Error message if unsuccessful

        Returns:
            Run ID
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO run_history
                (run_date, files_downloaded, files_updated, files_skipped,
                 total_size_bytes, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    now,
                    files_downloaded,
                    files_updated,
                    files_skipped,
                    total_size_bytes,
                    1 if success else 0,
                    error_message,
                ),
            )

            run_id = cursor.lastrowid

        logger.info(f"Added run history record (ID: {run_id})")
        return run_id

    def get_last_run(self) -> Optional[Dict[str, Any]]:
        """Get the most recent run history record.

        Returns:
            Run history dict or None if no runs
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM run_history ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent run history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of run history dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM run_history ORDER BY id DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # Announcement methods

    def get_announcement(self, announcement_id: str) -> Optional[Dict[str, Any]]:
        """Get announcement record by ID.

        Args:
            announcement_id: Canvas announcement ID

        Returns:
            Announcement record dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM announcements WHERE id = ?", (announcement_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_announcement(
        self,
        announcement_id: str,
        course_id: str,
        course_name: str,
        title: str,
        message: str,
        author: str,
        posted_at: Optional[datetime],
        canvas_url: str,
    ):
        """Add an announcement record.

        Args:
            announcement_id: Canvas announcement ID
            course_id: Canvas course ID
            course_name: Course name
            title: Announcement title
            message: Announcement message (HTML)
            author: Author name
            posted_at: Date posted
            canvas_url: Direct URL to announcement
        """
        now = datetime.now().isoformat()
        posted_at_str = posted_at.isoformat() if posted_at else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO announcements
                (id, course_id, course_name, title, message, author, posted_at,
                 canvas_url, first_seen_date, last_seen_date, notified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
                (
                    announcement_id,
                    course_id,
                    course_name,
                    title,
                    message,
                    author,
                    posted_at_str,
                    canvas_url,
                    now,
                    now,
                ),
            )

        logger.debug(f"Added announcement record: {title}")

    def update_announcement_seen(self, announcement_id: str):
        """Update last_seen_date for an announcement.

        Args:
            announcement_id: Canvas announcement ID
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE announcements SET last_seen_date = ? WHERE id = ?",
                (now, announcement_id),
            )

    def get_new_announcements(self) -> List[Dict[str, Any]]:
        """Get announcements that haven't been notified about.

        Returns:
            List of announcement records ordered by course and date
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM announcements
                   WHERE notified = 0
                   ORDER BY course_name, posted_at DESC"""
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_announcements_notified(self):
        """Mark all new announcements as notified."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE announcements SET notified = 1 WHERE notified = 0")

        logger.debug("Marked announcements as notified")

    # Assignment methods

    def get_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Get assignment record by ID.

        Args:
            assignment_id: Canvas assignment ID

        Returns:
            Assignment record dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_assignment(
        self,
        assignment_id: str,
        course_id: str,
        course_name: str,
        name: str,
        description: str,
        due_at: Optional[datetime],
        points_possible: Optional[float],
        submission_types: List[str],
        canvas_url: str,
    ):
        """Add an assignment record.

        Args:
            assignment_id: Canvas assignment ID
            course_id: Canvas course ID
            course_name: Course name
            name: Assignment name
            description: Assignment description (HTML)
            due_at: Due date
            points_possible: Points possible
            submission_types: List of submission types
            canvas_url: Direct URL to assignment
        """
        now = datetime.now().isoformat()
        due_at_str = due_at.isoformat() if due_at else None
        submission_types_str = json.dumps(submission_types)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO assignments
                (id, course_id, course_name, name, description, due_at,
                 points_possible, submission_types, canvas_url,
                 first_seen_date, last_seen_date, notified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
                (
                    assignment_id,
                    course_id,
                    course_name,
                    name,
                    description,
                    due_at_str,
                    points_possible,
                    submission_types_str,
                    canvas_url,
                    now,
                    now,
                ),
            )

        logger.debug(f"Added assignment record: {name}")

    def update_assignment_seen(self, assignment_id: str):
        """Update last_seen_date for an assignment.

        Args:
            assignment_id: Canvas assignment ID
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE assignments SET last_seen_date = ? WHERE id = ?",
                (now, assignment_id),
            )

    def get_new_assignments(self) -> List[Dict[str, Any]]:
        """Get assignments that haven't been notified about.

        Returns:
            List of assignment records ordered by course and due date
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM assignments
                   WHERE notified = 0
                   ORDER BY course_name, due_at ASC"""
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_assignments(self) -> List[Dict[str, Any]]:
        """Get assignments with future due dates that haven't been notified.

        Returns:
            List of upcoming assignment records
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM assignments
                   WHERE notified = 0
                   AND (due_at IS NULL OR due_at >= ?)
                   ORDER BY course_name, due_at ASC""",
                (now,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_assignments_notified(self):
        """Mark all new assignments as notified."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE assignments SET notified = 1 WHERE notified = 0")

        logger.debug("Marked assignments as notified")
