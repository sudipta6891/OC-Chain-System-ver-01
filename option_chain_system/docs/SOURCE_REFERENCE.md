# Source Reference

This document maps every source/settings file in `option_chain_system` to its purpose.

## Root Scripts and Settings
- `.env`: runtime environment values (local, sensitive).
- `.env.example`: documented template for `.env`.
- `.env.full_mode.example`: minimal full-enhancement profile.
- `check_runtime.py`: validates flags and DB readiness; optional schema auto-apply.
- `run_engine.py`: main per-symbol analytics pipeline orchestrator.
- `scheduler.py`: APScheduler entrypoint and market-time scheduling.
- `run_historical_test.py`: historical replay script entrypoint.
- `historical_test_runner.py`: replay analytics/report generation from DB snapshots.
- `run_walk_forward_backtest.py`: CLI wrapper for walk-forward backtest.
- `requirements.txt`: Python dependency list.

## Config
- `config/settings.py`: environment loader, typed settings, feature flags.
- `config/symbols.py`: symbol universe.
- `config/__init__.py`: config package marker.

## Data Layer
- `data_layer/fyers_auth.py`: authenticated FYERS client builder.
- `data_layer/data_fetcher.py`: spot/option-chain fetch and normalization.
- `data_layer/generate_token.py`: manual helper to generate FYERS access token.

## Analytics
- `analytics/basic_analysis.py`: ATM split, total OI, PCR.
- `analytics/advanced_analysis.py`: OI support/resistance and max-pain.
- `analytics/interpretation_engine.py`: writing/trap interpretation.
- `analytics/breakout_engine.py`: breakout and short-covering classification.
- `analytics/volume_engine.py`: volume spike detection.
- `analytics/probability_engine.py`: base directional probability model.
- `analytics/scalp_engine.py`: OTM scalp scoring engine.
- `analytics/intraday_engine.py`: next-15/30/60 outlook text.
- `analytics/intraday_oi_engine.py`: OI delta + acceleration.
- `analytics/institutional_confidence_engine.py`: directional confidence score.
- `analytics/market_bias_engine.py`: multi-factor bias scorecard.
- `analytics/option_geeks_engine.py`: Greeks-style metrics and timing.
- `analytics/data_quality_engine.py`: data guardrails.
- `analytics/market_regime_engine.py`: regime classifier (`TREND/RANGE/VOLATILE/TRAP`).
- `analytics/otm_timing_engine_v2.py`: timing gate with blockers.
- `analytics/dynamic_otm_selector.py`: dynamic strike selection.
- `analytics/probability_calibration_engine.py`: Platt + isotonic calibration.
- `analytics/otm_selector.py`: legacy fixed-distance OTM selector (kept for compatibility).

## Database
- `database/db_connection.py`: PostgreSQL connection pool.
- `database/snapshot_repository.py`: inserts chain snapshots.
- `database/summary_repository.py`: inserts summary rows.
- `database/scalp_repository.py`: inserts scalp score rows.
- `database/market_context_repository.py`: context reads for regime/backtest.
- `database/trade_signal_repository.py`: inserts candidate trade signals.
- `database/trade_outcome_repository.py`: outcome labeling and performance reads.
- `database/cleanup_manager.py`: retention cleanup scheduler hook.
- `database/apply_schema.py`: applies schema SQL to DB.
- `database/schema.sql`: main schema (snapshot/summary/signals/outcomes).
- `database/scalp_score_tracking schema_create.sql`: scalp table DDL.
- `database/test_data_remove_one_time_sample.sql`: one-time cleanup sample SQL.

## Reporting
- `reporting/report_builder.py`: HTML report composition.
- `reporting/email_service.py`: SMTP sender.

## Backtesting
- `backtesting/walk_forward_backtester.py`: trade-path simulation, metrics, drawdown.

## Tests
- `test_auth.py`: auth client construction test.
- `test_config.py`: settings presence test.
- `test_db.py`: connection pool initialization test.
- `test_fetch.py`: data quality engine test.
- `test_oi_delta.py`: OI delta default response test.
- `test_scalp_repo.py`: scalp signal behavior test.

## Runtime Artifacts (Not Source)
- `fyersApi.log`, `fyersRequests.log`: API logs.
- `venv/`, `__pycache__/`: environment/artifact directories.

