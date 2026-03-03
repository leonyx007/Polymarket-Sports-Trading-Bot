"""Integration smoke test for one paper trading cycle."""

from pathlib import Path

from poly_sports.trading.config import TradingConfig
from poly_sports.trading.engine import AutoTraderEngine
from poly_sports.utils.file_utils import save_json


def test_auto_trader_single_cycle(tmp_path: Path) -> None:
    comparison_path = tmp_path / "comparison.json"
    journal_dir = tmp_path / "journal"

    # Minimal comparison payload that yields one directional opportunity.
    save_json(
        [
            {
                "pm_event_id": "event-1",
                "pm_market_id": "market-1",
                "pm_market_outcomes": '["Team A", "Team B"]',
                "pm_market_outcomePrices": '["0.50", "0.50"]',
                "pm_event_liquidity": 10000,
                "pm_market_liquidityNum": 10000,
                "pm_spread": 0.01,
                "sportsbook_count": 3,
                "match_confidence": 0.9,
                "sportsbook_outcomes": [
                    {"name": "Team A", "avg_implied_probability": 0.515},
                    {"name": "Team B", "avg_implied_probability": 0.485},
                ],
            }
        ],
        str(comparison_path),
    )

    cfg = TradingConfig(
        trading_mode="paper",
        comparison_data_path=str(comparison_path),
        journal_dir=str(journal_dir),
        refresh_comparison_each_cycle=False,
        stake_per_trade_usd=20,
        min_profit_threshold=0.02,
        min_liquidity_usd=1000,
        min_confidence=0.7,
        max_spread=0.03,
    )
    engine = AutoTraderEngine(cfg)
    summary = engine.run_cycle()

    assert summary["signals"] >= 1
    assert summary["opened"] >= 1
    assert (journal_dir / "signals.jsonl").exists()
    assert (journal_dir / "orders.jsonl").exists()
    assert (journal_dir / "fills.jsonl").exists()
