"""Paper execution simulator with deterministic fill/fee/slippage model."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..config import TradingConfig
from ..models import ExecutionResult, OrderIntent
from .base import ExecutionAdapter


class PaperExecutionAdapter(ExecutionAdapter):
    """Paper execution adapter used for safe first-phase auto-trading."""

    def __init__(self, config: TradingConfig) -> None:
        self.config = config

    def execute(self, intent: OrderIntent) -> ExecutionResult:
        # Deterministic pseudo-random fill ratio based on signal + market id.
        # This provides stable behavior for tests and reproducible simulations.
        h = hashlib.sha256(f"{intent.signal_id}|{intent.market_id}".encode("utf-8")).hexdigest()
        deterministic_unit = int(h[:8], 16) / 0xFFFFFFFF
        fill_ratio = min(self.config.max_fill_ratio, max(0.2, deterministic_unit))

        filled_size = round(intent.requested_size_usd * fill_ratio, 8)
        requested_price = max(intent.requested_price, 0.0001)
        slippage_multiplier = 1 + (self.config.slippage_bps / 10_000.0)

        if intent.side == "BUY":
            fill_price = requested_price * slippage_multiplier
        else:
            fill_price = requested_price / slippage_multiplier

        notional = filled_size
        fees = notional * (self.config.fee_bps / 10_000.0)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        return ExecutionResult(
            ok=True,
            order_id=f"paper-{intent.signal_id[:10]}",
            signal_id=intent.signal_id,
            market_id=intent.market_id,
            side=intent.side,
            order_type=intent.order_type,
            filled_size_usd=filled_size,
            fill_price=round(fill_price, 8),
            fees_usd=round(fees, 8),
            slippage_bps=self.config.slippage_bps,
            timestamp=now,
            status="filled" if fill_ratio >= 0.999 else "partial_fill",
            metadata={"fill_ratio": round(fill_ratio, 6)},
        )
