"""Summarize paper/live trading journals for quick diagnostics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from poly_sports.trading.journal import TradeJournal
from poly_sports.utils.logger import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize trading session from JSONL journals")
    parser.add_argument("--journal-dir", default="data/trading", help="Journal directory path")
    return parser.parse_args()


def _safe_float(v: object) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    args = parse_args()
    journal = TradeJournal(args.journal_dir)

    fills = journal.load_entries("fills")
    orders = journal.load_entries("orders")
    positions = journal.load_entries("positions")
    risks = journal.load_entries("risk")

    closed_positions = [p for p in positions if p.get("event") == "closed"]
    opened_positions = [p for p in positions if p.get("event") == "opened"]

    realized = sum(_safe_float(p.get("realized_pnl_usd")) for p in closed_positions)
    wins = sum(1 for p in closed_positions if _safe_float(p.get("realized_pnl_usd")) > 0)
    losses = sum(1 for p in closed_positions if _safe_float(p.get("realized_pnl_usd")) < 0)
    total_fees = sum(_safe_float(f.get("fees_usd")) for f in fills)
    avg_slippage = (
        sum(_safe_float(f.get("slippage_bps")) for f in fills) / len(fills) if fills else 0.0
    )

    deny_reasons: dict[str, int] = {}
    for row in risks:
        if row.get("allow") is False:
            reason = str(row.get("reason_code", "unknown"))
            deny_reasons[reason] = deny_reasons.get(reason, 0) + 1

    logger.info("=" * 80)
    logger.info("Trading Session Summary")
    logger.info("=" * 80)
    logger.info(f"Journal dir: {Path(args.journal_dir).resolve()}")
    logger.info(f"Orders: {len(orders)}")
    logger.info(f"Fills: {len(fills)}")
    logger.info(f"Positions opened: {len(opened_positions)}")
    logger.info(f"Positions closed: {len(closed_positions)}")
    logger.info(f"Wins: {wins} | Losses: {losses}")
    logger.info(f"Realized PnL (USD): {realized:.4f}")
    logger.info(f"Total fees (USD): {total_fees:.4f}")
    logger.info(f"Avg slippage (bps): {avg_slippage:.2f}")
    if deny_reasons:
        logger.info("Top risk deny reasons:")
        for reason, count in sorted(deny_reasons.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  - {reason}: {count}")


if __name__ == "__main__":
    main()
