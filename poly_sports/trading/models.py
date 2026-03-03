"""Core trading domain models used by the paper/live engines."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional


OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["ENTRY", "EXIT"]
PositionStatus = Literal["OPEN", "CLOSED"]


@dataclass(slots=True)
class Opportunity:
    """Normalized directional opportunity from arbitrage detection."""

    market_id: str
    event_id: str
    outcome_name: str
    entry_price: float
    target_price: float
    expected_profit_pct: float
    liquidity: float
    spread: float
    confidence: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Signal:
    """Actionable signal derived from an opportunity."""

    signal_id: str
    market_id: str
    event_id: str
    outcome_name: str
    side: OrderSide
    order_type: OrderType
    suggested_price: float
    target_price: float
    confidence: float
    expected_profit_pct: float
    liquidity: float
    spread: float
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RiskDecision:
    """Result returned by risk engine."""

    allow: bool
    reason_code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OrderIntent:
    """Order intent created after risk approval."""

    signal_id: str
    market_id: str
    event_id: str
    outcome_name: str
    side: OrderSide
    order_type: OrderType
    requested_price: float
    requested_size_usd: float
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionResult:
    """Execution adapter response."""

    ok: bool
    order_id: str
    signal_id: str
    market_id: str
    side: OrderSide
    order_type: OrderType
    filled_size_usd: float
    fill_price: float
    fees_usd: float
    slippage_bps: float
    timestamp: str
    status: str = "filled"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Position:
    """Open/closed position maintained by the position manager."""

    position_id: str
    signal_id: str
    market_id: str
    event_id: str
    outcome_name: str
    side: OrderSide
    status: PositionStatus
    size_usd: float
    entry_price: float
    entry_time: str
    target_price: float
    stop_loss_price: float
    take_profit_price: float
    max_holding_minutes: int
    entry_fees_usd: float = 0.0
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    exit_reason: Optional[str] = None
    exit_fees_usd: float = 0.0
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_open(self) -> bool:
        return self.status == "OPEN"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExitDecision:
    """Exit recommendation emitted by the position manager."""

    should_exit: bool
    reason: str
    latest_price: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    """Return utc timestamp in ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
