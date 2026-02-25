# Developer Handbook

Version: consolidated from current project docs and settings references.

## Table of Contents
1. Project Overview
2. Architecture and Data Flow
3. Setup and Installation
4. Configuration and Feature Flags
5. Operations Runbook
6. Database Reference
7. Source Code Reference
8. Testing and Validation
9. Backtesting and Replay
10. Troubleshooting
11. Appendix: Environment Templates

## 1) Project Overview
Option Chain System is an automated option-chain analytics pipeline for index options.

Core capabilities:
- Fetches spot and option-chain data from FYERS.
- Runs multi-layer analytics (OI/PCR, breakout, bias, Greeks, timing, regime).
- Produces HTML reports for web viewing.
- Persists snapshots/summaries/signals/outcomes in PostgreSQL.
- Supports historical replay and walk-forward backtesting.

## 2) Architecture and Data Flow
High-level runtime path:
1. `data_layer/data_fetcher.py` fetches spot + option chain and normalizes fields.
2. `run_engine.py` orchestrates analytics modules in `analytics/`.
3. Feature-flagged enhancements apply:
   - guardrails
   - regime v2
   - timing v2
   - dynamic OTM picker
   - calibration
   - outcome tracking
4. Repositories in `database/` write snapshots/summaries/signals/outcomes.
5. `reporting/report_builder.py` composes report and `reporting/report_web_store.py` stores it for web viewing.
6. `scheduler.py` executes per market schedule.

## 3) Setup and Installation
1. Create virtual environment and install dependencies:
   - `pip install -r requirements.txt`
2. Create `.env` from `.env.example`.
3. Apply DB schema:
   - `python database/apply_schema.py`
4. Validate runtime:
   - `python check_runtime.py --apply-missing-schema`
5. Start scheduler:
   - `python scheduler.py`

## 4) Configuration and Feature Flags
Primary config loader:
- `config/settings.py`

Primary runtime values:
- `.env`

Important runtime variables:
- Credentials:
  - `FYERS_CLIENT_ID`, `FYERS_SECRET_KEY`, `FYERS_REDIRECT_URI`, `FYERS_ACCESS_TOKEN`
- Runtime:
  - `TIMEZONE`, `TEST_MODE`, `DATA_RETENTION_DAYS`, `OPTION_CHAIN_STRIKE_COUNT`
- DB:
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

Feature flags:
- `ENABLE_ALL_ENHANCEMENTS`:
  - Master switch; forces all enhancement flags on.
- `ENABLE_GUARDRAILS`
- `ENABLE_REGIME_V2`
- `ENABLE_TIMING_V2`
- `ENABLE_DYNAMIC_OTM`
- `ENABLE_OUTCOME_TRACKING`
- `ENABLE_CALIBRATION`
- `CALIBRATION_MIN_SAMPLES`

Recommended profiles:
- Progressive rollout:
  - `TEST_MODE=False`
  - `ENABLE_GUARDRAILS=True`
  - enable remaining flags one-by-one.
- Full enhanced mode:
  - `TEST_MODE=False`
  - `ENABLE_ALL_ENHANCEMENTS=True`
  - `CALIBRATION_MIN_SAMPLES=30`
  - `OPTION_CHAIN_STRIKE_COUNT=40`

## 5) Operations Runbook
Main operations:
- Scheduler:
  - `python scheduler.py`
- Runtime readiness:
  - `python check_runtime.py`
- Auto-fix schema then validate:
  - `python check_runtime.py --apply-missing-schema`
- Historical replay:
  - `python run_historical_test.py`
- Walk-forward backtest:
  - `python run_walk_forward_backtest.py --symbol NSE:NIFTYBANK-INDEX --start-date 2026-02-01 --end-date 2026-02-23`

Operational notes:
- Keep `TEST_MODE=False` when tracking outcomes.
- Calibration requires sufficient labeled samples.
- Scheduler prints feature flags at startup for confirmation.

## 6) Database Reference
Schema files:
- `database/schema.sql`
- `database/scalp_score_tracking schema_create.sql`

Tables:
- `option_chain_snapshot`:
  - raw chain rows by `snapshot_time`.
- `option_chain_summary`:
  - derived summary metrics by snapshot.
- `scalp_score_tracking`:
  - component scalp scores and labels.
- `trade_signals`:
  - candidate trade entries, timing, probabilities, risk params.
- `trade_outcomes`:
  - 10/30/60-minute outcome labels and return metrics.

Important indexes:
- `idx_snapshot_symbol_time`
- `idx_summary_symbol_time`
- `idx_scalp_symbol_time`
- `idx_trade_signals_symbol_time`
- `idx_trade_outcomes_signal`

Retention:
- managed by `database/cleanup_manager.py`
- controlled by `DATA_RETENTION_DAYS`

