"""Run auto-trading orchestrator (paper-first by default)."""
from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from poly_sports.trading.config import TradingConfig
from poly_sports.trading.engine import AutoTraderEngine
from poly_sports.utils.logger import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run auto-trader loop")
    parser.add_argument("--cycles", type=int, default=0, help="Number of cycles to run (0 = infinite)")
    parser.add_argument("--dry-run", action="store_true", help="Log decisions only; do not execute entries/exits")
    parser.add_argument("--interval", type=int, default=None, help="Override cycle interval seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = TradingConfig.from_env()
    if args.interval is not None:
        config.cycle_interval_seconds = args.interval
    if args.dry_run:
        config.dry_run = True
    try:
        config.validate()
    except ValueError as exc:
        logger.error(f"{exc}")
        logger.error("Auto Trader blocked by configuration guardrails.")
        return

    try:
        engine = AutoTraderEngine(config)
    except Exception as exc:
        logger.error(f"Failed to initialize auto-trader engine: {exc}")
        return
    stop = {"value": False}

    def _handle_stop(_sig: int, _frame: object) -> None:
        stop["value"] = True

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    logger.info("=" * 80)
    logger.info("Auto Trader Started")
    logger.info("=" * 80)
    logger.info(
        f"mode={config.trading_mode} dry_run={config.dry_run} interval={config.cycle_interval_seconds}s"
    )

    ran = 0
    while not stop["value"]:
        if args.cycles and ran >= args.cycles:
            break
        try:
            engine.run_cycle()
        except Exception as exc:  # pragma: no cover - safety log path
            logger.error(f"Auto-trader cycle failed: {exc}")
        ran += 1
        if args.cycles and ran >= args.cycles:
            break
        time.sleep(max(1, config.cycle_interval_seconds))

    logger.info(f"Auto Trader stopped after {ran} cycle(s)")


if __name__ == "__main__":
    main()
