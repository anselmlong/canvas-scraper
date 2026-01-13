"""File organizer for creating local directory structure."""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any


logger = logging.getLogger(__name__)


class FileOrganizer:
    """Organizes downloaded files in local directory structure."""

    def __init__(self, base_path: Path):
        """Initialize file organizer.

        Args:
            base_path: Base directory for downloaded files
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized file organizer at {self.base_path}")

    def get_course_directory(
        self, course_code: str, course_name: str, term: str
    ) -> Path:
        """Get or create directory for a course.

        Args:
            course_code: Course code (e.g., "CS 101")
            course_name: Course name
            term: Course term/semester

        Returns:
            Path to course directory
        """
        # Create safe directory name
        # Format: "CS 101 - Introduction to Computer Science (Fall 2024)"
        dir_name = f"{course_code} - {course_name} ({term})"
        dir_name = self._sanitize_filename(dir_name)

        course_dir = self.base_path / dir_name
        course_dir.mkdir(parents=True, exist_ok=True)

        return course_dir

    def get_file_path(self, course_dir: Path, folder_path: str, filename: str) -> Path:
        """Get full local path for a file.

        Args:
            course_dir: Course directory path
            folder_path: Canvas folder path (e.g., "Lectures/Week 1")
            filename: Original filename

        Returns:
            Full local file path
        """
        # Sanitize folder path
        if folder_path:
            # Split path and sanitize each component
            parts = folder_path.split("/")
            safe_parts = [self._sanitize_filename(part) for part in parts if part]
            folder_path_safe = os.path.join(*safe_parts)
        else:
            folder_path_safe = ""

        # Create full directory path
        file_dir = course_dir / folder_path_safe if folder_path_safe else course_dir
        file_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)

        # Handle filename conflicts
        file_path = file_dir / safe_filename
        if file_path.exists():
            file_path = self._get_unique_filename(file_dir, safe_filename)

        return file_path

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem.

        Args:
            filename: Original filename

        Returns:
            Safe filename
        """
        # Replace invalid characters with underscores
        # Invalid: / \ : * ? " < > |
        filename = re.sub(r'[/\\:*?"<>|]', "_", filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip(". ")

        # Limit length (leave room for extensions and counters)
        max_length = 200
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[: max_length - len(ext)] + ext

        return filename or "unnamed"

    def _get_unique_filename(self, directory: Path, filename: str) -> Path:
        """Get unique filename if file already exists.

        Args:
            directory: Directory path
            filename: Desired filename

        Returns:
            Unique file path
        """
        name, ext = os.path.splitext(filename)
        counter = 1

        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_path = directory / new_filename
            if not new_path.exists():
                return new_path
            counter += 1

    def get_relative_path(self, full_path: Path) -> str:
        """Get path relative to base directory.

        Args:
            full_path: Full file path

        Returns:
            Relative path string
        """
        try:
            return str(full_path.relative_to(self.base_path))
        except ValueError:
            return str(full_path)

    def delete_course_files(self, course_code: str, course_name: str, term: str):
        """Delete all files for a course.

        Args:
            course_code: Course code
            course_name: Course name
            term: Course term
        """
        course_dir = self.get_course_directory(course_code, course_name, term)

        if course_dir.exists():
            import shutil

            shutil.rmtree(course_dir)
            logger.info(f"Deleted course directory: {course_dir}")

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
