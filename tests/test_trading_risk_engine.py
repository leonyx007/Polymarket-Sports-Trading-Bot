"""Unit tests for trading risk engine."""

from datetime import datetime, timezone

from poly_sports.trading.config import TradingConfig
from poly_sports.trading.models import Position, Signal
from poly_sports.trading.risk_engine import RiskEngine


def _signal(**kwargs) -> Signal:
    base = Signal(
        signal_id="sig-1",
        market_id="m1",
        event_id="e1",
        outcome_name="Team A",
        side="BUY",
        order_type="ENTRY",
        suggested_price=0.5,
        target_price=0.52,
        confidence=0.9,
        expected_profit_pct=0.05,
        liquidity=5000,
        spread=0.01,
        created_at="2026-01-01T00:00:00Z",
    )
    for k, v in kwargs.items():
        setattr(base, k, v)
    return base


def _open_position() -> Position:
    return Position(
        position_id="pos-1",
        signal_id="sig-old",
        market_id="m1",
        event_id="e1",
        outcome_name="Team A",
        side="BUY",
        status="OPEN",
        size_usd=25,
        entry_price=0.5,
        entry_time="2026-01-01T00:00:00Z",
        target_price=0.55,
        stop_loss_price=0.45,
        take_profit_price=0.6,
        max_holding_minutes=60,
    )


def test_risk_engine_allows_valid_signal() -> None:
    cfg = TradingConfig()
    engine = RiskEngine(cfg)
    now = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    decision = engine.evaluate_entry(_signal(), open_positions=[], realized_pnl_today_usd=0, now_utc=now)
    assert decision.allow is True
    assert decision.reason_code == "ok"


def test_risk_engine_blocks_low_liquidity() -> None:
    cfg = TradingConfig(min_liquidity_usd=3000)
    engine = RiskEngine(cfg)
    now = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    decision = engine.evaluate_entry(
        _signal(liquidity=2000), open_positions=[], realized_pnl_today_usd=0, now_utc=now
    )
    assert decision.allow is False
    assert decision.reason_code == "low_liquidity"


def test_risk_engine_blocks_duplicate_exposure() -> None:
    cfg = TradingConfig()
    engine = RiskEngine(cfg)
    now = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    decision = engine.evaluate_entry(
        _signal(), open_positions=[_open_position()], realized_pnl_today_usd=0, now_utc=now
    )
    assert decision.allow is False
    assert decision.reason_code == "duplicate_market_exposure"
