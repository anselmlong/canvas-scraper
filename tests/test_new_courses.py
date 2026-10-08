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


@pytest.mark.parametrize(
    "flag", ["--add-courses", "--reselect-courses", "--remove-courses", "--export-config"]
)
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


def _run_course_command(monkeypatch, flag, whitelist, active, selected):
    monkeypatch.setattr(sys, "argv", ["main.py", flag])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch.object(main_module, "Config") as config_cls, \
         patch.object(main_module, "setup_logging"), \
         patch.object(main_module, "CanvasClient"), \
         patch.object(main_module, "CourseManager") as manager_cls, \
         patch.object(main_module, "run_sync") as sync:
        config = config_cls.return_value
        config.get.side_effect = lambda key, default=None: (
            whitelist if key == "courses.whitelist" else default
        )
        manager = manager_cls.return_value
        manager.get_active_courses.return_value = active
        manager.get_synced_courses.return_value = [
            c for c in active if str(c["id"]) in {str(w) for w in whitelist}
        ]
        manager.interactive_course_selection.return_value = selected
        main_module.main()
    sync.assert_not_called()
    return config, manager


def test_reselect_courses_replaces_whitelist_and_does_not_sync(monkeypatch):
    active = [{"id": 1, "code": "A"}, {"id": 2, "code": "B"}]
    config, manager = _run_course_command(
        monkeypatch, "--reselect-courses", [1], active, [active[1]]
    )
    manager.interactive_course_selection.assert_called_once_with(active)
    config.set.assert_called_once_with("courses.whitelist", [2])
    config.save.assert_called_once()


def test_remove_courses_offers_only_synced_courses_and_does_not_sync(monkeypatch):
    active = [{"id": 1, "code": "A"}, {"id": 2, "code": "B"}]
    _, manager = _run_course_command(
        monkeypatch, "--remove-courses", ["1", 2], active, [active[0]]
    )
    offered = manager.interactive_course_selection.call_args.args[0]
    assert offered == active
    # A quoted ID in a hand-edited whitelist is matched and removed as-is
    manager.remove_courses_from_config.assert_called_once_with(["1"])
