# Trading Engine (Paper-First)

## Overview

The trading engine consumes directional opportunities produced by the existing
pipeline and executes a guarded entry/exit lifecycle.

Current rollout status:
- Phase 1: paper execution enabled
- Phase 2: live execution adapter stubbed but disabled by default

## Components

- `poly_sports/trading/config.py`
  - Env-driven configuration and guard validation
- `poly_sports/trading/decision_engine.py`
  - Opportunity normalization, signal building, idempotency keys
- `poly_sports/trading/risk_engine.py`
  - Deterministic entry allow/deny checks
- `poly_sports/trading/execution/paper.py`
  - Paper fills with slippage/fee/fill-ratio model
- `poly_sports/trading/position_manager.py`
  - Position open/monitor/close logic and exit decisions
- `poly_sports/trading/journal.py`
  - Append-only JSONL trade/risk audit logs
- `poly_sports/trading/engine.py`
  - Cycle orchestrator tying all components together

## Cycle Data Flow

1. Load comparison data (`data/arbitrage_comparison.json` by default)
2. Detect opportunities (`detect_arbitrage_opportunities`)
3. Convert opportunities -> signals
4. Apply risk gate
5. Execute approved signals (paper/live adapter)
6. Create/update positions
7. Evaluate exits (TP/SL/timeout/target)
8. Persist state and journals

## Risk Rules (Entry)

- Daily realized loss cap
- Minimum liquidity
- Maximum spread
- Minimum confidence
- Signal freshness (max age)
- Max concurrent positions
- One open position per market/outcome
- Market cooldown after exits

## Journal Files

All files are append-only JSONL under `data/trading/`:

- `signals.jsonl` — all generated signals
- `orders.jsonl` — entry/exit intents
- `fills.jsonl` — execution results (or dry-run skips)
- `positions.jsonl` — opened/closed position snapshots
- `risk_events.jsonl` — allow/deny decisions with reason codes

State snapshot:
- `data/trading/state.json` keeps latest position state and realized PnL.

## Running

Dry-run one cycle:

```bash
python scripts/run_auto_trader.py --cycles 1 --dry-run
```

Paper loop:

```bash
python scripts/run_auto_trader.py
```

Session summary:

```bash
python scripts/summarize_trading_session.py --journal-dir data/trading
```

## Live Mode Safety

Live mode remains blocked by default.

To even request live mode:
- `TRADING_MODE=live`
- `ENABLE_LIVE_TRADING=true`

The current live adapter is intentionally a guarded placeholder and does not
place orders. Implement and test thoroughly before any production usage.
