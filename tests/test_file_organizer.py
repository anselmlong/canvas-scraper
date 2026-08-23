"""Test file_organizer module, especially path/filename sanitization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from file_organizer import FileOrganizer  # noqa: E402


def test_sanitize_filename_strips_illegal_characters(tmp_path):
    organizer = FileOrganizer(tmp_path)
    assert organizer._sanitize_filename('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"


def test_sanitize_filename_strips_leading_trailing_dots_and_spaces(tmp_path):
    organizer = FileOrganizer(tmp_path)
    assert organizer._sanitize_filename("  ..notes.txt..  ") == "notes.txt"


def test_sanitize_filename_pure_dots_falls_back_to_unnamed(tmp_path):
    organizer = FileOrganizer(tmp_path)
    assert organizer._sanitize_filename("..") == "unnamed"
    assert organizer._sanitize_filename("....") == "unnamed"
    assert organizer._sanitize_filename("") == "unnamed"


def test_sanitize_filename_truncates_long_names_preserving_extension(tmp_path):
    organizer = FileOrganizer(tmp_path)
    long_name = ("a" * 300) + ".pdf"
    result = organizer._sanitize_filename(long_name)
    assert len(result) <= 200
    assert result.endswith(".pdf")


def test_get_file_path_rejects_path_traversal_in_folder_path(tmp_path):
    """A malicious/odd Canvas folder path shouldn't escape the course directory."""
    organizer = FileOrganizer(tmp_path)
    course_dir = organizer.get_course_directory("CS101", "Intro to CS", "Fall 2024")

    file_path = organizer.get_file_path(course_dir, "../../../etc", "passwd.txt")

    # Resolved path must stay inside the course directory, never above base_path.
    resolved = file_path.resolve()
    assert organizer.base_path.resolve() in resolved.parents or resolved.parent == organizer.base_path.resolve()
    assert str(resolved).startswith(str(organizer.base_path.resolve()))


def test_get_file_path_creates_nested_folders(tmp_path):
    organizer = FileOrganizer(tmp_path)
    course_dir = organizer.get_course_directory("CS101", "Intro to CS", "Fall 2024")

    file_path = organizer.get_file_path(course_dir, "Lectures/Week 1", "slides.pdf")

    assert file_path.parent.exists()
    assert file_path.name == "slides.pdf"


def test_get_file_path_deduplicates_existing_files(tmp_path):
    organizer = FileOrganizer(tmp_path)
    course_dir = organizer.get_course_directory("CS101", "Intro to CS", "Fall 2024")

    first_path = organizer.get_file_path(course_dir, "", "notes.txt")
    first_path.write_text("original")

    second_path = organizer.get_file_path(course_dir, "", "notes.txt")

    assert second_path != first_path
    assert second_path.name == "notes_1.txt"


def test_get_course_directory_sanitizes_name(tmp_path):
    organizer = FileOrganizer(tmp_path)
    course_dir = organizer.get_course_directory(
        "CS/101", 'Intro: "Computer" Science', "Fall 2024"
    )
    assert course_dir.exists()
    assert "/" not in course_dir.name.replace(str(organizer.base_path), "")
