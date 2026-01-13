"""Canvas API client for interacting with Canvas LMS."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from canvasapi import Canvas
from canvasapi.course import Course
from canvasapi.file import File
from canvasapi.folder import Folder
from canvasapi.exceptions import CanvasException


logger = logging.getLogger(__name__)


class CanvasClient:
    """Wrapper for Canvas API interactions."""

    def __init__(self, base_url: str, api_token: str):
        """Initialize Canvas client.

        Args:
            base_url: Canvas instance URL (e.g., https://canvas.university.edu)
            api_token: Canvas API access token
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.canvas = Canvas(self.base_url, api_token)
        logger.info(f"Initialized Canvas client for {self.base_url}")

    def test_connection(self) -> tuple[bool, str]:
        """Test connection to Canvas API.

        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.canvas.get_current_user()
            return True, f"Connected as {user.name}"
        except CanvasException as e:
            return False, f"Canvas API error: {str(e)}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_active_courses(self) -> List[Dict[str, Any]]:
        """Get all active courses for the current user.

        Returns:
            List of course dictionaries with keys: id, code, name, term
        """
        logger.info("Fetching active courses...")
        courses = []

        try:
            # Get courses where user is a student
            for course in self.canvas.get_courses(
                enrollment_state="active", enrollment_type="student"
            ):
                # Skip courses without a course code
                if not hasattr(course, "course_code"):
                    continue

                course_dict = {
                    "id": course.id,
                    "code": course.course_code,
                    "name": course.name,
                    "term": self._get_course_term(course),
                }
                courses.append(course_dict)
                logger.debug(
                    f"Found course: {course_dict['code']} - {course_dict['name']}"
                )

            logger.info(f"Found {len(courses)} active courses")
            return courses

        except CanvasException as e:
            logger.error(f"Error fetching courses: {e}")
            raise

    def _get_course_term(self, course: Course) -> str:
        """Extract term/semester from course.

        Args:
            course: Canvas course object

        Returns:
            Term string (e.g., "Fall 2024")
        """
        if hasattr(course, "term") and hasattr(course.term, "name"):
            return course.term.name
        elif hasattr(course, "enrollment_term_id"):
            try:
                term = self.canvas.get_enrollment_term(course.enrollment_term_id)
                return term.name
            except:
                pass

        # Fallback to current year
        return f"Term {datetime.now().year}"

    def get_course(self, course_id: int) -> Optional[Course]:
        """Get a specific course by ID.

        Args:
            course_id: Canvas course ID

        Returns:
            Course object or None if not found
        """
        try:
            return self.canvas.get_course(course_id)
        except CanvasException as e:
            logger.error(f"Error fetching course {course_id}: {e}")
            return None

    def get_course_folders(self, course_id: int) -> List[Dict[str, Any]]:
        """Get folder structure for a course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of folder dictionaries with keys: id, name, full_path, parent_id
        """
        logger.info(f"Fetching folders for course {course_id}...")
        folders = []

        try:
            course = self.canvas.get_course(course_id)

            for folder in course.get_folders():
                folder_dict = {
                    "id": folder.id,
                    "name": folder.name,
                    "full_path": folder.full_name,
                    "parent_id": folder.parent_folder_id
                    if hasattr(folder, "parent_folder_id")
                    else None,
                }
                folders.append(folder_dict)
                logger.debug(f"Found folder: {folder_dict['full_path']}")

            logger.info(f"Found {len(folders)} folders")
            return folders

        except CanvasException as e:
            logger.error(f"Error fetching folders for course {course_id}: {e}")
            return []

    def get_course_files(self, course_id: int) -> List[Dict[str, Any]]:
        """Get all files for a course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of file dictionaries with keys: id, name, size, modified_at,
            url, folder_id, mime_type
        """
        logger.info(f"Fetching files for course {course_id}...")
        files = []

        try:
            course = self.canvas.get_course(course_id)

            for file in course.get_files():
                file_dict = {
                    "id": file.id,
                    "name": file.display_name,
                    "filename": file.filename,
                    "size": file.size,
                    "modified_at": self._parse_datetime(file.modified_at),
                    "url": file.url,
                    "folder_id": file.folder_id if hasattr(file, "folder_id") else None,
                    "mime_type": file.mime_class
                    if hasattr(file, "mime_class")
                    else "unknown",
                    "canvas_url": f"{self.base_url}/courses/{course_id}/files/{file.id}",
                }
                files.append(file_dict)
                logger.debug(
                    f"Found file: {file_dict['name']} ({self._format_size(file_dict['size'])})"
                )

            logger.info(f"Found {len(files)} files")
            return files

        except CanvasException as e:
            logger.error(f"Error fetching files for course {course_id}: {e}")
            return []

    def get_folder_path(self, course_id: int, folder_id: Optional[int]) -> str:
        """Get the full path of a folder.

        Args:
            course_id: Canvas course ID
            folder_id: Canvas folder ID (None for root)

        Returns:
            Folder path (e.g., "course files/Lectures/Week 1")
        """
        if folder_id is None:
            return ""

        try:
            course = self.canvas.get_course(course_id)
            folder = course.get_folder(folder_id)

            # Remove "course files/" prefix if present
            path = folder.full_name
            if path.startswith("course files/"):
                path = path[13:]  # len('course files/')

            return path

        except CanvasException as e:
            logger.warning(f"Error getting folder path for folder {folder_id}: {e}")
            return ""

    def download_file(self, file_url: str, destination: str) -> bool:
        """Download a file from Canvas.

        Args:
            file_url: Canvas file download URL
            destination: Local file path to save to

        Returns:
            True if successful, False otherwise
        """
        try:
            import requests

            # Canvas file URLs are authenticated with the API token
            response = requests.get(
                file_url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                stream=True,
                timeout=300,  # 5 minute timeout for large files
            )
            response.raise_for_status()

            # Write file in chunks
            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return True

        except Exception as e:
            logger.error(f"Error downloading file from {file_url}: {e}")
            return False

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse Canvas datetime string.

        Args:
            date_str: ISO format datetime string

        Returns:
            datetime object
        """
        try:
            # Canvas uses ISO 8601 format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.now()

    def _format_size(self, size_bytes: int) -> str:
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
