"""Unit tests for position manager exit rules."""

from datetime import datetime, timedelta, timezone

from poly_sports.trading.config import TradingConfig
from poly_sports.trading.position_manager import PositionManager
from poly_sports.trading.models import ExecutionResult, Signal


def _signal() -> Signal:
    return Signal(
        signal_id="sig-1",
        market_id="m1",
        event_id="e1",
        outcome_name="Team A",
        side="BUY",
        order_type="ENTRY",
        suggested_price=0.5,
        target_price=0.55,
        confidence=0.9,
        expected_profit_pct=0.05,
        liquidity=5000,
        spread=0.01,
        created_at="2026-01-01T00:00:00Z",
    )


def _entry_result() -> ExecutionResult:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return ExecutionResult(
        ok=True,
        order_id="paper-1",
        signal_id="sig-1",
        market_id="m1",
        side="BUY",
        order_type="ENTRY",
        filled_size_usd=25,
        fill_price=0.5,
        fees_usd=0.05,
        slippage_bps=10,
        timestamp=now,
    )


def test_position_manager_take_profit_exit() -> None:
    cfg = TradingConfig(take_profit_pct=0.1, stop_loss_pct=0.1)
    pm = PositionManager(cfg)
    pos = pm.open_position(_signal(), _entry_result())
    decision = pm.evaluate_exit(pos, latest_price=0.56)
    assert decision.should_exit is True
    assert decision.reason in {"take_profit", "target_reached"}


def test_position_manager_max_holding_exit() -> None:
    cfg = TradingConfig(max_holding_minutes=10)
    pm = PositionManager(cfg)
    pos = pm.open_position(_signal(), _entry_result())
    entry_dt = datetime.fromisoformat(pos.entry_time.replace("Z", "+00:00"))
    now = entry_dt + timedelta(minutes=20)
    decision = pm.evaluate_exit(pos, latest_price=0.5, now_utc=now)
    assert decision.should_exit is True
    assert decision.reason == "max_holding_time"
