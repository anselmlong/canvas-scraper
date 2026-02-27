"""Test that all simple scripts can be imported."""

import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_import_main():
    """Test main module imports."""
    import main

    assert hasattr(main, "main")


def test_import_canvas_client():
    """Test canvas_client module imports."""
    import canvas_client

    assert hasattr(canvas_client, "CanvasClient")


def test_import_config():
    """Test config module imports."""
    import config

    assert hasattr(config, "Config")


def test_import_download_manager():
    """Test download_manager module imports."""
    import download_manager

    assert hasattr(download_manager, "DownloadManager")


def test_import_filter_engine():
    """Test filter_engine module imports."""
    import filter_engine

    assert hasattr(filter_engine, "FilterEngine")


def test_import_file_organizer():
    """Test file_organizer module imports."""
    import file_organizer

    assert hasattr(file_organizer, "FileOrganizer")


def test_import_metadata_db():
    """Test metadata_db module imports."""
    import metadata_db

    assert hasattr(metadata_db, "MetadataDB")


def test_import_course_manager():
    """Test course_manager module imports."""
    import course_manager

    assert hasattr(course_manager, "CourseManager")


def test_import_report_generator():
    """Test report_generator module imports."""
    import report_generator

    assert hasattr(report_generator, "ReportGenerator")


def test_import_email_notifier():
    """Test email_notifier module imports."""
    import email_notifier

    assert hasattr(email_notifier, "EmailNotifier")