## 7) Source Code Reference
Root scripts:
- `run_engine.py`: core orchestration.
- `scheduler.py`: schedule and execution.
- `check_runtime.py`: env + DB readiness checks.
- `run_historical_test.py`: replay entry script.
- `run_walk_forward_backtest.py`: backtest CLI entry.

Config:
- `config/settings.py`
- `config/symbols.py`
- `config/__init__.py`

Data layer:
- `data_layer/fyers_auth.py`
- `data_layer/data_fetcher.py`
- `data_layer/generate_token.py`

Analytics:
- `analytics/basic_analysis.py`
- `analytics/advanced_analysis.py`
- `analytics/interpretation_engine.py`
- `analytics/breakout_engine.py`
- `analytics/volume_engine.py`
- `analytics/probability_engine.py`
- `analytics/scalp_engine.py`
- `analytics/intraday_engine.py`
- `analytics/intraday_oi_engine.py`
- `analytics/institutional_confidence_engine.py`
- `analytics/market_bias_engine.py`
- `analytics/option_geeks_engine.py`
- `analytics/data_quality_engine.py`
- `analytics/market_regime_engine.py`
- `analytics/otm_timing_engine_v2.py`
- `analytics/dynamic_otm_selector.py`
- `analytics/probability_calibration_engine.py`
- `analytics/otm_selector.py` (legacy compatibility)

Database repos/utilities:
- `database/db_connection.py`
- `database/snapshot_repository.py`
- `database/summary_repository.py`
- `database/scalp_repository.py`
- `database/market_context_repository.py`
- `database/trade_signal_repository.py`
- `database/trade_outcome_repository.py`
- `database/cleanup_manager.py`
- `database/apply_schema.py`

Reporting:
- `reporting/report_builder.py`
- `reporting/report_web_store.py`

Backtesting:
- `backtesting/walk_forward_backtester.py`

Tests:
- `test_auth.py`
- `test_config.py`
- `test_db.py`
- `test_fetch.py`
- `test_oi_delta.py`
- `test_scalp_repo.py`

## 8) Testing and Validation
Unit tests:
- Run from `option_chain_system`:
  - `python -m unittest discover -p "test_*.py" -v`

Runtime checks:
- Env-only:
  - `python check_runtime.py --skip-db`
- Full:
  - `python check_runtime.py`

Validation strategy:
- Use historical replay for qualitative behavior.
- Use walk-forward backtest for quantitative metrics.

## 9) Backtesting and Replay
Historical replay:
- `run_historical_test.py` and `historical_test_runner.py`
- Uses stored snapshots and summaries near requested timestamp.

Walk-forward backtest:
- `backtesting/walk_forward_backtester.py`
- Models:
  - slippage
  - transaction cost
  - stop-loss
  - target
  - time-stop
- CLI wrapper:
  - `run_walk_forward_backtest.py`

## 10) Troubleshooting
Missing tables:
- `python database/apply_schema.py`
- or `python check_runtime.py --apply-missing-schema`

No outcome rows:
- Ensure:
  - `TEST_MODE=False`
  - `ENABLE_OUTCOME_TRACKING=True`

Calibration stays identity:
- Ensure:
  - `ENABLE_CALIBRATION=True`
  - enough labeled samples (based on `CALIBRATION_MIN_SAMPLES`)

Too many low-quality entries:
- Ensure:
  - `ENABLE_TIMING_V2=True`
  - `ENABLE_GUARDRAILS=True`
- review runtime logs:
  - `Timing V2 Blockers`
  - `Regime Cautions`

## 11) Appendix: Environment Templates
### `.env.example`
```env
# ------------------------------
# FYERS Credentials
# ------------------------------
FYERS_CLIENT_ID=
FYERS_SECRET_KEY=
FYERS_REDIRECT_URI=
FYERS_ACCESS_TOKEN=

# ------------------------------
# Runtime
# ------------------------------
TIMEZONE=Asia/Kolkata
TEST_MODE=False
DATA_RETENTION_DAYS=7
OPTION_CHAIN_STRIKE_COUNT=40

# ------------------------------
# Feature Flags
# ------------------------------
ENABLE_ALL_ENHANCEMENTS=False
ENABLE_GUARDRAILS=True
ENABLE_REGIME_V2=False
ENABLE_TIMING_V2=False
ENABLE_DYNAMIC_OTM=False
ENABLE_OUTCOME_TRACKING=False
ENABLE_CALIBRATION=False
CALIBRATION_MIN_SAMPLES=30

# ------------------------------
# Database
# ------------------------------
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

```

### `.env.full_mode.example`
```env
TEST_MODE=False
ENABLE_ALL_ENHANCEMENTS=True
CALIBRATION_MIN_SAMPLES=30
OPTION_CHAIN_STRIKE_COUNT=40
```

## Optional: Export to PDF
If you have Pandoc installed, run:
- `pandoc docs/DEVELOPER_HANDBOOK.md -o docs/DEVELOPER_HANDBOOK.pdf`

