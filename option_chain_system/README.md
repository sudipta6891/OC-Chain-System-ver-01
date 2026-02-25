# Option Chain System

Automated option-chain analytics and reporting pipeline for index options.

## What This Project Does
- Fetches spot and option-chain data from FYERS.
- Computes analytics signals (OI/PCR, breakout, bias, Greeks, timing, regime).
- Generates actionable HTML web reports.
- Stores snapshots and derived signals in PostgreSQL.
- Tracks trade outcomes and supports walk-forward backtesting.

## Documentation Index
- `docs/DEVELOPER_HANDBOOK.md`: single consolidated handbook.
- `docs/SETTINGS.md`: full environment variable and flag reference.
- `docs/SOURCE_REFERENCE.md`: file-by-file source code map.
- `docs/OPERATIONS.md`: runbook for setup, runtime, and maintenance.
- `docs/DATABASE.md`: schema and table usage.
- `docs/TESTING.md`: tests and validation commands.

## Quick Start
1. Create and fill `.env` using `.env.example`.
2. Install dependencies from `requirements.txt`.
3. Apply schema:
   - `python database/apply_schema.py`
4. Validate runtime:
   - `python check_runtime.py --apply-missing-schema`
5. Start scheduler:
   - `python scheduler.py`
6. View reports in browser:
   - `python serve_reports.py --host 127.0.0.1 --port 8080`
   - open `http://127.0.0.1:8080`

## Modes
- Progressive flags (recommended during rollout):
  - `ENABLE_GUARDRAILS`, `ENABLE_OUTCOME_TRACKING`, `ENABLE_TIMING_V2`, `ENABLE_REGIME_V2`, `ENABLE_DYNAMIC_OTM`, `ENABLE_CALIBRATION`.
- Full-stack mode:
  - Set `ENABLE_ALL_ENHANCEMENTS=True`.

## Notes
- Keep `TEST_MODE=False` when you need DB writes for signal/outcome tracking.
- Every cycle also writes HTML report files under `reports/web/` for web viewing.
- `venv/` and `__pycache__/` are runtime artifacts and are not part of source documentation scope.
