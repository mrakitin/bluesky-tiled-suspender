"""Tests for tiled_suspender.py."""

from unittest.mock import MagicMock, patch

import pytest
from ophyd.utils.errors import ReadOnlyError

from tiled_suspender import TiledHealthSignal, TiledSuspender, tiled_status


# ---------------------------------------------------------------------------
# TiledHealthSignal tests
# ---------------------------------------------------------------------------


def test_get_returns_string():
    """get() must always return a string."""
    sig = TiledHealthSignal(name="test_sig")
    value = sig.get()
    assert isinstance(value, str)


def test_get_offline_on_network_error():
    """get() returns 'offline' when the server is unreachable."""
    sig = TiledHealthSignal(
        name="test_offline",
        url="https://this.url.does.not.exist.example.invalid/healthz",
        timeout=2.0,
    )
    assert sig.get() == "offline"


def test_get_offline_on_request_exception():
    """get() returns 'offline' when requests raises any exception."""
    sig = TiledHealthSignal(name="test_exc")
    with patch("tiled_suspender.requests.get", side_effect=ConnectionError("boom")):
        assert sig.get() == "offline"


def test_get_parses_status_from_json():
    """get() extracts the 'status' key from the JSON response."""
    sig = TiledHealthSignal(name="test_parse")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": "ready"}
    with patch("tiled_suspender.requests.get", return_value=mock_response):
        assert sig.get() == "ready"


def test_get_returns_unknown_when_key_missing():
    """get() returns 'unknown' when the JSON has no 'status' key."""
    sig = TiledHealthSignal(name="test_no_key")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {}
    with patch("tiled_suspender.requests.get", return_value=mock_response):
        assert sig.get() == "unknown"


def test_readback_updated_after_get():
    """_readback is updated to match the last get() result."""
    sig = TiledHealthSignal(name="test_rb")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": "ready"}
    with patch("tiled_suspender.requests.get", return_value=mock_response):
        sig.get()
    assert sig._readback == "ready"


def test_put_raises_readonly_error():
    """put() must raise ReadOnlyError."""
    sig = TiledHealthSignal(name="test_put")
    with pytest.raises(ReadOnlyError):
        sig.put("ready")


# ---------------------------------------------------------------------------
# Module-level instance
# ---------------------------------------------------------------------------


def test_tiled_status_instance():
    """tiled_status is a TiledHealthSignal named 'tiled_status'."""
    assert isinstance(tiled_status, TiledHealthSignal)
    assert tiled_status.name == "tiled_status"


# ---------------------------------------------------------------------------
# TiledSuspender tests
# ---------------------------------------------------------------------------


def test_suspender_defaults_to_tiled_status():
    """TiledSuspender uses the module-level tiled_status when no signal given."""
    s = TiledSuspender()
    assert s._sig is tiled_status


def test_suspender_accepts_custom_signal():
    """TiledSuspender accepts an explicit signal."""
    sig = TiledHealthSignal(name="custom")
    s = TiledSuspender(sig)
    assert s._sig is sig


@pytest.mark.parametrize("value", ["offline", "unknown", "error", "degraded", ""])
def test_should_suspend_when_not_ready(value):
    """_should_suspend returns True for any value other than 'ready'."""
    s = TiledSuspender()
    assert s._should_suspend(value) is True


def test_should_not_suspend_when_ready():
    """_should_suspend returns False when value is 'ready'."""
    s = TiledSuspender()
    assert s._should_suspend("ready") is False


@pytest.mark.parametrize("value", ["offline", "unknown", "error", "degraded", ""])
def test_should_not_resume_when_not_ready(value):
    """_should_resume returns False for any value other than 'ready'."""
    s = TiledSuspender()
    assert s._should_resume(value) is False


def test_should_resume_when_ready():
    """_should_resume returns True when value is 'ready'."""
    s = TiledSuspender()
    assert s._should_resume("ready") is True


# ---------------------------------------------------------------------------
# Integration test (live network)
# ---------------------------------------------------------------------------


@pytest.mark.network
def test_live_endpoint_returns_ready():
    """Integration: the live tiled endpoint returns 'ready' (requires network)."""
    sig = TiledHealthSignal(name="live_test")
    assert sig.get() == "ready"
