"""Tests for run_sync's incremental-sync decisions."""

import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import main as main_module
from download_manager import DownloadResult
from metadata_db import MetadataDB

COURSE = {"id": 1, "code": "CS101", "name": "Programming", "term": "Fall"}


@pytest.fixture
def singapore_tz():
    """Run the test with the local clock at UTC+8, like an NUS laptop."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "Asia/Singapore"
    time.tzset()
    yield
    if old is None:
        del os.environ["TZ"]
    else:
        os.environ["TZ"] = old
    time.tzset()


def _config(tmp_path):
    values = {"filters": {}, "download.concurrent_downloads": 1}
    config = MagicMock()
    config.validate.return_value = (True, [])
    config.project_root = tmp_path
    config.download_path = tmp_path / "files"
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    return config


def _run(tmp_path, canvas_files=(), assignments=()):
    """Run run_sync against a mocked Canvas; return the DownloadTasks queued."""
    client = MagicMock()
    client.get_course_files.return_value = list(canvas_files)
    client.get_course_announcements.return_value = []
    client.get_course_assignments.return_value = list(assignments)
    client.get_folder_path.return_value = ""

    queued = []

    def fake_download(tasks):
        queued.extend(tasks)
        return [DownloadResult(task=t, success=True) for t in tasks], []

    with patch.object(main_module, "CanvasClient", return_value=client), \
         patch.object(main_module, "CourseManager") as manager_cls, \
         patch.object(main_module, "DownloadManager") as dm_cls:
        manager_cls.return_value.get_active_courses.return_value = [COURSE]
        manager_cls.return_value.detect_new_courses.return_value = []
        manager_cls.return_value.get_synced_courses.return_value = [COURSE]
        dm_cls.return_value.download_files.side_effect = fake_download
        main_module.run_sync(_config(tmp_path), send_email=False)
    return queued


def test_file_updated_after_download_is_refetched_east_of_utc(tmp_path, singapore_tz):
    db = MetadataDB(tmp_path / "data" / "scraper.db")
    db.add_downloaded_file("10", "1", "CS101", "slides.pdf", "x", 100, datetime.now())
    # Downloaded at 10:00 Singapore time (02:00 UTC), as datetime.now() stores it
    with sqlite3.connect(tmp_path / "data" / "scraper.db") as conn:
        conn.execute("UPDATE downloaded_files SET download_date = '2026-10-01T10:00:00'")

    # Lecturer re-uploads the slides at 05:00 UTC, three hours after the download
    canvas_file = {
        "id": 10, "name": "slides.pdf", "size": 100, "url": "u", "folder_id": None,
        "modified_at": datetime(2026, 10, 1, 5, 0, tzinfo=timezone.utc),
        "canvas_url": "c",
    }
    queued = _run(tmp_path, canvas_files=[canvas_file])

    assert [t.file_id for t in queued] == ["10"]
    assert queued[0].is_update
