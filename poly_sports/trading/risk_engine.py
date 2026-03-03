"""Deterministic safety checks before entry execution."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

from .config import TradingConfig
from .models import Position, RiskDecision, Signal


class RiskEngine:
    """Hard-gate risk checks for entries."""

    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self._cooldown_by_market: Dict[str, datetime] = {}

    def evaluate_entry(
        self,
        signal: Signal,
        open_positions: Iterable[Position],
        realized_pnl_today_usd: float,
        now_utc: Optional[datetime] = None,
    ) -> RiskDecision:
        now = now_utc or datetime.now(timezone.utc)

        # Global drawdown kill switch.
        if realized_pnl_today_usd <= -abs(self.config.max_daily_loss_usd):
            return RiskDecision(
                allow=False,
                reason_code="daily_loss_limit",
                message="Daily loss limit reached.",
                details={"realized_pnl_today_usd": realized_pnl_today_usd},
            )

        if signal.liquidity < self.config.min_liquidity_usd:
            return RiskDecision(
                allow=False,
                reason_code="low_liquidity",
                message="Liquidity below configured minimum.",
                details={"liquidity": signal.liquidity, "required": self.config.min_liquidity_usd},
            )

        if signal.spread > self.config.max_spread:
            return RiskDecision(
                allow=False,
                reason_code="wide_spread",
                message="Market spread above configured limit.",
                details={"spread": signal.spread, "max_spread": self.config.max_spread},
            )

        if signal.confidence < self.config.min_confidence:
            return RiskDecision(
                allow=False,
                reason_code="low_confidence",
                message="Signal confidence is too low.",
                details={"confidence": signal.confidence, "min_confidence": self.config.min_confidence},
            )

        # Signal freshness check.
        try:
            created = datetime.fromisoformat(signal.created_at.replace("Z", "+00:00"))
            age = now - created
            if age > timedelta(minutes=self.config.max_signal_age_minutes):
                return RiskDecision(
                    allow=False,
                    reason_code="stale_signal",
                    message="Signal is older than allowed window.",
                    details={"age_seconds": age.total_seconds()},
                )
        except ValueError:
            return RiskDecision(
                allow=False,
                reason_code="invalid_signal_timestamp",
                message="Signal timestamp is invalid.",
            )

        open_positions_list = [p for p in open_positions if p.is_open()]
        if len(open_positions_list) >= self.config.max_concurrent_positions:
            return RiskDecision(
                allow=False,
                reason_code="max_positions",
                message="Max concurrent positions reached.",
                details={"open_positions": len(open_positions_list)},
            )

        # One open position per market/outcome in this strategy.
        for p in open_positions_list:
            if p.market_id == signal.market_id and p.outcome_name == signal.outcome_name:
                return RiskDecision(
                    allow=False,
                    reason_code="duplicate_market_exposure",
                    message="Existing open position for this market/outcome.",
                    details={"position_id": p.position_id},
                )

        cooldown_until = self._cooldown_by_market.get(signal.market_id)
        if cooldown_until and now < cooldown_until:
            return RiskDecision(
                allow=False,
                reason_code="cooldown",
                message="Market is in cooldown window.",
                details={"cooldown_until": cooldown_until.isoformat()},
            )

        return RiskDecision(
            allow=True,
            reason_code="ok",
            message="Signal approved by risk engine.",
        )

    def mark_market_cooldown(self, market_id: str, now_utc: Optional[datetime] = None) -> None:
        now = now_utc or datetime.now(timezone.utc)
        self._cooldown_by_market[market_id] = now + timedelta(seconds=self.config.cooldown_seconds)
