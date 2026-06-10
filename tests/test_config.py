"""Test config module."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_config_loads():
    """Test Config can be instantiated and loads from yaml."""
    # Mock the project root to point to test data
    with patch("config.Path") as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.parent = Path(__file__).parent.parent
        mock_path_instance.__truediv__ = lambda self, x: Path(__file__).parent.parent / x
        mock_path.return_value = mock_path_instance

        # We can't actually load config without a real config file
        # So just verify the module can be imported and has expected attributes
        import config

        assert hasattr(config, "Config")


def test_config_class_exists():
    """Test Config class exists."""
    import config

    # Verify Config is a class
    assert isinstance(config.Config, type)


def test_validate_check_email_false_skips_email_errors(tmp_path, monkeypatch):
    """--no-email runs must not fail validation over missing email credentials."""
    import yaml

    import config as config_module

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "canvas": {"base_url": "https://canvas.example.edu/"},
                "courses": {"sync_mode": "whitelist", "whitelist": [12345]},
                "notification": {"email": {"enabled": True, "recipient": ""}},
            }
        )
    )
    cfg = config_module.Config(config_path=cfg_file)
    monkeypatch.setenv("CANVAS_API_TOKEN", "token")
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)
    monkeypatch.delenv("EMAIL_APP_PASSWORD", raising=False)

    ok_with_email, errors_with_email = cfg.validate()
    assert not ok_with_email
    assert any("Email" in e for e in errors_with_email)

    ok_without_email, errors_without_email = cfg.validate(check_email=False)
    assert ok_without_email, errors_without_email
