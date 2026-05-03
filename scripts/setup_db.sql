-- ============================================
--  HFT Momentum Bot - Database Schema
-- ============================================

CREATE TABLE IF NOT EXISTS trade_logs (
    id          SERIAL PRIMARY KEY,
    ticket      BIGINT,
    symbol      VARCHAR(20),
    action      VARCHAR(10),
    volume      DOUBLE PRECISION,
    entry_price DOUBLE PRECISION,
    sl          DOUBLE PRECISION,
    tp          DOUBLE PRECISION,
    pnl         DOUBLE PRECISION,
    timestamp   BIGINT,
    reason      VARCHAR(50),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS microstructure_logs (
    id            SERIAL PRIMARY KEY,
    symbol        VARCHAR(20),
    timestamp     BIGINT,
    tick_velocity DOUBLE PRECISION,
    buy_volume    DOUBLE PRECISION,
    sell_volume   DOUBLE PRECISION,
    delta         DOUBLE PRECISION,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Indices para queries frecuentes
CREATE INDEX IF NOT EXISTS idx_trade_logs_symbol ON trade_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_logs_timestamp ON trade_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_micro_logs_symbol ON microstructure_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_micro_logs_timestamp ON microstructure_logs(timestamp);
