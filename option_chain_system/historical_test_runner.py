"""Historical report generator using DB snapshots and summaries."""

from __future__ import annotations

from datetime import datetime
import pandas as pd
import pytz

from analytics.advanced_analysis import AdvancedOptionAnalysis
from analytics.basic_analysis import BasicOptionAnalysis
from analytics.breakout_engine import BreakoutEngine
from analytics.data_quality_engine import DataQualityEngine
from analytics.dynamic_otm_selector import DynamicOTMSelector
from analytics.institutional_confidence_engine import InstitutionalConfidenceEngine
from analytics.intraday_engine import IntradayEngine
from analytics.intraday_oi_engine import IntradayOIDeltaEngine
from analytics.interpretation_engine import InterpretationEngine
from analytics.market_bias_engine import MarketBiasEngine
from analytics.market_regime_engine import MarketRegimeEngine
from analytics.option_geeks_engine import OptionGeeksEngine
from analytics.otm_timing_engine_v2 import OTMTimingEngineV2
from analytics.probability_calibration_engine import ProbabilityCalibrationEngine
from analytics.probability_engine import ProbabilityEngine
from analytics.scalp_engine import OTMScalpEngine
from analytics.volume_engine import VolumeEngine
from config.settings import settings
from database.db_connection import DatabaseConnection
from database.market_context_repository import MarketContextRepository
from database.trade_outcome_repository import TradeOutcomeRepository
from reporting.report_builder import ReportBuilder


TIMEZONE = pytz.timezone("Asia/Kolkata")


def _pick_side(market_bias_data: dict, geeks_data: dict) -> str:
    score = int(market_bias_data.get("market_score", 0))
    geeks_side = geeks_data.get("preferred_otm_side", "NO TRADE / WAIT")
    if score >= 20 and "CE" in geeks_side:
        return "CE"
    if score <= -20 and "PE" in geeks_side:
        return "PE"
    if score >= 25:
        return "CE"
    if score <= -25:
        return "PE"
    return ""


