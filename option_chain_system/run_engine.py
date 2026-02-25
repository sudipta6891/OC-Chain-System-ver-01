"""
Core orchestration engine for one option-chain processing cycle per symbol.

Flow:
1) Fetch and basic analytics
2) Data quality and optional enhanced models
3) Optional signal persistence/outcome labeling
4) Report generation and web persistence
"""

from data_layer.data_fetcher import OptionChainFetcher
from analytics.basic_analysis import BasicOptionAnalysis
from analytics.advanced_analysis import AdvancedOptionAnalysis
from analytics.interpretation_engine import InterpretationEngine
from analytics.breakout_engine import BreakoutEngine
from analytics.probability_engine import ProbabilityEngine
from analytics.probability_calibration_engine import ProbabilityCalibrationEngine
from analytics.volume_engine import VolumeEngine
from analytics.scalp_engine import OTMScalpEngine
from analytics.intraday_engine import IntradayEngine
from analytics.intraday_oi_engine import IntradayOIDeltaEngine
from analytics.institutional_confidence_engine import InstitutionalConfidenceEngine
from analytics.market_bias_engine import MarketBiasEngine
from analytics.option_geeks_engine import OptionGeeksEngine
from analytics.data_quality_engine import DataQualityEngine
from analytics.market_regime_engine import MarketRegimeEngine
from analytics.otm_timing_engine_v2 import OTMTimingEngineV2
from analytics.dynamic_otm_selector import DynamicOTMSelector
from reporting.report_builder import ReportBuilder
from reporting.report_web_store import ReportWebStore
from database.snapshot_repository import SnapshotRepository
from database.summary_repository import SummaryRepository
from database.scalp_repository import ScalpRepository
from database.market_context_repository import MarketContextRepository
from database.trade_signal_repository import TradeSignalRepository
from database.trade_outcome_repository import TradeOutcomeRepository
from config.settings import settings


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


def _fallback_tracking_pick(df, spot: float, side: str, distance_percent: float = 2.0) -> dict:
    if side not in ("CE", "PE"):
        return {"strike": None, "entry_ltp": None, "score": 0.0, "reasons": ["Invalid side for fallback picker."]}

    if side == "CE":
        target = spot * (1 + distance_percent / 100.0)
        eligible = df[(df["option_type"] == "CE") & (df["strike_price"] >= target)].copy()
    else:
        target = spot * (1 - distance_percent / 100.0)
        eligible = df[(df["option_type"] == "PE") & (df["strike_price"] <= target)].copy()

    if eligible.empty:
        return {"strike": None, "entry_ltp": None, "score": 0.0, "reasons": ["No fallback eligible OTM strike found."]}

    eligible["dist"] = (eligible["strike_price"] - target).abs()
    row = eligible.sort_values("dist", ascending=True).iloc[0]
    return {
        "strike": float(row["strike_price"]),
        "entry_ltp": float(row["ltp"]),
        "score": 0.0,
        "reasons": [f"Fallback {distance_percent:.1f}% OTM picker used for outcome tracking."],
    }


