# Database Documentation

Primary DDL files:
- `database/schema.sql`
- `database/scalp_score_tracking schema_create.sql`

## Tables
### `option_chain_snapshot`
- Raw option-chain rows per snapshot.
- Key fields: `symbol`, `strike_price`, `option_type`, `open_interest`, `oi_change`, `volume`, `ltp`, `snapshot_time`.

### `option_chain_summary`
- Derived summary metrics per snapshot.
- Key fields: `spot_price`, `atm_strike`, `pcr`, `support`, `resistance`, `max_pain`, `structure`.

### `scalp_score_tracking`
- Scalp engine component scores and labels per snapshot.
- Created from `database/scalp_score_tracking schema_create.sql`.

### `trade_signals`
- Candidate trade entries emitted by pipeline.
- Includes side, strike, timing, raw/calibrated probability, risk parameters.

### `trade_outcomes`
- Labeled outcomes for each signal at 10/30/60-minute horizons.
- Includes `return_pct`, `outcome_label`, `hit_target`, `hit_stop`, `expectancy_component`.

## Indexes
- Snapshot: `idx_snapshot_symbol_time`
- Summary: `idx_summary_symbol_time`
- Scalp: `idx_scalp_symbol_time`
- Signals: `idx_trade_signals_symbol_time`
- Outcomes: `idx_trade_outcomes_signal`

## Migration
- Apply/re-apply schema:
  - `python database/apply_schema.py`
- Readiness check + auto apply:
  - `python check_runtime.py --apply-missing-schema`

## Retention
- Managed by `database/cleanup_manager.py`.
- Controlled by `DATA_RETENTION_DAYS`.

