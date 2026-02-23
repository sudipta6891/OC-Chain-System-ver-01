# Testing and Validation

## Unit Tests
Run from `option_chain_system` directory:
- `python -m unittest discover -p "test_*.py" -v`

Covered test modules:
- `test_fetch.py`: data quality behavior.
- `test_oi_delta.py`: OI delta defaults.
- `test_scalp_repo.py`: scalp signal expectation.
- `test_auth.py`: auth initialization (dependency-gated).
- `test_db.py`: DB pool initialization (dependency-gated).
- `test_config.py`: settings field presence (env-gated).

## Runtime Validation
- Environment-only check:
  - `python check_runtime.py --skip-db`
- Full readiness:
  - `python check_runtime.py`

## Strategy Validation
- Historical replay:
  - `python run_historical_test.py`
- Walk-forward:
  - `python run_walk_forward_backtest.py --as-json`

## Notes
- Some tests intentionally skip when optional dependencies/env are unavailable.
- For outcome-tracking validation, run with:
  - `TEST_MODE=False`
  - `ENABLE_OUTCOME_TRACKING=True`

