"""Unit tests for paper execution adapter."""

from poly_sports.trading.config import TradingConfig
from poly_sports.trading.execution.paper import PaperExecutionAdapter
from poly_sports.trading.models import OrderIntent


def test_paper_execution_returns_fill() -> None:
    cfg = TradingConfig(fee_bps=20, slippage_bps=10, max_fill_ratio=1.0)
    adapter = PaperExecutionAdapter(cfg)
    intent = OrderIntent(
        signal_id="sig-abc",
        market_id="mkt-1",
        event_id="evt-1",
        outcome_name="Team A",
        side="BUY",
        order_type="ENTRY",
        requested_price=0.5,
        requested_size_usd=100,
        created_at="2026-01-01T00:00:00Z",
    )
    result = adapter.execute(intent)
    assert result.ok is True
    assert result.order_id.startswith("paper-")
    assert result.filled_size_usd > 0
    assert result.fill_price > intent.requested_price
    assert result.fees_usd > 0


def test_paper_execution_is_deterministic_for_same_signal() -> None:
    cfg = TradingConfig(max_fill_ratio=0.8)
    adapter = PaperExecutionAdapter(cfg)
    intent = OrderIntent(
        signal_id="sig-fixed",
        market_id="mkt-fixed",
        event_id="evt-1",
        outcome_name="Team A",
        side="BUY",
        order_type="ENTRY",
        requested_price=0.5,
        requested_size_usd=42,
        created_at="2026-01-01T00:00:00Z",
    )
    a = adapter.execute(intent)
    b = adapter.execute(intent)
    assert a.filled_size_usd == b.filled_size_usd
    assert a.fill_price == b.fill_price
