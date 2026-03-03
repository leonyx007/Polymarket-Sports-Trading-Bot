# Polymarket Sports Arbitrage Bot
Production-style toolkit for sports market analytics and paper auto-trading.
This project compares Polymarket sports prices with sportsbook implied probabilities, finds directional opportunities, and runs a guarded paper trading loop with audit logs.

## Table of Contents
- Overview
- Core Features
- Architecture
- Prerequisites
- Installation
- Configuration
- Pipeline Commands
- Auto-Trading Commands
- Risk Controls
- Outputs and Journals
- Recommended Workflow
- Troubleshooting
- Testing
- Project Structure
- Documentation
- License

## Overview
The repository has two layers:
1) Analytics layer
- fetches Polymarket sports markets,
- fetches sportsbook odds,
- matches events/outcomes,
- computes directional opportunities.
2) Trading layer (paper-first)
- normalizes opportunities into signals,
- runs deterministic risk gates,
- simulates fills in paper mode,
- manages exits and positions,
- stores append-only JSONL journals.
This is directional value trading, not guaranteed risk-free arbitrage.

## Core Features
- Polymarket Gamma API ingestion
- Optional CLOB read-only enrichment
- Sportsbook odds ingestion and normalization
- Fuzzy event matching with confidence scores
- Directional edge ranking by expected value
- Paper execution adapter with deterministic behavior
- Position lifecycle rules (TP/SL/max-hold)
- JSON/CSV exports and JSONL audit logs

## Architecture
Packages:
- `poly_sports/data_fetching/` (fetch and compare)
- `poly_sports/processing/` (matching and edge logic)
- `poly_sports/trading/` (models, config, decision, risk, execution, journal, positions)
- `scripts/` (operational command entrypoints)
Core flow:
1. Fetch markets -> `data/arbitrage_data*.json`
2. Compare with sportsbook odds -> `data/arbitrage_comparison.json`
3. Detect opportunities -> `data/directional_arbitrage.json`
4. Run trader -> `data/trading/*.jsonl` and `state.json`

## Prerequisites
- Python 3.9+ (3.12 recommended)
- `venv` support
- `ODDS_API_KEY`
No private key is required for paper mode.

## Installation
From repo root:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```
Create local env file:
```bash
cp .env.example .env
```

## Configuration
Minimum `.env`:
```env
ODDS_API_KEY=your_odds_api_key_here
TRADING_MODE=paper
ENABLE_LIVE_TRADING=false
TRADING_DRY_RUN=true
```

### Pipeline variables
| Variable | Default | Description |
|---|---|---|
| `ODDS_API_KEY` | - | Required sportsbook API key |
| `GAMMA_API_URL` | `https://gamma-api.polymarket.com` | Polymarket source |
| `CLOB_HOST` | `https://clob.polymarket.com` | CLOB endpoint |
| `ENRICH_WITH_CLOB` | `false` | Include CLOB market metadata |
| `USE_STORED_EVENTS` | `false` | Reuse cached sportsbook events |
| `OUTPUT_DIR` | `data` | Output directory |

### Trading variables
| Variable | Default | Description |
|---|---|---|
| `TRADING_MODE` | `paper` | Trading mode (`paper` / `live`) |
| `ENABLE_LIVE_TRADING` | `false` | Hard guard for live mode |
| `TRADING_DRY_RUN` | `true` | Log-only execution mode |
| `TRADING_STAKE_USD` | `25` | Stake per entry |
| `TRADING_MAX_POSITIONS` | `5` | Max concurrent positions |
| `TRADING_MAX_DAILY_LOSS_USD` | `100` | Daily kill-switch |
| `TRADING_MIN_PROFIT` | `0.02` | Minimum expected edge |
| `TRADING_MIN_CONFIDENCE` | `0.75` | Minimum match confidence |
| `TRADING_MIN_LIQUIDITY_USD` | `2000` | Liquidity gate |
| `TRADING_MAX_SPREAD` | `0.03` | Spread gate |
| `TRADING_CYCLE_SECONDS` | `60` | Loop interval |
| `TRADING_COOLDOWN_SECONDS` | `300` | Post-close cooldown |
| `TRADING_COMPARISON_PATH` | `data/arbitrage_comparison.json` | Signal input file |
| `TRADING_JOURNAL_DIR` | `data/trading` | Journal output path |

