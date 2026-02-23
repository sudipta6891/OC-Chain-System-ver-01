"""
Walk-forward backtester for option-buying signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import pandas as pd
from database.db_connection import DatabaseConnection
from database.market_context_repository import MarketContextRepository


@dataclass
class BacktestConfig:
    slippage_pct: float = 0.35
    txn_cost_pct: float = 0.10
    default_stop_loss_pct: float = 25.0
    default_target_pct: float = 45.0
    default_time_stop_min: int = 30


class WalkForwardBacktester:
    @staticmethod
    def _fetch_ltp_path(symbol: str, side: str, strike: float, entry_time, until_time) -> pd.DataFrame:
        query = """
        SELECT snapshot_time, ltp
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND option_type = %s
          AND strike_price = %s
          AND snapshot_time BETWEEN %s AND %s
        ORDER BY snapshot_time ASC
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, side, strike, entry_time, until_time))
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows, columns=["snapshot_time", "ltp"])
            df["ltp"] = pd.to_numeric(df["ltp"], errors="coerce")
            return df.dropna(subset=["ltp"]).reset_index(drop=True)
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def _simulate_trade(row, cfg: BacktestConfig) -> dict:
        entry_ltp = float(row.entry_ltp or 0.0)
        if entry_ltp <= 0:
            return {"status": "skip", "net_return_pct": 0.0}

        stop_pct = float(row.stop_loss_pct or cfg.default_stop_loss_pct)
        target_pct = float(row.target_pct or cfg.default_target_pct)
        time_stop_min = int(row.time_stop_min or cfg.default_time_stop_min)

        entry_time = row.snapshot_time
        until_time = entry_time + timedelta(minutes=time_stop_min)
        path = WalkForwardBacktester._fetch_ltp_path(
            symbol=row.symbol,
            side=row.side,
            strike=float(row.strike_price),
            entry_time=entry_time,
            until_time=until_time,
        )
        if path.empty:
            return {"status": "skip", "net_return_pct": 0.0}

        executed_entry = entry_ltp * (1 + cfg.slippage_pct / 100.0)
        stop_level = executed_entry * (1 - abs(stop_pct) / 100.0)
        target_level = executed_entry * (1 + abs(target_pct) / 100.0)

        exit_ltp = float(path.iloc[-1]["ltp"])
        exit_reason = "TIME_STOP"
        for _, p in path.iterrows():
            ltp = float(p["ltp"])
            if ltp <= stop_level:
                exit_ltp = ltp
                exit_reason = "STOP_LOSS"
                break
            if ltp >= target_level:
                exit_ltp = ltp
                exit_reason = "TARGET"
                break

        executed_exit = exit_ltp * (1 - cfg.slippage_pct / 100.0)
        gross_return_pct = ((executed_exit - executed_entry) / executed_entry) * 100.0
        net_return_pct = gross_return_pct - cfg.txn_cost_pct

        return {
            "status": "done",
            "exit_reason": exit_reason,
            "gross_return_pct": gross_return_pct,
            "net_return_pct": net_return_pct,
        }

    @staticmethod
    def run(symbol: str, start_date: str, end_date: str, cfg: BacktestConfig | None = None) -> dict:
        cfg = cfg or BacktestConfig()
        signals = MarketContextRepository.fetch_signals_for_range(symbol, start_date, end_date)
        if signals.empty:
            return {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "trades": 0,
                "hit_rate": 0.0,
                "avg_net_return_pct": 0.0,
                "expectancy": 0.0,
                "max_drawdown_pct": 0.0,
            }

        results = []
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for row in signals.itertuples(index=False):
            r = WalkForwardBacktester._simulate_trade(row, cfg)
            if r["status"] != "done":
                continue
            equity += float(r["net_return_pct"])
            peak = max(peak, equity)
            max_dd = min(max_dd, equity - peak)
            results.append(r)

        if not results:
            return {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "trades": 0,
                "hit_rate": 0.0,
                "avg_net_return_pct": 0.0,
                "expectancy": 0.0,
                "max_drawdown_pct": 0.0,
            }

        wins = sum(1 for r in results if r["net_return_pct"] > 0)
        trades = len(results)
        avg_net = sum(r["net_return_pct"] for r in results) / trades
        expectancy = avg_net / 100.0

        return {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "trades": trades,
            "hit_rate": round(wins / trades, 4),
            "avg_net_return_pct": round(avg_net, 4),
            "expectancy": round(expectancy, 6),
            "max_drawdown_pct": round(abs(max_dd), 4),
        }

