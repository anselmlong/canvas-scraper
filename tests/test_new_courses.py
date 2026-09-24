"""Course discovery is visible, opt-in, and safe for unattended runs."""
from unittest.mock import MagicMock, patch
import sys

import pytest
import main as main_module
from report_generator import ReportGenerator


def test_report_preserves_unselected_courses():
    courses = [{"id": 42, "code": "CS101", "name": "Programming", "term": "Fall"}]
    report = ReportGenerator(MagicMock()).generate_report([], [], [], [], courses)
    assert report["new_courses"] == courses
    assert report["new_count"] == 0


@pytest.mark.parametrize("flag", ["--add-courses", "--export-config"])
@pytest.mark.parametrize("explicit", [True, False])
def test_prompting_commands_reject_unattended_runs(monkeypatch, flag, explicit):
    monkeypatch.setattr(sys, "argv", ["main.py", flag] + (["--non-interactive"] if explicit else []))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: explicit)
    with patch.object(main_module, "Config"), patch.object(main_module, "setup_logging"), \
         patch("builtins.input", side_effect=AssertionError("must not prompt")), \
         patch.object(main_module, "CanvasClient") as client, \
         patch.object(main_module, "run_sync") as sync:
        with pytest.raises(SystemExit) as exc:
            main_module.main()
    assert exc.value.code == 1
    client.assert_not_called()
    sync.assert_not_called()


@pytest.mark.parametrize("available", [[], [{"id": 42, "code": "CS101"}]])
def test_add_courses_selects_only_new_courses_and_does_not_sync(monkeypatch, available):
    monkeypatch.setattr(sys, "argv", ["main.py", "--add-courses"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch.object(main_module, "Config"), patch.object(main_module, "setup_logging"), \
         patch.object(main_module, "CanvasClient"), \
         patch.object(main_module, "CourseManager") as manager_cls, \
         patch.object(main_module, "run_sync") as sync:
        manager = manager_cls.return_value
        manager.detect_new_courses.return_value = available
        manager.interactive_course_selection.return_value = available
        main_module.main()
    sync.assert_not_called()
    if available:
        manager.interactive_course_selection.assert_called_once_with(available)
        manager.add_courses_to_config.assert_called_once_with(available)
    else:
        manager.interactive_course_selection.assert_not_called()
        manager.add_courses_to_config.assert_not_called()
