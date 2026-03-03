"""Unit tests for signal idempotency helpers."""

from poly_sports.trading.decision_engine import generate_signal_id, should_open_signal


def test_generate_signal_id_stable() -> None:
    sid1 = generate_signal_id("m1", "Team A", "BUY", 0.5, "2026-01-01T00:00:00+00:00")
    sid2 = generate_signal_id("m1", "Team A", "BUY", 0.5, "2026-01-01T00:00:00+00:00")
    assert sid1 == sid2


def test_should_open_signal_idempotent() -> None:
    seen: set[str] = set()
    signal_id = "abc123"
    assert should_open_signal(signal_id, seen) is True
    assert should_open_signal(signal_id, seen) is False
