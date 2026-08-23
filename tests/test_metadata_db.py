"""Test metadata_db module (SQLite-backed tracking of downloads/skips)."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from metadata_db import MetadataDB  # noqa: E402


def test_add_and_get_downloaded_file(tmp_path):
    db = MetadataDB(tmp_path / "scraper.db")

    db.add_downloaded_file(
        file_id="1",
        course_id="100",
        course_name="CS101",
        filename="notes.pdf",
        local_path="/tmp/notes.pdf",
        size_bytes=1234,
        canvas_modified_date=datetime(2024, 1, 1),
    )

    record = db.get_downloaded_file("1")
    assert record is not None
    assert record["filename"] == "notes.pdf"
    assert record["size_bytes"] == 1234


def test_get_downloaded_file_missing_returns_none(tmp_path):
    db = MetadataDB(tmp_path / "scraper.db")
    assert db.get_downloaded_file("does-not-exist") is None


def test_add_downloaded_file_is_upsert(tmp_path):
    """INSERT OR REPLACE means re-adding the same file_id updates in place."""
    db = MetadataDB(tmp_path / "scraper.db")

    db.add_downloaded_file(
        file_id="1", course_id="100", course_name="CS101", filename="v1.pdf",
        local_path="/tmp/v1.pdf", size_bytes=100,
        canvas_modified_date=datetime(2024, 1, 1),
    )
    db.add_downloaded_file(
        file_id="1", course_id="100", course_name="CS101", filename="v2.pdf",
        local_path="/tmp/v2.pdf", size_bytes=200,
        canvas_modified_date=datetime(2024, 2, 1),
    )

    record = db.get_downloaded_file("1")
    assert record["filename"] == "v2.pdf"
    assert record["size_bytes"] == 200


def test_delete_downloaded_file(tmp_path):
    db = MetadataDB(tmp_path / "scraper.db")
    db.add_downloaded_file(
        file_id="1", course_id="100", course_name="CS101", filename="a.pdf",
        local_path="/tmp/a.pdf", size_bytes=1,
        canvas_modified_date=datetime(2024, 1, 1),
    )
    db.delete_downloaded_file("1")
    assert db.get_downloaded_file("1") is None


def test_records_with_sql_special_characters_round_trip(tmp_path):
    """Filenames/course names containing quotes must not corrupt other rows
    or break queries -- parameterized queries should make this a non-issue,
    but this guards against a future regression to string formatting."""
    db = MetadataDB(tmp_path / "scraper.db")

    tricky_name = "week 1'; DROP TABLE downloaded_files; --.pdf"
    db.add_downloaded_file(
        file_id="1", course_id="100", course_name='CS101 "Intro"',
        filename=tricky_name, local_path="/tmp/x.pdf", size_bytes=1,
        canvas_modified_date=datetime(2024, 1, 1),
    )

    record = db.get_downloaded_file("1")
    assert record["filename"] == tricky_name
    assert record["course_name"] == 'CS101 "Intro"'

    # Table must still exist and be queryable.
    assert db.get_downloaded_files_by_course("100") != []


def test_skipped_files_notification_flow(tmp_path):
    db = MetadataDB(tmp_path / "scraper.db")

    db.add_skipped_file(
        file_id="1", course_id="100", course_name="CS101", filename="movie.mp4",
        folder_path="Lectures", size_bytes=999, canvas_url="https://example.com/1",
        skip_reason="blacklisted",
    )

    new_skips = db.get_new_skipped_files()
    assert len(new_skips) == 1
    assert new_skips[0]["notified"] == 0

    db.mark_skipped_files_notified()
    assert db.get_new_skipped_files() == []


def test_run_history_ordering(tmp_path):
    db = MetadataDB(tmp_path / "scraper.db")

    db.add_run_history(files_downloaded=1, files_updated=0, files_skipped=0, total_size_bytes=100)
    second_id = db.add_run_history(files_downloaded=2, files_updated=1, files_skipped=1, total_size_bytes=200)

    last_run = db.get_last_run()
    assert last_run["id"] == second_id
    assert last_run["files_downloaded"] == 2

    history = db.get_run_history(limit=10)
    assert len(history) == 2
    assert history[0]["id"] == second_id  # most recent first


def test_upcoming_assignments_excludes_notified(tmp_path):
    db = MetadataDB(tmp_path / "scraper.db")

    db.add_assignment(
        assignment_id="1", course_id="100", course_name="CS101", name="HW1",
        description="", due_at=datetime(2099, 1, 1), points_possible=10,
        submission_types=["online_upload"], canvas_url="https://example.com/a/1",
    )

    upcoming = db.get_upcoming_assignments()
    assert len(upcoming) == 1

    db.mark_assignments_notified()
    assert db.get_upcoming_assignments() == []
