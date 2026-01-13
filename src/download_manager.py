"""Download manager with parallel downloads and retry logic."""

import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class DownloadTask:
    """Represents a file download task."""

    file_id: str
    file_url: str
    destination: Path
    filename: str
    size_bytes: int
    course_name: str
    is_update: bool = False


@dataclass
class DownloadResult:
    """Result of a download attempt."""

    task: DownloadTask
    success: bool
    error_message: str = ""
    attempts: int = 1


class DownloadManager:
    """Manages file downloads with retry logic and parallelization."""

    def __init__(
        self,
        canvas_client,
        max_workers: int = 3,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """Initialize download manager.

        Args:
            canvas_client: CanvasClient instance
            max_workers: Maximum concurrent downloads
            max_retries: Maximum retry attempts per file
            retry_delay: Initial delay between retries (seconds)
        """
        self.canvas_client = canvas_client
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        logger.info(
            f"Initialized download manager "
            f"(workers: {max_workers}, max retries: {max_retries})"
        )

    def download_files(
        self, tasks: List[DownloadTask]
    ) -> Tuple[List[DownloadResult], List[DownloadResult]]:
        """Download multiple files in parallel.

        Args:
            tasks: List of download tasks

        Returns:
            Tuple of (successful_results, failed_results)
        """
        if not tasks:
            return [], []

        logger.info(f"Starting download of {len(tasks)} files...")

        successful = []
        failed = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._download_with_retry, task): task for task in tasks
            }

            # Process completed downloads
            for future in as_completed(future_to_task):
                result = future.result()

                if result.success:
                    successful.append(result)
                    logger.info(
                        f"✓ Downloaded: {result.task.filename} "
                        f"({self._format_size(result.task.size_bytes)})"
                    )
                else:
                    failed.append(result)
                    logger.error(
                        f"✗ Failed: {result.task.filename} - {result.error_message}"
                    )

        logger.info(
            f"Download complete: {len(successful)} successful, {len(failed)} failed"
        )

        return successful, failed

    def _download_with_retry(self, task: DownloadTask) -> DownloadResult:
        """Download a file with retry logic.

        Args:
            task: Download task

        Returns:
            Download result
        """
        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                # Ensure destination directory exists
                task.destination.parent.mkdir(parents=True, exist_ok=True)

                # Download file
                success = self.canvas_client.download_file(
                    task.file_url, str(task.destination)
                )

                if success:
                    return DownloadResult(task=task, success=True, attempts=attempt)
                else:
                    last_error = "Download returned False"

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Download attempt {attempt}/{self.max_retries} failed "
                    f"for {task.filename}: {last_error}"
                )

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** (attempt - 1))
                time.sleep(delay)

        # All retries failed
        return DownloadResult(
            task=task,
            success=False,
            error_message=f"Failed after {self.max_retries} attempts: {last_error}",
            attempts=self.max_retries,
        )

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
