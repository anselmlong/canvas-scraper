"""Test canvas_client module with mocks."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _mock_streaming_response(chunks, status_ok=True):
    """Build a MagicMock resembling a requests.Response used for streaming."""
    response = MagicMock()
    response.iter_content.return_value = iter(chunks)
    if status_ok:
        response.raise_for_status.return_value = None
    return response


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


def test_download_file_succeeds_within_max_bytes(tmp_path):
    """A response within the configured cap is written to disk normally."""
    with patch("canvas_client.Canvas"):
        import canvas_client

        client = canvas_client.CanvasClient("https://example.com", "test_token")

    dest = tmp_path / "file.pdf"
    response = _mock_streaming_response([b"a" * 100, b"b" * 100])

    with patch("canvas_client.requests.get", return_value=response):
        success = client.download_file(
            "https://example.com/files/1", str(dest), max_bytes=1000
        )

    assert success is True
    assert dest.exists()
    assert dest.stat().st_size == 200


def test_download_file_aborts_when_exceeding_max_bytes(tmp_path):
    """The actual streamed size is enforced, not just Canvas's reported size."""
    with patch("canvas_client.Canvas"):
        import canvas_client

        client = canvas_client.CanvasClient("https://example.com", "test_token")

    dest = tmp_path / "file.pdf"
    # Response streams far more than the configured cap.
    response = _mock_streaming_response([b"x" * 1000 for _ in range(10)])

    with patch("canvas_client.requests.get", return_value=response):
        success = client.download_file(
            "https://example.com/files/1", str(dest), max_bytes=500
        )

    assert success is False
    # Partial file must be cleaned up, not left half-written on disk.
    assert not dest.exists()


def test_download_file_no_cap_when_max_bytes_none(tmp_path):
    """Existing callers that don't pass max_bytes keep unbounded streaming."""
    with patch("canvas_client.Canvas"):
        import canvas_client

        client = canvas_client.CanvasClient("https://example.com", "test_token")

    dest = tmp_path / "file.pdf"
    response = _mock_streaming_response([b"y" * 10000])

    with patch("canvas_client.requests.get", return_value=response):
        success = client.download_file("https://example.com/files/1", str(dest))

    assert success is True
    assert dest.stat().st_size == 10000
