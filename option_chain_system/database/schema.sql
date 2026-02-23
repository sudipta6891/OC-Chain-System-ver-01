-- ============================================
-- OPTION CHAIN SNAPSHOT TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS option_chain_snapshot (

    id SERIAL PRIMARY KEY,

    symbol VARCHAR(50),
    strike_price NUMERIC,
    option_type VARCHAR(5),

    open_interest BIGINT,
    oi_change BIGINT,
    volume BIGINT,
    ltp NUMERIC,

    snapshot_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshot_symbol_time
ON option_chain_snapshot(symbol, snapshot_time DESC);


-- ============================================
-- OPTION CHAIN SUMMARY TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS option_chain_summary (

    id SERIAL PRIMARY KEY,

    symbol VARCHAR(50),
    snapshot_time TIMESTAMP WITH TIME ZONE,

    spot_price NUMERIC,
    atm_strike NUMERIC,

    total_ce_oi BIGINT,
    total_pe_oi BIGINT,
    pcr NUMERIC,

    resistance NUMERIC,
    support NUMERIC,
    max_pain NUMERIC,

    structure TEXT,
    trap_signal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_summary_symbol_time
ON option_chain_summary(symbol, snapshot_time DESC);


-- ============================================
-- TRADE SIGNALS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS trade_signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    side VARCHAR(8) NOT NULL, -- CE / PE
    strike_price NUMERIC NOT NULL,
    entry_ltp NUMERIC,
    spot_price NUMERIC NOT NULL,
    regime VARCHAR(32) DEFAULT 'UNKNOWN',
    signal_strength NUMERIC DEFAULT 0,
    timing_score NUMERIC DEFAULT 0,
    raw_probability NUMERIC DEFAULT 0,
    calibrated_probability NUMERIC DEFAULT 0,
    stop_loss_pct NUMERIC DEFAULT 0,
    target_pct NUMERIC DEFAULT 0,
    time_stop_min INT DEFAULT 30,
    execution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trade_signals_symbol_time
ON trade_signals(symbol, snapshot_time DESC);


-- ============================================
-- TRADE OUTCOMES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS trade_outcomes (
    id BIGSERIAL PRIMARY KEY,
    signal_id BIGINT NOT NULL REFERENCES trade_signals(id) ON DELETE CASCADE,
    horizon_min INT NOT NULL, -- 10 / 30 / 60
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_ltp NUMERIC,
    return_pct NUMERIC,
    pnl_points NUMERIC,
    outcome_label VARCHAR(16), -- WIN / LOSS / FLAT / OPEN
    hit_target BOOLEAN DEFAULT FALSE,
    hit_stop BOOLEAN DEFAULT FALSE,
    expectancy_component NUMERIC DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(signal_id, horizon_min)
);

CREATE INDEX IF NOT EXISTS idx_trade_outcomes_signal
ON trade_outcomes(signal_id);
