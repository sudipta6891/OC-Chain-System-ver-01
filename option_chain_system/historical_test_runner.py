"""
Historical Test Runner (Backtesting Foundation)

Purpose:
- Run full analytics for a specific historical timestamp
- Validate snapshot existence
- Generate same HTML report
- Send TEST email
"""

from datetime import datetime
import pytz
import pandas as pd

from database.db_connection import DatabaseConnection
from analytics.basic_analysis import BasicOptionAnalysis
from analytics.advanced_analysis import AdvancedOptionAnalysis
from analytics.interpretation_engine import InterpretationEngine
from analytics.breakout_engine import BreakoutEngine
from analytics.probability_engine import ProbabilityEngine
from analytics.volume_engine import VolumeEngine
from analytics.scalp_engine import OTMScalpEngine
from analytics.institutional_confidence_engine import InstitutionalConfidenceEngine
from analytics.intraday_engine import IntradayEngine
from analytics.option_geeks_engine import OptionGeeksEngine
from reporting.report_builder import ReportBuilder
from reporting.email_service import EmailService
from analytics.intraday_oi_engine import IntradayOIDeltaEngine


TIMEZONE = pytz.timezone("Asia/Kolkata")


class HistoricalTestRunner:


    @staticmethod
    def fetch_previous_snapshot(symbol: str, target_time: datetime) -> pd.DataFrame:

        query = """
        SELECT strike_price,
            option_type,
            open_interest
        FROM option_chain_snapshot
        WHERE symbol = %s
        AND snapshot_time < %s
        ORDER BY snapshot_time DESC
        LIMIT 200
        """

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query, (symbol, target_time))
            rows = cursor.fetchall()

            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(
                rows,
                columns=[
                    "strike_price",
                    "option_type",
                    "open_interest"
                ]
            )

            df["strike_price"] = df["strike_price"].astype(float)
            df["open_interest"] = df["open_interest"].astype(float)

            return df

        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_snapshot(symbol: str, target_time: datetime) -> pd.DataFrame:

        query = """
        SELECT strike_price,
            option_type,
            open_interest,
            volume,
            ltp,
            snapshot_time
        FROM option_chain_snapshot
        WHERE symbol = %s
        AND snapshot_time BETWEEN %s - INTERVAL '5 minutes'
                                AND %s + INTERVAL '5 minutes'
        ORDER BY ABS(EXTRACT(EPOCH FROM (snapshot_time - %s)))
        LIMIT 200
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
                columns=[
                    "strike_price",
                    "option_type",
                    "open_interest",
                    "volume",
                    "ltp",
                    "snapshot_time"
                ]
            )
            # 🔥 Convert Decimal → Float
            df["strike_price"] = df["strike_price"].astype(float)
            df["open_interest"] = df["open_interest"].astype(float)
            df["volume"] = df["volume"].astype(float)
            df["ltp"] = df["ltp"].astype(float)

            print("🕒 Closest Snapshot Found At:", df["snapshot_time"].iloc[0])

            return df

        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def fetch_summary(symbol: str, target_time: datetime) -> pd.DataFrame:

        query = """
        SELECT spot_price,
            atm_strike,
            total_ce_oi,
            total_pe_oi,
            pcr,
            resistance,
            support,
            max_pain,
            structure,
            trap_signal,
            snapshot_time
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
                    "snapshot_time"
                ]
            )

            df["spot_price"] = df["spot_price"].astype(float)
            return df

        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)

    @staticmethod
    def run(symbol: str, date_str: str, time_str: str):
        # Convert to datetime
        target_time = datetime.strptime(
            f"{date_str} {time_str}",
            "%Y-%m-%d %H:%M"
        )

        target_time = TIMEZONE.localize(target_time)
        replay_date = target_time.strftime("%Y-%m-%d")
        replay_time = target_time.strftime("%H:%M IST")

        print("\n=====================================")
        print("HISTORICAL TEST MODE")
        print("Symbol:", symbol)
        print("Target Time:", target_time)
        print("=====================================\n")

        df = HistoricalTestRunner.fetch_snapshot(symbol, target_time)
        prev_df = HistoricalTestRunner.fetch_previous_snapshot(symbol, target_time)

        if not prev_df.empty:

            df = df.merge(
                prev_df,
                on=["strike_price", "option_type"],
                how="left",
                suffixes=("", "_prev")
            )

            df["oi_change"] = df["open_interest"] - df["open_interest_prev"].fillna(0)

        else:
            df["oi_change"] = 0.0

        if df.empty:
            print("❌ No snapshot data found for given timestamp.")
            return

        print("✅ Snapshot data found. Running analytics...\n")

        summary_df = HistoricalTestRunner.fetch_summary(symbol, target_time)

        if summary_df.empty:
            print("❌ No summary data found.")
            return

        spot = summary_df["spot_price"].iloc[0]

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

        atm = basic.detect_atm_strike(df, spot)
        ce_df, pe_df = basic.split_ce_pe(df)
        total_ce, total_pe = basic.calculate_total_oi(ce_df, pe_df)
        pcr = basic.calculate_pcr(total_pe, total_ce)
        resistance, support = advanced.oi_based_levels(ce_df, pe_df)
        max_pain = advanced.calculate_max_pain(df)

        structure = interpreter.detect_writing(ce_df, pe_df)
        breakout_signal = breakout_engine.detect_breakout(spot, resistance, support)
        covering_signal = breakout_engine.detect_short_covering(ce_df, pe_df)

        prob_data = prob_engine.calculate_bias(pcr, breakout_signal, structure)
        volume_data = volume_engine.detect_volume_spike(df, atm)
        scalp_data = scalp_engine.generate_signal(
            breakout_signal,
            covering_signal,
            volume_data,
            prob_data
        )

        confidence_data = confidence_engine.calculate_confidence(
            {
                "ce_delta": 0,
                "pe_delta": 0
            },
            prob_data,
            volume_data,
            scalp_data
        )

        intraday_data = intraday_engine.generate_outlook(
            spot,
            resistance,
            support,
            prob_data,
            breakout_signal
        )
        oi_delta_data = IntradayOIDeltaEngine.calculate_oi_delta(
            symbol=symbol,
            snapshot_time=target_time,
            spot=spot
        )
        geeks_data = geeks_engine.analyze(
            df=df,
            spot=spot,
            atm=atm,
            breakout_signal=breakout_signal,
            snapshot_time=target_time,
            profile="aggressive",
        )
        print("RUNNER OI DATA:", oi_delta_data)
        if pcr > 1:
            pcr_note = "PCR above 1 – Put Writing Bias (Historical Replay)"
        elif pcr < 1:
            pcr_note = "PCR below 1 – Call Writing Bias (Historical Replay)"
        else:
            pcr_note = "Neutral PCR (Historical Replay)"
        maxpain_note = (
            f"Historical Replay Mode | "
            f"Replay Date: {replay_date} | "
            f"Replay Time: {replay_time} | "
            f"Max Pain: {max_pain}"
        )
        replay_info = {
            "date": replay_date,
            "time": replay_time,
            "symbol": symbol
        }

        report_html = report_builder.build_html_report(
            symbol,
            spot,
            atm,
            resistance,
            support,
            max_pain,
            pcr,
            prob_data,
            scalp_data,
            intraday_data,
            oi_delta_data,
            pcr_note,
            maxpain_note,
            confidence_data,
            geeks_data=geeks_data,
            replay_info=replay_info   # keyword argument (recommended)
        )

        subject_line = (
            f"[HISTORICAL TEST] {symbol} | "
            f"{replay_date} {replay_time}"
        )

        EmailService.send_email(
            subject=subject_line,
            body=report_html
        )

        print("📧 Historical Test Email Sent Successfully!")
