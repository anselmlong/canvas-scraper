"""Test email_notifier module with mocks."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_email_notifier_instantiation():
    """Test EmailNotifier can be instantiated with mock config."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, default=None: {
        "notification.email.smtp_server": "smtp.gmail.com",
        "notification.email.smtp_port": 587,
        "notification.email.from_name": "Test",
        "notification.email.recipient": "test@example.com",
    }.get(key, default)
    mock_config.email_username = "test@example.com"
    mock_config.email_password = "test_password"

    with patch("email_notifier.Environment"):
        import email_notifier

        notifier = email_notifier.EmailNotifier(mock_config)
        assert notifier.smtp_server == "smtp.gmail.com"
        assert notifier.recipient == "test@example.com"


def test_email_notifier_test_connection_success():
    """Test EmailNotifier.test_connection returns success on valid credentials."""
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, default=None: {
        "notification.email.smtp_server": "smtp.gmail.com",
        "notification.email.smtp_port": 587,
        "notification.email.from_name": "Test",
        "notification.email.recipient": "test@example.com",
    }.get(key, default)
    mock_config.email_username = "test@example.com"
    mock_config.email_password = "test_password"

    with patch("email_notifier.Environment"):
        with patch("email_notifier.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            import email_notifier

            notifier = email_notifier.EmailNotifier(mock_config)
            success, message = notifier.test_connection()

            assert success is True
            assert "success" in message.lower()


def test_email_notifier_test_connection_failure():
    """Test EmailNotifier.test_connection returns failure on invalid credentials."""
    import smtplib

    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, default=None: {
        "notification.email.smtp_server": "smtp.gmail.com",
        "notification.email.smtp_port": 587,
        "notification.email.from_name": "Test",
        "notification.email.recipient": "test@example.com",
    }.get(key, default)
    mock_config.email_username = "test@example.com"
    mock_config.email_password = "wrong_password"

    with patch("email_notifier.Environment"):
        with patch("email_notifier.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPAuthenticationError(
                535, b"Authentication failed"
            )

            import email_notifier

            notifier = email_notifier.EmailNotifier(mock_config)
            success, message = notifier.test_connection()

            assert success is False
            assert "auth" in message.lower() or "failed" in message.lower()
