# Settings Reference

Primary configuration file: `config/settings.py`  
Primary runtime source: `.env` (not committed)  
Template: `.env.example`

## Core Runtime
- `FYERS_CLIENT_ID`: FYERS app client ID.
- `FYERS_SECRET_KEY`: FYERS app secret.
- `FYERS_REDIRECT_URI`: redirect URI configured in FYERS app.
- `FYERS_ACCESS_TOKEN`: active access token used for API calls.
- `TIMEZONE`: runtime timezone (default `Asia/Kolkata`).
- `TEST_MODE`: `True`/`False`; test mode skips key DB writes in engine flow.
- `TEST_INTERVAL_MINUTES`: test-mode scheduler interval in minutes (default `3`).
- `TEST_SYMBOLS`: optional comma-separated symbol list for test mode (example: `NSE:NIFTYBANK-INDEX`).

## Database
- `DB_NAME`: PostgreSQL database name.
- `DB_USER`: PostgreSQL user.
- `DB_PASSWORD`: PostgreSQL password.
- `DB_HOST`: PostgreSQL host (default `localhost`).
- `DB_PORT`: PostgreSQL port (default `5432`).

## Email
- `EMAIL_SENDER`: sender email account.
- `EMAIL_APP_PASSWORD`: app password for SMTP auth.
- `EMAIL_RECIPIENTS`: comma/newline-separated recipient list.

## Data Retention and Fetch
- `DATA_RETENTION_DAYS`: cleanup retention window.
- `OPTION_CHAIN_STRIKE_COUNT`: chain depth requested from API.

## Feature Flags
- `ENABLE_ALL_ENHANCEMENTS`:
  - Master switch; forces all enhancement flags to `True`.
- `ENABLE_GUARDRAILS`:
  - Data quality checks (stale/missing/anomaly checks).
- `ENABLE_OUTCOME_TRACKING`:
  - Inserts into `trade_signals` and `trade_outcomes`.
- `ENABLE_TIMING_V2`:
  - Uses `OTMTimingEngineV2`.
- `ENABLE_REGIME_V2`:
  - Uses `MarketRegimeEngine`.
- `ENABLE_DYNAMIC_OTM`:
  - Uses dynamic strike picker.
- `ENABLE_CALIBRATION`:
  - Enables probability calibration.
- `CALIBRATION_MIN_SAMPLES`:
  - Minimum samples required before non-identity calibration.

## Recommended Profiles
### Safe Progressive Rollout
- `TEST_MODE=False`
- `ENABLE_GUARDRAILS=True`
- Enable remaining flags one by one.

### Lean Test Mode
- `TEST_MODE=True`
- `TEST_INTERVAL_MINUTES=3`
- `TEST_SYMBOLS=NSE:NIFTYBANK-INDEX`
- Keep advanced enhancement flags disabled for isolated tests.

### Full Enhanced Mode
- `TEST_MODE=False`
- `ENABLE_ALL_ENHANCEMENTS=True`
- `CALIBRATION_MIN_SAMPLES=30`
- `OPTION_CHAIN_STRIKE_COUNT=40`

