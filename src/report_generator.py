"""Report generator for creating download summaries."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates download reports for email notifications."""

    def __init__(self, file_organizer):
        """Initialize report generator.

        Args:
            file_organizer: FileOrganizer instance
        """
        self.file_organizer = file_organizer

    def generate_report(
        self,
        new_downloads: List[Any],
        updated_downloads: List[Any],
        skipped_files: List[Dict[str, Any]],
        failed_downloads: List[Any],
        new_courses: List[Dict[str, Any]],
        new_announcements: Optional[List[Dict[str, Any]]] = None,
        upcoming_assignments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive download report.

        Args:
            new_downloads: List of DownloadResult for new files
            updated_downloads: List of DownloadResult for updated files
            skipped_files: List of skipped file records from DB
            failed_downloads: List of DownloadResult for failed downloads
            new_courses: List of newly detected courses
            new_announcements: List of new announcement records from DB
            upcoming_assignments: List of upcoming assignment records from DB

        Returns:
            Report data dict for email template
        """
        new_announcements = new_announcements if new_announcements is not None else []
        upcoming_assignments = (
            upcoming_assignments if upcoming_assignments is not None else []
        )

        # Group files by course
        new_files_by_course = self._group_by_course(new_downloads)
        updated_files_by_course = self._group_by_course(updated_downloads)
        skipped_files_by_course = self._group_skipped_by_course(skipped_files)
        failed_files_by_course = self._group_failed_by_course(failed_downloads)

        # Group announcements and assignments by course
        announcements_by_course = self._group_announcements_by_course(new_announcements)
        assignments_by_course = self._group_assignments_by_course(upcoming_assignments)

        # Ignore this because we don't want to show new courses in the report
        new_courses = []

        # Calculate totals
        total_size_bytes = sum(
            d.task.size_bytes for d in new_downloads + updated_downloads
        )

        report = {
            "timestamp": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            "new_count": len(new_downloads),
            "updated_count": len(updated_downloads),
            "skipped_count": len(skipped_files),
            "failed_count": len(failed_downloads),
            "total_size_mb": f"{total_size_bytes / 1024 / 1024:.1f}",
            "new_files": new_files_by_course,
            "updated_files": updated_files_by_course,
            "skipped_files": skipped_files_by_course,
            "failed_files": failed_files_by_course,
            "new_courses": new_courses,
            "next_run_time": self._get_next_run_time(),
            # New announcement and assignment data
            "new_announcements": announcements_by_course,
            "upcoming_assignments": assignments_by_course,
            "announcement_count": len(new_announcements),
            "assignment_count": len(upcoming_assignments),
        }

        logger.info(
            f"Generated report: {len(new_downloads)} new, {len(updated_downloads)} updated"
        )

        return report

    def _group_by_course(
        self, download_results: List[Any]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Group download results by course.

        Args:
            download_results: List of DownloadResult objects

        Returns:
            Dict mapping course name to list of file info dicts
        """
        grouped = defaultdict(list)

        for result in download_results:
            task = result.task
            file_info = {
                "relative_path": self.file_organizer.get_relative_path(
                    task.destination
                ),
                "size": self.file_organizer.format_size(task.size_bytes),
                "filename": task.filename,
            }
            grouped[task.course_name].append(file_info)

        return dict(grouped)

    def _group_skipped_by_course(
        self, skipped_files: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Group skipped files by course.

        Args:
            skipped_files: List of skipped file records

        Returns:
            Dict mapping course name to list of file info dicts
        """
        grouped = defaultdict(list)

        for file_record in skipped_files:
            file_info = {
                "filename": file_record["filename"],
                "size": self.file_organizer.format_size(file_record["size_bytes"]),
                "folder_path": file_record["folder_path"] or "Root",
                "reason": file_record["skip_reason"],
                "canvas_url": file_record["canvas_url"],
            }
            grouped[file_record["course_name"]].append(file_info)

        return dict(grouped)

    def _group_failed_by_course(
        self, failed_results: List[Any]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Group failed downloads by course.

        Args:
            failed_results: List of DownloadResult objects for failures

        Returns:
            Dict mapping course name to list of file info dicts
        """
        grouped = defaultdict(list)

        for result in failed_results:
            task = result.task
            file_info = {"filename": task.filename, "error": result.error_message}
            grouped[task.course_name].append(file_info)

        return dict(grouped)

    def _get_next_run_time(self) -> str:
        """Get formatted next run time.

        Returns:
            Formatted next run time string
        """
        # Assume daily at noon
        now = datetime.now()
        next_run = now.replace(hour=12, minute=0, second=0, microsecond=0)

        # If already past noon today, schedule for tomorrow
        if now.hour >= 12:
            next_run += timedelta(days=1)

        return next_run.strftime("%B %d, %Y at %I:%M %p")

    def _group_announcements_by_course(
        self, announcements: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Group announcements by course.

        Args:
            announcements: List of announcement records from DB

        Returns:
            Dict mapping course name to list of announcement info dicts
        """
        grouped = defaultdict(list)

        for ann in announcements:
            # Format posted date
            posted_at = ann.get("posted_at")
            if posted_at:
                try:
                    dt = datetime.fromisoformat(posted_at)
                    posted_at_str = dt.strftime("%B %d, %Y at %I:%M %p")
                except (ValueError, TypeError):
                    posted_at_str = posted_at
            else:
                posted_at_str = "Unknown date"

            ann_info = {
                "title": ann["title"],
                "message": ann.get("message", ""),
                "author": ann.get("author", "Unknown"),
                "posted_at": posted_at_str,
                "canvas_url": ann["canvas_url"],
            }
            grouped[ann["course_name"]].append(ann_info)

        return dict(grouped)

    def _group_assignments_by_course(
        self, assignments: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Group assignments by course.

        Args:
            assignments: List of assignment records from DB

        Returns:
            Dict mapping course name to list of assignment info dicts
        """
        grouped = defaultdict(list)

        for assign in assignments:
            # Format due date
            due_at = assign.get("due_at")
            if due_at:
                try:
                    dt = datetime.fromisoformat(due_at)
                    due_at_str = dt.strftime("%B %d, %Y at %I:%M %p")
                except (ValueError, TypeError):
                    due_at_str = due_at
            else:
                due_at_str = "No due date"

            # Format points
            points = assign.get("points_possible")
            points_str = f"{points:.0f}" if points else None

            assign_info = {
                "name": assign["name"],
                "description": assign.get("description", ""),
                "due_at": due_at_str,
                "points": points_str,
                "canvas_url": assign["canvas_url"],
            }
            grouped[assign["course_name"]].append(assign_info)

        return dict(grouped)
