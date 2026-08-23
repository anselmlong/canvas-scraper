"""Test download_manager module: retries, shutdown handling, result aggregation."""

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from download_manager import DownloadManager, DownloadTask  # noqa: E402


def _make_task(destination: Path) -> DownloadTask:
    return DownloadTask(
        file_id="1",
        file_url="https://example.com/files/1",
        destination=destination,
        filename="file.pdf",
        size_bytes=100,
        course_name="CS101",
    )


def test_download_files_reports_success(tmp_path):
    canvas_client = MagicMock()
    canvas_client.download_file.return_value = True

    manager = DownloadManager(canvas_client, max_workers=1, max_retries=1)
    task = _make_task(tmp_path / "file.pdf")

    successful, failed = manager.download_files([task])

    assert len(successful) == 1
    assert failed == []
    canvas_client.download_file.assert_called_once()


def test_download_files_retries_then_succeeds(tmp_path, monkeypatch):
    canvas_client = MagicMock()
    canvas_client.download_file.side_effect = [False, True]

    manager = DownloadManager(
        canvas_client, max_workers=1, max_retries=3, retry_delay=0.01
    )
    task = _make_task(tmp_path / "file.pdf")

    successful, failed = manager.download_files([task])

    assert len(successful) == 1
    assert successful[0].attempts == 2
    assert canvas_client.download_file.call_count == 2


def test_download_files_gives_up_after_max_retries(tmp_path):
    canvas_client = MagicMock()
    canvas_client.download_file.return_value = False

    manager = DownloadManager(
        canvas_client, max_workers=1, max_retries=2, retry_delay=0.01
    )
    task = _make_task(tmp_path / "file.pdf")

    successful, failed = manager.download_files([task])

    assert successful == []
    assert len(failed) == 1
    assert failed[0].attempts == 2
    assert canvas_client.download_file.call_count == 2


def test_download_files_empty_task_list(tmp_path):
    canvas_client = MagicMock()
    manager = DownloadManager(canvas_client)

    successful, failed = manager.download_files([])

    assert successful == []
    assert failed == []
    canvas_client.download_file.assert_not_called()


def test_download_files_skips_work_when_shutdown_already_set(tmp_path):
    """If shutdown is requested before download_files even starts pulling
    results, in-flight work is abandoned rather than reported as failed."""
    canvas_client = MagicMock()
    shutdown_event = threading.Event()
    shutdown_event.set()

    manager = DownloadManager(canvas_client, shutdown_event=shutdown_event)
    task = _make_task(tmp_path / "file.pdf")

    successful, failed = manager.download_files([task])

    assert successful == []
    assert failed == []


def test_download_with_retry_returns_cancelled_result_on_shutdown_during_wait(tmp_path):
    """_download_with_retry itself must surface a clear cancellation result
    when shutdown fires while waiting between retries."""
    canvas_client = MagicMock()
    canvas_client.download_file.return_value = False
    shutdown_event = threading.Event()

    # wait() returns True immediately since the event is already set,
    # simulating shutdown firing during the inter-retry backoff.
    shutdown_event.set()

    manager = DownloadManager(
        canvas_client, max_retries=3, retry_delay=0.01, shutdown_event=None
    )
    manager.shutdown_event = shutdown_event
    task = _make_task(tmp_path / "file.pdf")

    result = manager._download_with_retry(task)

    assert result.success is False
    assert "shutdown" in result.error_message.lower()


def test_max_bytes_is_passed_through_to_canvas_client(tmp_path):
    canvas_client = MagicMock()
    canvas_client.download_file.return_value = True

    manager = DownloadManager(canvas_client, max_workers=1, max_bytes=12345)
    task = _make_task(tmp_path / "file.pdf")

    manager.download_files([task])

    _, kwargs = canvas_client.download_file.call_args
    assert kwargs["max_bytes"] == 12345
