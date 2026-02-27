"""Test canvas_client module with mocks."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_canvas_client_instantiation():
    """Test CanvasClient can be instantiated."""
    with patch("canvas_client.Canvas"):
        import canvas_client

        client = canvas_client.CanvasClient("https://example.com", "test_token")
        assert client.base_url == "https://example.com"
        assert client.api_token == "test_token"


def test_canvas_client_test_connection_success():
    """Test CanvasClient.test_connection returns success on valid credentials."""
    with patch("canvas_client.Canvas") as mock_canvas_class:
        mock_canvas = MagicMock()
        mock_user = MagicMock()
        mock_user.name = "Test User"
        mock_canvas.get_current_user.return_value = mock_user
        mock_canvas_class.return_value = mock_canvas

        import canvas_client

        client = canvas_client.CanvasClient("https://example.com", "test_token")
        success, message = client.test_connection()

        assert success is True
        assert "Test User" in message


def test_canvas_client_test_connection_failure():
    """Test CanvasClient.test_connection returns failure on invalid credentials."""
    from canvasapi.exceptions import CanvasException

    with patch("canvas_client.Canvas") as mock_canvas_class:
        mock_canvas = MagicMock()
        mock_canvas.get_current_user.side_effect = CanvasException("Invalid token")
        mock_canvas_class.return_value = mock_canvas

        import canvas_client

        client = canvas_client.CanvasClient("https://example.com", "invalid_token")
        success, message = client.test_connection()

        assert success is False
        assert "error" in message.lower() or "invalid" in message.lower()
