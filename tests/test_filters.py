"""Test filter_engine module - pure logic tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import filter_engine


def test_filter_engine_blacklist_extension():
    """Test FilterEngine skips files with blacklisted extensions."""
    fe = filter_engine.FilterEngine({
        "extension_blacklist": [".mp4", ".avi"]
    })

    # Test video extension
    file_meta = {"name": "lecture.mp4", "size": 1024, "mime_type": "video"}
    should_download, reason = fe.should_download(file_meta)
    assert should_download is False
    assert "extension" in reason.lower() or "video" in reason.lower() or "blacklist" in reason.lower()


def test_filter_engine_size_limit():
    """Test FilterEngine skips files exceeding size limit."""
    fe = filter_engine.FilterEngine({"max_file_size_mb": 10})

    # File larger than 10MB
    file_meta = {"name": "large_file.pdf", "size": 15 * 1024 * 1024, "mime_type": "pdf"}
    should_download, reason = fe.should_download(file_meta)
    assert should_download is False
    assert "size" in reason.lower() or "large" in reason.lower()


def test_filter_engine_name_pattern():
    """Test FilterEngine skips files matching name patterns."""
    fe = filter_engine.FilterEngine({"name_patterns_to_skip": ["textbook", "ebook"]})

    file_meta = {"name": "CS101_Textbook.pdf", "size": 1024, "mime_type": "pdf"}
    should_download, reason = fe.should_download(file_meta)
    assert should_download is False
    assert "textbook" in reason.lower() or "pattern" in reason.lower()


def test_filter_engine_allowed_file():
    """Test FilterEngine allows files that pass all filters."""
    fe = filter_engine.FilterEngine(
        {
            "max_file_size_mb": 10,
            "extension_blacklist": [".mp4", ".avi"],
            "name_patterns_to_skip": ["textbook"],
        }
    )

    # File that passes all filters
    file_meta = {"name": "lecture1.pdf", "size": 1024, "mime_type": "pdf"}
    should_download, reason = fe.should_download(file_meta)
    assert should_download is True


def test_filter_engine_empty_config():
    """Test FilterEngine allows all when config is empty."""
    fe = filter_engine.FilterEngine({})

    # Any file should be allowed
    file_meta = {"name": "any_file.pdf", "size": 10000000, "mime_type": "pdf"}
    should_download, reason = fe.should_download(file_meta)
    assert should_download is True
