"""
Repository for trade outcome labeling and analytics.
"""

from __future__ import annotations

from datetime import timedelta
from database.db_connection import DatabaseConnection


class TradeOutcomeRepository:
    @staticmethod
    def _fetch_ltp_at_or_after(symbol: str, side: str, strike: float, target_time):
        query = """
        SELECT snapshot_time, ltp
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND option_type = %s
          AND strike_price = %s
          AND snapshot_time >= %s
        ORDER BY snapshot_time ASC
        LIMIT 1
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, side, strike, target_time))
            row = cursor.fetchone()
            return row if row else None
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def _upsert_outcome(
        signal_id: int,
        horizon_min: int,
        exit_time,
        exit_ltp: float | None,
        return_pct: float | None,
        pnl_points: float | None,
        outcome_label: str,
        hit_target: bool,
        hit_stop: bool,
        expectancy_component: float,
    ) -> None:
        query = """
        INSERT INTO trade_outcomes (
            signal_id, horizon_min, exit_time, exit_ltp, return_pct, pnl_points,
            outcome_label, hit_target, hit_stop, expectancy_component
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (signal_id, horizon_min)
        DO UPDATE SET
            exit_time = EXCLUDED.exit_time,
            exit_ltp = EXCLUDED.exit_ltp,
            return_pct = EXCLUDED.return_pct,
            pnl_points = EXCLUDED.pnl_points,
            outcome_label = EXCLUDED.outcome_label,
            hit_target = EXCLUDED.hit_target,
            hit_stop = EXCLUDED.hit_stop,
            expectancy_component = EXCLUDED.expectancy_component
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                query,
                (
                    signal_id,
                    horizon_min,
                    exit_time,
                    exit_ltp,
                    return_pct,
                    pnl_points,
                    outcome_label,
                    hit_target,
                    hit_stop,
                    expectancy_component,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def label_outcomes_for_signal(
        signal_id: int,
        symbol: str,
        side: str,
        strike: float,
        entry_time,
        entry_ltp: float | None,
        stop_loss_pct: float,
        target_pct: float,
    ) -> None:
        if not entry_ltp or entry_ltp <= 0:
            return

        for horizon in (10, 30, 60):
            target_time = entry_time + timedelta(minutes=horizon)
            row = TradeOutcomeRepository._fetch_ltp_at_or_after(symbol, side, strike, target_time)
            if not row:
                TradeOutcomeRepository._upsert_outcome(
                    signal_id=signal_id,
                    horizon_min=horizon,
                    exit_time=None,
                    exit_ltp=None,
                    return_pct=None,
                    pnl_points=None,
                    outcome_label="OPEN",
                    hit_target=False,
                    hit_stop=False,
                    expectancy_component=0.0,
                )
                continue

            exit_time, exit_ltp = row
            exit_ltp = float(exit_ltp)
            pnl_points = exit_ltp - float(entry_ltp)
            return_pct = (pnl_points / float(entry_ltp)) * 100
            hit_target = return_pct >= target_pct
            hit_stop = return_pct <= -abs(stop_loss_pct)

            if hit_target:
                label = "WIN"
            elif hit_stop:
                label = "LOSS"
            elif abs(return_pct) < 1.0:
                label = "FLAT"
            else:
                label = "WIN" if return_pct > 0 else "LOSS"

            TradeOutcomeRepository._upsert_outcome(
                signal_id=signal_id,
                horizon_min=horizon,
                exit_time=exit_time,
                exit_ltp=exit_ltp,
                return_pct=return_pct,
                pnl_points=pnl_points,
                outcome_label=label,
                hit_target=hit_target,
                hit_stop=hit_stop,
                expectancy_component=return_pct / 100.0,
            )

    @staticmethod
    def fetch_recent_performance(symbol: str, lookback_days: int = 20) -> dict:
        query = """
        SELECT
            COUNT(*) AS trades,
            AVG(return_pct) AS avg_return_pct,
            SUM(CASE WHEN outcome_label = 'WIN' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*),0) AS hit_rate,
            AVG(expectancy_component) AS expectancy
        FROM trade_outcomes o
        JOIN trade_signals s ON s.id = o.signal_id
        WHERE s.symbol = %s
          AND s.snapshot_time >= NOW() - (%s || ' days')::interval
          AND o.horizon_min = 30
          AND o.outcome_label IN ('WIN','LOSS','FLAT')
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, lookback_days))
            row = cursor.fetchone()
            if not row:
                return {"trades": 0, "hit_rate": 0.0, "expectancy": 0.0, "avg_return_pct": 0.0}
            return {
                "trades": int(row[0] or 0),
                "avg_return_pct": float(row[1] or 0.0),
                "hit_rate": float(row[2] or 0.0),
                "expectancy": float(row[3] or 0.0),
            }
        except Exception:
            return {"trades": 0, "hit_rate": 0.0, "expectancy": 0.0, "avg_return_pct": 0.0}
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def process_pending_signals(symbol: str, lookback_hours: int = 8) -> None:
        query = """
        SELECT id, symbol, snapshot_time, side, strike_price, entry_ltp, stop_loss_pct, target_pct
        FROM trade_signals
        WHERE symbol = %s
          AND snapshot_time >= NOW() - (%s || ' hours')::interval
        ORDER BY snapshot_time DESC
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, lookback_hours))
            rows = cursor.fetchall()
        except Exception:
            rows = []
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

        for row in rows:
            signal_id, sym, entry_time, side, strike, entry_ltp, stop_loss_pct, target_pct = row
            TradeOutcomeRepository.label_outcomes_for_signal(
                signal_id=int(signal_id),
                symbol=sym,
                side=side,
                strike=float(strike),
                entry_time=entry_time,
                entry_ltp=float(entry_ltp or 0.0),
                stop_loss_pct=float(stop_loss_pct or 25.0),
                target_pct=float(target_pct or 45.0),
            )

    @staticmethod
    def fetch_calibration_samples(symbol: str, lookback_days: int = 45) -> list[tuple[float, int]]:
        """
        Returns (raw_probability_0_to_1, outcome_binary) samples for calibration.
        """
        query = """
        SELECT COALESCE(s.raw_probability, s.calibrated_probability), o.outcome_label
        FROM trade_outcomes o
        JOIN trade_signals s ON s.id = o.signal_id
        WHERE s.symbol = %s
          AND s.snapshot_time >= NOW() - (%s || ' days')::interval
          AND o.horizon_min = 30
          AND o.outcome_label IN ('WIN','LOSS')
          AND COALESCE(s.raw_probability, s.calibrated_probability) IS NOT NULL
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, lookback_days))
            rows = cursor.fetchall()
            samples: list[tuple[float, int]] = []
            for prob, label in rows:
                p = float(prob or 0.5)
                p = max(0.01, min(0.99, p))
                y = 1 if label == "WIN" else 0
                samples.append((p, y))
            return samples
        except Exception:
            return []
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)
