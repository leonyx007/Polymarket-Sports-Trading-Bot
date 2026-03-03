"""Position lifecycle and exit decision logic."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import TradingConfig
from .models import ExecutionResult, ExitDecision, Position, Signal, utc_now_iso


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class PositionManager:
    """Open/monitor/close position lifecycle."""

    def __init__(self, config: TradingConfig) -> None:
        self.config = config

    def open_position(self, signal: Signal, execution: ExecutionResult) -> Position:
        now = execution.timestamp or utc_now_iso()
        stop_loss_price = signal.suggested_price * (1 - self.config.stop_loss_pct)
        take_profit_price = signal.suggested_price * (1 + self.config.take_profit_pct)
        return Position(
            position_id=f"pos-{execution.order_id}",
            signal_id=signal.signal_id,
            market_id=signal.market_id,
            event_id=signal.event_id,
            outcome_name=signal.outcome_name,
            side=signal.side,
            status="OPEN",
            size_usd=execution.filled_size_usd,
            entry_price=execution.fill_price,
            entry_time=now,
            target_price=signal.target_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            max_holding_minutes=self.config.max_holding_minutes,
            entry_fees_usd=execution.fees_usd,
            metadata={"signal_confidence": signal.confidence},
        )

    def evaluate_exit(
        self,
        position: Position,
        latest_price: Optional[float],
        now_utc: Optional[datetime] = None,
    ) -> ExitDecision:
        if not position.is_open():
            return ExitDecision(False, "position_closed")
        if latest_price is None or latest_price <= 0:
            return ExitDecision(False, "missing_price")

        now = now_utc or datetime.now(timezone.utc)
        entry_time = _parse_iso(position.entry_time)
        if now - entry_time >= timedelta(minutes=position.max_holding_minutes):
            return ExitDecision(True, "max_holding_time", latest_price)

        if latest_price <= position.stop_loss_price:
            return ExitDecision(True, "stop_loss", latest_price)
        if latest_price >= position.take_profit_price:
            return ExitDecision(True, "take_profit", latest_price)
        if latest_price >= position.target_price:
            return ExitDecision(True, "target_reached", latest_price)

        return ExitDecision(False, "hold", latest_price)

    def close_position(
        self,
        position: Position,
        execution: ExecutionResult,
        exit_reason: str,
    ) -> Position:
        if not position.is_open():
            return position
        # PnL approximation in probability-price space.
        gross_pnl = position.size_usd * ((execution.fill_price / position.entry_price) - 1)
        net_pnl = gross_pnl - position.entry_fees_usd - execution.fees_usd
        return replace(
            position,
            status="CLOSED",
            exit_price=execution.fill_price,
            exit_time=execution.timestamp,
            exit_reason=exit_reason,
            exit_fees_usd=execution.fees_usd,
            realized_pnl_usd=round(net_pnl, 8),
            unrealized_pnl_usd=0.0,
        )
