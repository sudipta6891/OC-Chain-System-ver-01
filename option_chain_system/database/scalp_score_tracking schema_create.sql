CREATE TABLE IF NOT EXISTS scalp_score_tracking (

    id SERIAL PRIMARY KEY,

    symbol VARCHAR(50),
    snapshot_time TIMESTAMP WITH TIME ZONE,

    spot_price NUMERIC,

    breakout_score INT,
    volume_score INT,
    bias_score INT,
    covering_score INT,

    total_score INT,
    signal VARCHAR(50),
    edge VARCHAR(50),
    risk_level VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scalp_symbol_time
ON scalp_score_tracking(symbol, snapshot_time DESC);
