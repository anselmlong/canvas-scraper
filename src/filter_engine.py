"""File filtering engine for determining which files to download."""

import os
import logging
from typing import Dict, Any, Tuple


logger = logging.getLogger(__name__)


class FilterEngine:
    """Determines which files should be downloaded based on filters."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize filter engine with configuration.

        Args:
            config: Filter configuration dict
        """
        self.max_size_bytes = config.get("max_file_size_mb", 50) * 1024 * 1024
        self.blacklist_exts = set(
            ext.lower() for ext in config.get("extension_blacklist", [])
        )
        self.skip_patterns = [
            pattern.lower() for pattern in config.get("name_patterns_to_skip", [])
        ]
        self.pdf_max_size = config.get("pdf_max_size_mb", 30) * 1024 * 1024

        logger.info(
            f"Initialized filter engine (max size: {config.get('max_file_size_mb')}MB)"
        )
        logger.debug(f"Blacklisted extensions: {', '.join(self.blacklist_exts)}")

    def should_download(self, file_metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if a file should be downloaded.

        Args:
            file_metadata: File metadata dict with keys: name, size, mime_type

        Returns:
            Tuple of (should_download: bool, reason: str)
        """
        filename = file_metadata.get("name", "")
        size_bytes = file_metadata.get("size", 0)

        # Get file extension
        ext = os.path.splitext(filename)[1].lower()

        # Check size limit
        if size_bytes > self.max_size_bytes:
            size_mb = size_bytes / 1024 / 1024
            max_mb = self.max_size_bytes / 1024 / 1024
            return False, f"Exceeds size limit ({size_mb:.1f} MB > {max_mb:.0f} MB)"

        # Check extension blacklist
        if ext in self.blacklist_exts:
            file_type = self._get_file_type_name(ext)
            return False, f"{file_type} ({ext}) - blacklisted file type"

        # Check name patterns
        filename_lower = filename.lower()
        for pattern in self.skip_patterns:
            if pattern in filename_lower:
                return False, f"Filename matches skip pattern: '{pattern}'"

        # Smart PDF rule - assume large PDFs are textbooks
        if ext == ".pdf" and size_bytes > self.pdf_max_size:
            size_mb = size_bytes / 1024 / 1024
            return False, f"Large PDF ({size_mb:.1f} MB) - likely textbook"

        # File passes all filters
        return True, "Approved"

    def _get_file_type_name(self, ext: str) -> str:
        """Get human-readable file type name.

        Args:
            ext: File extension (e.g., '.mp4')

        Returns:
            Human-readable type name
        """
        video_exts = {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".webm",
            ".flv",
            ".wmv",
            ".m4v",
            ".mpeg",
            ".mpg",
        }
        ebook_exts = {".epub", ".mobi"}

        if ext in video_exts:
            return "Video file"
        elif ext in ebook_exts:
            return "Ebook"
        else:
            return "File"

    def get_stats(self) -> Dict[str, Any]:
        """Get filter configuration stats.

        Returns:
            Dict with filter statistics
        """
        return {
            "max_size_mb": self.max_size_bytes / 1024 / 1024,
            "blacklisted_extensions": list(self.blacklist_exts),
            "skip_patterns": self.skip_patterns,
            "pdf_max_size_mb": self.pdf_max_size / 1024 / 1024,
        }
