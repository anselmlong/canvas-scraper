"""Tests for the --non-interactive guard in main()."""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import main as main_module

SRC_MAIN = Path(__file__).parent.parent / "src" / "main.py"


class _FakeStdin:
    """Stand-in for sys.stdin with a controllable isatty()."""

    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def _mock_config(configured: bool) -> MagicMock:
    config = MagicMock()
    config.is_configured.return_value = configured
    config.validate.return_value = (
        configured,
        [] if configured else ["Canvas API token not set in .env file"],
    )
    return config


def _call_main(monkeypatch, argv, configured, tty):
    """Invoke main.main() with mocked Config, stdin tty state, and argv.

    Returns (exit_code, run_sync_mock, setup_wizard_mock).
    """
    config = _mock_config(configured)
    monkeypatch.setattr(sys, "argv", ["main.py"] + argv)
    monkeypatch.setattr(sys, "stdin", _FakeStdin(tty))
    with (
        patch.object(main_module, "Config", return_value=config),
        patch.object(main_module, "setup_logging", return_value=MagicMock()),
        patch.object(main_module, "run_sync") as run_sync,
        patch.object(main_module, "setup_wizard") as setup_wizard,
    ):
        exit_code = 0
        try:
            main_module.main()
        except SystemExit as exc:
            exit_code = exc.code
    return exit_code, run_sync, setup_wizard


def test_non_interactive_flag_exits_1_when_unconfigured(monkeypatch):
    """--non-interactive on an unconfigured install exits 1 (even with a tty)."""
    exit_code, run_sync, setup_wizard = _call_main(
        monkeypatch, ["--non-interactive"], configured=False, tty=True
    )
    assert exit_code == 1
    setup_wizard.assert_not_called()
    run_sync.assert_not_called()


def test_non_tty_stdin_exits_1_when_unconfigured(monkeypatch):
    """Without the flag, a non-tty stdin (cron/CI) still skips the wizard."""
    exit_code, run_sync, setup_wizard = _call_main(
        monkeypatch, [], configured=False, tty=False
    )
    assert exit_code == 1
    setup_wizard.assert_not_called()
    run_sync.assert_not_called()


def test_tty_unconfigured_launches_wizard(monkeypatch):
    """Interactive terminal without the flag still gets the setup wizard."""
    exit_code, run_sync, setup_wizard = _call_main(
        monkeypatch, [], configured=False, tty=True
    )
    assert exit_code == 0
    setup_wizard.assert_called_once()
    run_sync.assert_not_called()  # still unconfigured after wizard -> return


def test_non_interactive_configured_runs_sync(monkeypatch):
    """--non-interactive on a configured install proceeds to a normal sync."""
    exit_code, run_sync, setup_wizard = _call_main(
        monkeypatch,
        ["--non-interactive", "--dry-run", "--no-email"],
        configured=True,
        tty=False,
    )
    assert exit_code == 0
    setup_wizard.assert_not_called()
    run_sync.assert_called_once()


def test_non_interactive_logs_validation_errors(monkeypatch, caplog):
    """The guard logs each validation error before exiting."""
    with caplog.at_level(logging.ERROR):
        exit_code, _, _ = _call_main(
            monkeypatch, ["--non-interactive"], configured=False, tty=True
        )
    assert exit_code == 1
    assert "not configured and running non-interactively" in caplog.text
    assert "Canvas API token not set in .env file" in caplog.text
    assert "--setup" in caplog.text


def test_parser_accepts_non_interactive_flag():
    """--non-interactive is a recognized argument (shows up in --help)."""
    result = subprocess.run(
        [sys.executable, str(SRC_MAIN), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "--non-interactive" in result.stdout


def test_tty_wizard_success_runs_sync(monkeypatch):
    """When the wizard configures successfully, sync proceeds."""
    config = _mock_config(configured=False)
    config.is_configured.side_effect = [False, True]  # before wizard, after wizard
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setattr(sys, "stdin", _FakeStdin(True))
    with (
        patch.object(main_module, "Config", return_value=config),
        patch.object(main_module, "setup_logging", return_value=MagicMock()),
        patch.object(main_module, "run_sync") as run_sync,
        patch.object(main_module, "setup_wizard") as setup_wizard,
    ):
        main_module.main()
    setup_wizard.assert_called_once()
    run_sync.assert_called_once()


def test_subprocess_non_tty_unconfigured_exits_1(tmp_path):
    """End-to-end: piped stdin + no config exits 1 instead of hanging on input().

    Config resolves config.yaml/.env relative to main.py's project root, so the
    src/ tree is copied into tmp_path — otherwise a developer's real config.yaml
    would make the subprocess "configured" and launch an actual sync.
    """
    src_copy = tmp_path / "src"
    shutil.copytree(SRC_MAIN.parent, src_copy)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CANVAS_API_TOKEN", "EMAIL_USERNAME", "EMAIL_APP_PASSWORD")
    }
    result = subprocess.run(
        [sys.executable, str(src_copy / "main.py")],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        cwd=tmp_path,
    )
    assert result.returncode == 1
    assert "not configured and running non-interactively" in result.stderr