def run_option_chain(symbol: str) -> None:
    fetcher = OptionChainFetcher()
    basic = BasicOptionAnalysis()
    advanced = AdvancedOptionAnalysis()
    interpreter = InterpretationEngine()
    breakout_engine = BreakoutEngine()
    prob_engine = ProbabilityEngine()
    volume_engine = VolumeEngine()
    scalp_engine = OTMScalpEngine()
    intraday_engine = IntradayEngine()
    report_builder = ReportBuilder()
    confidence_engine = InstitutionalConfidenceEngine()
    market_bias_engine = MarketBiasEngine()
    geeks_engine = OptionGeeksEngine()

    print(f"\nProcessing {symbol}\n")
    spot = fetcher.fetch_spot_price(symbol)
    df = fetcher.fetch_option_chain(symbol)

    if df.empty:
        print(f"Skipping {symbol} due to no expiry data.\n")
        return

    snapshot_time = df["snapshot_time"].iloc[0]
    if settings.ENABLE_GUARDRAILS:
        quality = DataQualityEngine.assess(symbol=symbol, df=df, spot=spot, snapshot_time=snapshot_time)
    else:
        quality = type(
            "Quality",
            (),
            {
                "is_usable": True,
                "stale_data": False,
                "missing_strikes": False,
                "anomaly_flags": [],
                "warnings": [],
            },
        )()

    print(
        f"Data Quality | usable={quality.is_usable}, stale={quality.stale_data}, "
        f"missing_strikes={quality.missing_strikes}, anomalies={len(quality.anomaly_flags)}"
    )

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

    if not settings.TEST_MODE:
        SnapshotRepository.bulk_insert_snapshot(df)
        SummaryRepository.insert_summary(
            symbol=symbol,
            snapshot_time=snapshot_time,
            spot_price=spot,
            atm_strike=atm,
            total_ce_oi=total_ce,
            total_pe_oi=total_pe,
            pcr=pcr,
            resistance=resistance,
            support=support,
            max_pain=max_pain,
            structure=structure,
            trap_signal=trap,
        )
    else:
        print("TEST MODE: Skipping snapshot/summary inserts.")

    oi_delta_data = IntradayOIDeltaEngine.calculate_oi_delta(
        symbol=symbol,
        snapshot_time=snapshot_time,
        spot=spot,
    )

    regime_data = {
        "label": "UNKNOWN",
        "confidence": 0,
        "features": {},
        "why_now": [],
        "why_not_now": [],
    }
    if settings.ENABLE_REGIME_V2:
        summary_history = MarketContextRepository.fetch_recent_summaries(symbol, snapshot_time, limit=24)
        regime_data = MarketRegimeEngine.detect(summary_history, df, oi_delta_data)
    print(
        "Regime V2 | "
        f"enabled={settings.ENABLE_REGIME_V2}, "
        f"label={regime_data.get('label')}, "
        f"confidence={regime_data.get('confidence')}"
    )
    if regime_data.get("why_not_now"):
        print("Regime Cautions:", "; ".join(regime_data["why_not_now"]))

    prob_data = prob_engine.calculate_bias(pcr, breakout_signal, structure)
    scalp_data = scalp_engine.generate_signal(
        breakout_signal,
        covering_signal,
        volume_data,
        prob_data,
    )

    market_bias_data = market_bias_engine.calculate_market_bias(
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

    timing_data = {
        "timing_score_v2": int(geeks_data.get("otm_timing_score", 0)),
        "allow_trade": bool(quality.is_usable),
        "entry_window": geeks_data.get("entry_window", "WAIT"),
        "reasons": ["Timing v2 disabled"],
        "blockers": [],
        "calibration_input_probability": max(
            0.01, min(0.99, 0.5 + (int(market_bias_data.get("market_score", 0)) / 200.0))
        ),
        "expected_move_pct": 0.5,
        "invalidation_pct": 0.25,
    }
    if settings.ENABLE_TIMING_V2:
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
    print(
        "Timing V2 | "
        f"enabled={settings.ENABLE_TIMING_V2}, "
        f"score={timing_data.get('timing_score_v2')}, "
        f"allow_trade={timing_data.get('allow_trade')}, "
        f"entry_window={timing_data.get('entry_window')}"
    )
    if timing_data.get("blockers"):
        print("Timing V2 Blockers:", "; ".join(timing_data["blockers"]))

    cal = {
        "method": "identity",
        "calibrated_probability": timing_data["calibration_input_probability"],
        "sample_size": 0,
    }
    if settings.ENABLE_CALIBRATION:
        calibration_samples = TradeOutcomeRepository.fetch_calibration_samples(symbol, lookback_days=45)
        cal = ProbabilityCalibrationEngine.calibrate(
            raw_probability=timing_data["calibration_input_probability"],
            samples=calibration_samples,
            min_samples=settings.CALIBRATION_MIN_SAMPLES,
        )
    print(
        "Calibration | "
        f"enabled={settings.ENABLE_CALIBRATION}, "
        f"method={cal.get('method')}, "
        f"p={cal.get('calibrated_probability'):.3f}, "
        f"samples={cal.get('sample_size')}"
    )
    prob_data = prob_engine.calculate_bias(
        pcr,
        breakout_signal,
        structure,
        calibration_probability=cal["calibrated_probability"],
    )

    confidence_data = confidence_engine.calculate_confidence(
        oi_delta_data,
        prob_data,
        volume_data,
        scalp_data,
    )

    intraday_data = intraday_engine.generate_outlook(
        spot,
        resistance,
        support,
        prob_data,
        breakout_signal,
    )

    if not settings.TEST_MODE:
        ScalpRepository.insert_scalp_score(
            symbol=symbol,
            snapshot_time=snapshot_time,
            spot_price=spot,
            scalp_data=scalp_data,
        )
        if settings.ENABLE_OUTCOME_TRACKING:
            TradeOutcomeRepository.process_pending_signals(symbol)

    side = _pick_side(market_bias_data, geeks_data)
    dynamic_pick = {"strike": None, "entry_ltp": None, "score": 0.0, "reasons": ["No trade side selected."]}
    signal_id = None
    stop_loss_pct = 25.0
    target_pct = 45.0
    time_stop_min = 30

    if side and timing_data["allow_trade"] and quality.is_usable:
        if settings.ENABLE_DYNAMIC_OTM:
            dynamic_pick = DynamicOTMSelector.select(
                df=df,
                spot=spot,
                atm=atm,
                side=side,
                breakout_signal=breakout_signal,
                regime=regime_data["label"],
                snapshot_time=snapshot_time,
            )
        else:
            dynamic_pick = {
                "strike": None,
                "entry_ltp": None,
                "score": 0.0,
                "reasons": ["Dynamic OTM selector disabled."],
            }
            if settings.ENABLE_OUTCOME_TRACKING:
                dynamic_pick = _fallback_tracking_pick(df=df, spot=spot, side=side, distance_percent=2.0)

        print(
            "OTM Picker | "
            f"enabled={settings.ENABLE_DYNAMIC_OTM}, "
            f"side={side}, "
            f"strike={dynamic_pick.get('strike')}, "
            f"entry_ltp={dynamic_pick.get('entry_ltp')}, "
            f"score={dynamic_pick.get('score')}"
        )
        if dynamic_pick.get("reasons"):
            print("OTM Picker Reasons:", "; ".join(dynamic_pick["reasons"]))

        if (
            settings.ENABLE_OUTCOME_TRACKING
            and dynamic_pick["strike"] is not None
            and not settings.TEST_MODE
        ):
            signal_id = TradeSignalRepository.insert_signal(
                symbol=symbol,
                snapshot_time=snapshot_time,
                side=side,
                strike_price=float(dynamic_pick["strike"]),
                entry_ltp=float(dynamic_pick["entry_ltp"] or 0.0),
                spot_price=spot,
                regime=regime_data["label"],
                signal_strength=float(market_bias_data.get("market_score", 0)),
                timing_score=float(timing_data["timing_score_v2"]),
                raw_probability=float(timing_data["calibration_input_probability"]),
                calibrated_probability=float(cal["calibrated_probability"]),
                stop_loss_pct=stop_loss_pct,
                target_pct=target_pct,
                time_stop_min=time_stop_min,
                execution_notes="; ".join(dynamic_pick.get("reasons", [])),
            )
            if signal_id:
                TradeOutcomeRepository.label_outcomes_for_signal(
                    signal_id=signal_id,
                    symbol=symbol,
                    side=side,
                    strike=float(dynamic_pick["strike"]),
                    entry_time=snapshot_time,
                    entry_ltp=float(dynamic_pick["entry_ltp"] or 0.0),
                    stop_loss_pct=stop_loss_pct,
                    target_pct=target_pct,
                )

    performance_data = {"trades": 0, "hit_rate": 0.0, "expectancy": 0.0, "avg_return_pct": 0.0}
    if settings.ENABLE_OUTCOME_TRACKING:
        performance_data = TradeOutcomeRepository.fetch_recent_performance(symbol=symbol, lookback_days=20)

    pcr_note = (
        "Low PCR bearish" if pcr < 0.8 else
        "Balanced PCR range" if pcr <= 1.2 else
        "High PCR bullish"
    )
    maxpain_note = "Near max pain range magnet" if abs(spot - max_pain) / max(1.0, spot) < 0.0015 else "Away from max pain"

    final_side = side if side in ("CE", "PE") else "NO TRADE"
    has_valid_strike = dynamic_pick.get("strike") is not None
    final_allow_trade = bool(timing_data["allow_trade"] and quality.is_usable and final_side in ("CE", "PE") and has_valid_strike)

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
        market_bias_data=market_bias_data,
        geeks_data=geeks_data,
        regime_data=regime_data,
        timing_data=timing_data,
        dynamic_pick=dynamic_pick,
        calibration_data=cal,
        quality_data={
            "is_usable": quality.is_usable,
            "stale_data": quality.stale_data,
            "missing_strikes": quality.missing_strikes,
            "anomaly_flags": quality.anomaly_flags,
            "warnings": quality.warnings,
        },
        performance_data=performance_data,
        execution_data={
            "side": final_side,
            "signal_id": signal_id,
            "stop_loss_pct": stop_loss_pct,
            "target_pct": target_pct,
            "time_stop_min": time_stop_min,
            "allow_trade": final_allow_trade,
            "invalidation_pct": timing_data["invalidation_pct"],
            "expected_move_pct": timing_data["expected_move_pct"],
        },
    )

    subject_line = f"{'[TEST MODE] ' if settings.TEST_MODE else ''}10-Min Option Chain Report - {symbol}"
    try:
        saved_path = ReportWebStore.save_report(symbol=symbol, subject=subject_line, report_html=report_html)
        print(f"Web report saved: {saved_path}")
    except Exception as exc:
        print(f"Web report save failed: {exc}")