## Pipeline Commands
Run the full data pipeline:
```bash
source .venv/bin/activate
python -m poly_sports.data_fetching.fetch_sports_markets
python -m poly_sports.data_fetching.fetch_sports_markets filter data/arbitrage_data.json data
python -m poly_sports.data_fetching.fetch_odds_comparison
python scripts/run_arbitrage_detection.py --sort-by profit_margin
```
Key artifacts:
- `data/arbitrage_data_filtered.json`
- `data/arbitrage_comparison.json`
- `data/directional_arbitrage.json`

## Auto-Trading Commands
One-cycle dry run:
```bash
python scripts/run_auto_trader.py --cycles 1 --dry-run
```
Continuous paper run:
```bash
python scripts/run_auto_trader.py
```
Session summary:
```bash
python scripts/summarize_trading_session.py --journal-dir data/trading
```
Live execution is intentionally guarded by config and adapter checks.

### Sample Output
![Auto-trader and arbitrage output](/root/.cursor/projects/root-work/assets/c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_73128371978e98cf0786f3f5f206193e_images_image-9d0cdd5a-08d4-4723-a47f-cef9a96f778b.png)

## Risk Controls
Signals can be denied for:
- low confidence,
- low liquidity,
- high spread,
- stale signal age,
- max position cap reached,
- duplicate market exposure,
- daily loss limit reached,
- cooldown not elapsed.
All decisions are written to `risk_events.jsonl` for audit and tuning.

## Outputs and Journals
Standard output files:
- `data/sports_markets.json`
- `data/arbitrage_data.json`
- `data/arbitrage_data_filtered.json`
- `data/arbitrage_comparison.json`
- `data/directional_arbitrage.json`
Trading journals in `data/trading/`:
- `signals.jsonl`
- `risk_events.jsonl`
- `orders.jsonl`
- `fills.jsonl`
- `positions.jsonl`
- `state.json`
Use journals as authoritative lifecycle history.

## Recommended Workflow
1. Refresh comparison data.
2. Run one-cycle dry run.
3. Inspect `risk_events.jsonl` deny reasons.
4. Tune thresholds gradually.
5. Run continuous paper mode.
6. Validate consistency across multiple days before any live path work.

## Troubleshooting
### `python: command not found`
Use `python3` or activate venv:
```bash
source .venv/bin/activate
python ...
```
### `ModuleNotFoundError`
Usually the shell is outside `.venv`; activate it again.
### Low match rate
Usually a matching-quality issue (naming/time/coverage mismatch), not a crash.
### Auto-trader shows `opened: 0`
Common causes:
- `TRADING_DRY_RUN=true`,
- all signals denied by risk filters,
- duplicate/idempotent suppression.

## Testing
Run full tests:
```bash
pytest tests/ -v
```
Run trading-focused tests:
```bash
pytest tests/test_trading_*.py -q
```

## Project Structure
```text
Polymarket-Sports-Arbitrage-Bot/
├── poly_sports/
│   ├── data_fetching/
│   ├── processing/
│   ├── trading/
│   │   ├── execution/
│   │   ├── config.py
│   │   ├── decision_engine.py
│   │   ├── engine.py
│   │   ├── journal.py
│   │   ├── models.py
│   │   ├── position_manager.py
│   │   └── risk_engine.py
│   └── utils/
├── scripts/
├── tests/
├── docs/
└── data/
```

## Documentation
- `docs/ARBITRAGE_CALCULATION.md` (edge and delta formulas)
- `docs/TRADING_ENGINE.md` (engine lifecycle and journal schema)

## License
Add your preferred license (for example MIT) and include a `LICENSE` file in the repository root.
