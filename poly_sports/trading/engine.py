"""Auto-trading orchestration loop for paper/live adapters."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from poly_sports.data_fetching.fetch_odds_comparison import main as refresh_comparison_pipeline
from poly_sports.processing.arbitrage_calculation import detect_arbitrage_opportunities
from poly_sports.utils.file_utils import load_json, save_json
from poly_sports.utils.logger import logger

from .config import TradingConfig
from .decision_engine import (
    build_signals,
    latest_price_map_from_opportunities,
    opportunity_from_dict,
    should_open_signal,
)
from .execution import PaperExecutionAdapter, PolymarketLiveExecutionAdapter
from .journal import TradeJournal
from .models import OrderIntent, Position, utc_now_iso
from .position_manager import PositionManager
from .risk_engine import RiskEngine


class AutoTraderEngine:
    """Coordinates data->signal->risk->execute->monitor->journal."""

    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self.config.validate()
        self.journal = TradeJournal(config.journal_dir)
        self.risk = RiskEngine(config)
        self.position_manager = PositionManager(config)
        self.positions: Dict[str, Position] = {}
        self.seen_signal_ids = self.journal.load_seen_entry_signal_ids()
        self.realized_pnl_today = 0.0
        self._state_path = Path(config.journal_dir) / "state.json"

        if config.trading_mode == "paper":
            self.execution_adapter = PaperExecutionAdapter(config)
        else:
            self.execution_adapter = PolymarketLiveExecutionAdapter()

        self._load_state()

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return
        state = load_json(str(self._state_path))
        for row in state.get("positions", []):
            p = Position(**row)
            self.positions[p.position_id] = p
        self.realized_pnl_today = float(state.get("realized_pnl_today", 0.0))

    def _save_state(self) -> None:
        save_json(
            {
                "updated_at": utc_now_iso(),
                "realized_pnl_today": self.realized_pnl_today,
                "positions": [p.to_dict() for p in self.positions.values()],
            },
            str(self._state_path),
        )

    def _load_comparison_data(self) -> List[dict]:
        if self.config.refresh_comparison_each_cycle:
            logger.info("Refreshing comparison data pipeline...")
            refresh_comparison_pipeline()
        data = load_json(self.config.comparison_data_path)
        if not isinstance(data, list):
            raise ValueError("Comparison data must be a list")
        return data

    def _build_cycle_bucket(self) -> str:
        now = datetime.now(timezone.utc)
        minute_bucket = (now.minute // max(1, self.config.cycle_interval_seconds // 60)) * max(
            1, self.config.cycle_interval_seconds // 60
        )
        return now.replace(minute=minute_bucket, second=0, microsecond=0).isoformat()

    def run_cycle(self) -> Dict[str, int]:
        comparison_data = self._load_comparison_data()
        raw_opps = detect_arbitrage_opportunities(
            comparison_data,
            min_profit_threshold=self.config.min_profit_threshold,
            min_liquidity=self.config.min_liquidity_usd,
        )
        opportunities = [opportunity_from_dict(row) for row in raw_opps]
        latest_prices = latest_price_map_from_opportunities(opportunities)
        cycle_bucket = self._build_cycle_bucket()
        signals = build_signals(opportunities, cycle_bucket)

        opened = 0
        denied = 0
        skipped_duplicate = 0
        closed = 0

        for signal in signals:
            self.journal.log_signal(signal.to_dict())
            if not should_open_signal(signal.signal_id, self.seen_signal_ids):
                skipped_duplicate += 1
                self.journal.log_risk(
                    {
                        "timestamp": utc_now_iso(),
                        "signal_id": signal.signal_id,
                        "market_id": signal.market_id,
                        "allow": False,
                        "reason_code": "duplicate_signal",
                        "message": "Signal already processed earlier.",
                    }
                )
                continue

            decision = self.risk.evaluate_entry(
                signal=signal,
                open_positions=self.positions.values(),
                realized_pnl_today_usd=self.realized_pnl_today,
            )
            self.journal.log_risk(
                {
                    "timestamp": utc_now_iso(),
                    "signal_id": signal.signal_id,
                    "market_id": signal.market_id,
                    **decision.to_dict(),
                }
            )
            if not decision.allow:
                denied += 1
                continue

            intent = OrderIntent(
                signal_id=signal.signal_id,
                market_id=signal.market_id,
                event_id=signal.event_id,
                outcome_name=signal.outcome_name,
                side=signal.side,
                order_type="ENTRY",
                requested_price=signal.suggested_price,
                requested_size_usd=self.config.stake_per_trade_usd,
                created_at=utc_now_iso(),
                metadata={"cycle_bucket": cycle_bucket},
            )
            self.journal.log_order(intent.to_dict())

            if self.config.dry_run:
                self.journal.log_fill(
                    {
                        "timestamp": utc_now_iso(),
                        "signal_id": signal.signal_id,
                        "order_type": "ENTRY",
                        "status": "dry_run_skipped",
                    }
                )
                continue

            exec_result = self.execution_adapter.execute(intent)
            self.journal.log_fill(exec_result.to_dict())
            if exec_result.ok and exec_result.filled_size_usd > 0:
                pos = self.position_manager.open_position(signal, exec_result)
                self.positions[pos.position_id] = pos
                self.journal.log_position(
                    {"timestamp": utc_now_iso(), "event": "opened", **pos.to_dict()}
                )
                opened += 1

        # Exit cycle for open positions.
        for position in list(self.positions.values()):
            if not position.is_open():
                continue
            latest_price = latest_prices.get((position.market_id, position.outcome_name))
            decision = self.position_manager.evaluate_exit(position, latest_price)
            if not decision.should_exit:
                # Track unrealized snapshot when price is available.
                if decision.latest_price is not None:
                    unrealized = position.size_usd * ((decision.latest_price / position.entry_price) - 1)
                    position.unrealized_pnl_usd = round(unrealized, 8)
                continue

            intent = OrderIntent(
                signal_id=position.signal_id,
                market_id=position.market_id,
                event_id=position.event_id,
                outcome_name=position.outcome_name,
                side="SELL" if position.side == "BUY" else "BUY",
                order_type="EXIT",
                requested_price=decision.latest_price or position.entry_price,
                requested_size_usd=position.size_usd,
                created_at=utc_now_iso(),
                metadata={"exit_reason": decision.reason},
            )
            self.journal.log_order(intent.to_dict())

            if self.config.dry_run:
                continue

            exec_result = self.execution_adapter.execute(intent)
            self.journal.log_fill(exec_result.to_dict())
            if exec_result.ok:
                closed_position = self.position_manager.close_position(
                    position,
                    exec_result,
                    exit_reason=decision.reason,
                )
                self.positions[closed_position.position_id] = closed_position
                self.realized_pnl_today += closed_position.realized_pnl_usd
                self.journal.log_position(
                    {"timestamp": utc_now_iso(), "event": "closed", **closed_position.to_dict()}
                )
                self.risk.mark_market_cooldown(position.market_id)
                closed += 1

        self._save_state()
        summary = {
            "signals": len(signals),
            "opened": opened,
            "closed": closed,
            "denied": denied,
            "duplicates": skipped_duplicate,
            "open_positions": len([p for p in self.positions.values() if p.is_open()]),
        }
        logger.info(f"Auto-trader cycle summary: {summary}")
        return summary
