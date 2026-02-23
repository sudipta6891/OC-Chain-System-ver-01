# Operations Runbook

## 1) Initial Setup
1. Create virtual environment and install dependencies:
   - `pip install -r requirements.txt`
2. Create `.env` from `.env.example`.
3. Apply DB schema:
   - `python database/apply_schema.py`
4. Validate runtime:
   - `python check_runtime.py --apply-missing-schema`

## 2) Running the System
- Scheduler mode:
  - `python scheduler.py`
- Single-run debug:
  - `python run_engine.py` (via importer call from your script/test harness)

## 3) Test/Replay Utilities
- Historical replay:
  - `python run_historical_test.py`
- Walk-forward backtest:
  - `python run_walk_forward_backtest.py --symbol NSE:NIFTYBANK-INDEX --start-date 2026-02-01 --end-date 2026-02-23`

## 4) Runtime Checks
- Settings and DB readiness:
  - `python check_runtime.py`
- Auto-fix missing schema and re-check:
  - `python check_runtime.py --apply-missing-schema`

## 5) Feature Rollout
- Progressive rollout:
  - Toggle one `ENABLE_*` flag at a time in `.env`.
- Full enhancement mode:
  - Set `ENABLE_ALL_ENHANCEMENTS=True`.

## 6) Common Issues
- Missing DB tables:
  - Run `python database/apply_schema.py`.
- Outcome tracking not writing:
  - Ensure `TEST_MODE=False` and `ENABLE_OUTCOME_TRACKING=True`.
- Calibration stays identity:
  - Confirm enough labeled samples and `ENABLE_CALIBRATION=True`.