class HistoricalTestRunner:
    @staticmethod
    def fetch_previous_snapshot(symbol: str, target_time: datetime) -> pd.DataFrame:
        query = """
        SELECT strike_price, option_type, open_interest
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND snapshot_time < %s
        ORDER BY snapshot_time DESC
        LIMIT 400
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, target_time))
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows, columns=["strike_price", "option_type", "open_interest"])
            df["strike_price"] = pd.to_numeric(df["strike_price"], errors="coerce")
            df["open_interest"] = pd.to_numeric(df["open_interest"], errors="coerce")
            return df.dropna(subset=["strike_price", "open_interest"])
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_snapshot(symbol: str, target_time: datetime) -> pd.DataFrame:
        query = """
        SELECT strike_price, option_type, open_interest, volume, ltp, snapshot_time
        FROM option_chain_snapshot
        WHERE symbol = %s
          AND snapshot_time BETWEEN %s - INTERVAL '5 minutes'
                                AND %s + INTERVAL '5 minutes'
        ORDER BY ABS(EXTRACT(EPOCH FROM (snapshot_time - %s)))
        LIMIT 500
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, target_time, target_time, target_time))
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(
                rows,
                columns=["strike_price", "option_type", "open_interest", "volume", "ltp", "snapshot_time"],
            )
            for col in ("strike_price", "open_interest", "volume", "ltp"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["symbol"] = symbol
            return df.dropna(subset=["strike_price", "open_interest", "volume", "ltp"]).reset_index(drop=True)
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_summary(symbol: str, target_time: datetime) -> pd.DataFrame:
        query = """
        SELECT spot_price, atm_strike, total_ce_oi, total_pe_oi, pcr,
               resistance, support, max_pain, structure, trap_signal, snapshot_time
        FROM option_chain_summary
        WHERE symbol = %s
          AND snapshot_time BETWEEN %s - INTERVAL '5 minutes'
                                AND %s + INTERVAL '5 minutes'
        ORDER BY ABS(EXTRACT(EPOCH FROM (snapshot_time - %s)))
        LIMIT 1
        """
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (symbol, target_time, target_time, target_time))
            row = cursor.fetchone()
            if not row:
                return pd.DataFrame()
            df = pd.DataFrame(
                [row],
                columns=[
                    "spot_price",
                    "atm_strike",
                    "total_ce_oi",
                    "total_pe_oi",
                    "pcr",
                    "resistance",
                    "support",
                    "max_pain",
                    "structure",
                    "trap_signal",
                    "snapshot_time",
                ],
            )
            for col in ("spot_price", "atm_strike", "total_ce_oi", "total_pe_oi", "pcr", "resistance", "support", "max_pain"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def _prepare_snapshot(symbol: str, target_time: datetime) -> tuple[pd.DataFrame, datetime | None]:
        df = HistoricalTestRunner.fetch_snapshot(symbol, target_time)
        if df.empty:
            return df, None

        snapshot_time = df["snapshot_time"].iloc[0]
        prev_df = HistoricalTestRunner.fetch_previous_snapshot(symbol, snapshot_time)
        if not prev_df.empty:
            df = df.merge(prev_df, on=["strike_price", "option_type"], how="left", suffixes=("", "_prev"))
            df["oi_change"] = (df["open_interest"] - df["open_interest_prev"].fillna(0)).astype(float)
            if "open_interest_prev" in df.columns:
                df = df.drop(columns=["open_interest_prev"])
        else:
            df["oi_change"] = 0.0
        return df, snapshot_time

    @staticmethod
    def generate_report_html(symbol: str, target_time: datetime) -> dict:
        df, snapshot_time = HistoricalTestRunner._prepare_snapshot(symbol, target_time)
        if df.empty or snapshot_time is None:
            raise ValueError("No snapshot data found near requested timestamp")

        summary_df = HistoricalTestRunner.fetch_summary(symbol, target_time)
        if summary_df.empty:
            raise ValueError("No summary data found near requested timestamp")

        spot = float(summary_df["spot_price"].iloc[0])
        replay_date = snapshot_time.astimezone(TIMEZONE).strftime("%Y-%m-%d")
        replay_time = snapshot_time.astimezone(TIMEZONE).strftime("%H:%M:%S IST")

        basic = BasicOptionAnalysis()
        advanced = AdvancedOptionAnalysis()
        interpreter = InterpretationEngine()
        breakout_engine = BreakoutEngine()
        prob_engine = ProbabilityEngine()
        volume_engine = VolumeEngine()
        scalp_engine = OTMScalpEngine()
        confidence_engine = InstitutionalConfidenceEngine()
        intraday_engine = IntradayEngine()
        geeks_engine = OptionGeeksEngine()
        report_builder = ReportBuilder()

        quality = DataQualityEngine.assess(symbol=symbol, df=df, spot=spot, snapshot_time=snapshot_time)

        atm = basic.detect_atm_strike(df, spot)
        ce_df, pe_df = basic.split_ce_pe(df)
        total_ce, total_pe = basic.calculate_total_oi(ce_df, pe_df)
        pcr = basic.calculate_pcr(total_pe, total_ce)
        resistance, support = advanced.oi_based_levels(ce_df, pe_df)
        max_pain = advanced.calculate_max_pain(df)
        structure = interpreter.detect_writing(ce_df, pe_df)
        trap = interpreter.detect_trap(spot, resistance, support)
        volume_data = volume_engine.detect_volume_spike(df, atm)
        breakout_signal = breakout_engine.detect_breakout(spot, resistance, support)
        covering_signal = breakout_engine.detect_short_covering(ce_df, pe_df)

        oi_delta_data = IntradayOIDeltaEngine.calculate_oi_delta(symbol=symbol, snapshot_time=snapshot_time, spot=spot)

        summary_history = MarketContextRepository.fetch_recent_summaries(symbol, snapshot_time, limit=24)
        regime_data = MarketRegimeEngine.detect(summary_history, df, oi_delta_data)

        prob_data = prob_engine.calculate_bias(pcr, breakout_signal, structure)
        scalp_data = scalp_engine.generate_signal(breakout_signal, covering_signal, volume_data, prob_data)

        market_bias_data = MarketBiasEngine.calculate_market_bias(
            pcr=pcr,
            structure=structure,
            breakout_signal=breakout_signal,
            trap=trap,
            spot=spot,
            support=support,
            resistance=resistance,
            max_pain=max_pain,
            prob_data=prob_data,
            volume_data=volume_data,
            oi_delta_data=oi_delta_data,
            scalp_data=scalp_data,
        )

        geeks_data = geeks_engine.analyze(
            df=df,
            spot=spot,
            atm=atm,
            breakout_signal=breakout_signal,
            snapshot_time=snapshot_time,
            profile="aggressive",
        )

        timing_data = OTMTimingEngineV2.score(
            geeks_data=geeks_data,
            regime_data=regime_data,
            quality_data={
                "stale_data": quality.stale_data,
                "missing_strikes": quality.missing_strikes,
                "anomaly_flags": quality.anomaly_flags,
            },
            market_bias_data=market_bias_data,
        )

        calibration_samples = TradeOutcomeRepository.fetch_calibration_samples(symbol, lookback_days=45)
        calibration_data = ProbabilityCalibrationEngine.calibrate(
            raw_probability=float(timing_data["calibration_input_probability"]),
            samples=calibration_samples,
            min_samples=settings.CALIBRATION_MIN_SAMPLES,
        )
        prob_data = prob_engine.calculate_bias(
            pcr,
            breakout_signal,
            structure,
            calibration_probability=calibration_data["calibrated_probability"],
        )

        confidence_data = confidence_engine.calculate_confidence(
            oi_delta_data,
            prob_data,
            volume_data,
            scalp_data,
        )
        intraday_data = intraday_engine.generate_outlook(spot, resistance, support, prob_data, breakout_signal)

        side = _pick_side(market_bias_data, geeks_data)
        dynamic_pick = {"strike": None, "entry_ltp": None, "score": 0.0, "reasons": ["No trade side selected."]}
        if side and timing_data["allow_trade"] and quality.is_usable:
            dynamic_pick = DynamicOTMSelector.select(
                df=df,
                spot=spot,
                atm=atm,
                side=side,
                breakout_signal=breakout_signal,
                regime=regime_data["label"],
                snapshot_time=snapshot_time,
            )

        performance_data = TradeOutcomeRepository.fetch_recent_performance(symbol=symbol, lookback_days=20)

        pcr_note = (
            "Low PCR bearish" if pcr < 0.8 else "Balanced PCR range" if pcr <= 1.2 else "High PCR bullish"
        )
        maxpain_note = (
            f"Historical Replay | Date: {replay_date} | Time: {replay_time} | Max Pain: {max_pain:.2f}"
        )

        report_html = report_builder.build_html_report(
            symbol=symbol,
            spot=spot,
            atm=atm,
            resistance=resistance,
            support=support,
            max_pain=max_pain,
            pcr=pcr,
            prob_data=prob_data,
            scalp_data=scalp_data,
            intraday_data=intraday_data,
            oi_delta_data=oi_delta_data,
            pcr_note=pcr_note,
            maxpain_note=maxpain_note,
            confidence_data=confidence_data,
            market_bias_data=market_bias_data,
            geeks_data=geeks_data,
            replay_info={"date": replay_date, "time": replay_time, "symbol": symbol},
            regime_data=regime_data,
            timing_data=timing_data,
            dynamic_pick=dynamic_pick,
            calibration_data=calibration_data,
            quality_data={
                "is_usable": quality.is_usable,
                "stale_data": quality.stale_data,
                "missing_strikes": quality.missing_strikes,
                "anomaly_flags": quality.anomaly_flags,
                "warnings": quality.warnings,
            },
            performance_data=performance_data,
            execution_data={
                "side": side,
                "signal_id": None,
                "stop_loss_pct": 25.0,
                "target_pct": 45.0,
                "time_stop_min": 30,
                "allow_trade": bool(timing_data["allow_trade"] and quality.is_usable),
                "invalidation_pct": timing_data["invalidation_pct"],
                "expected_move_pct": timing_data["expected_move_pct"],
            },
        )

        subject_line = f"[HISTORICAL TEST] {symbol} | {replay_date} {replay_time}"
        return {
            "report_html": report_html,
            "subject_line": subject_line,
            "snapshot_time": snapshot_time,
            "replay_date": replay_date,
            "replay_time": replay_time,
        }

    @staticmethod
    def run(symbol: str, date_str: str, time_str: str) -> None:
        target_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        target_time = TIMEZONE.localize(target_time)
        result = HistoricalTestRunner.generate_report_html(symbol=symbol, target_time=target_time)
        print(
            f"Historical report generated for {symbol} at "
            f"{result['replay_date']} {result['replay_time']} (email disabled)"
        )
