"""
Structured HTML report builder.
"""

from __future__ import annotations


class ReportBuilder:
    @staticmethod
    def build_html_report(
        symbol: str,
        spot: float,
        atm: float,
        resistance: float,
        support: float,
        max_pain: float,
        pcr: float,
        prob_data: dict,
        scalp_data: dict,
        intraday_data: dict,
        oi_delta_data: dict,
        pcr_note: str,
        maxpain_note: str,
        confidence_data: dict,
        market_bias_data: dict | None = None,
        geeks_data: dict | None = None,
        replay_info: dict | None = None,
        regime_data: dict | None = None,
        timing_data: dict | None = None,
        dynamic_pick: dict | None = None,
        calibration_data: dict | None = None,
        quality_data: dict | None = None,
        performance_data: dict | None = None,
        execution_data: dict | None = None,
        sr_window_data: dict | None = None,
    ) -> str:
        replay_block = ""
        if replay_info:
            replay_block = (
                "<div style='background:#fff3cd;padding:12px;border-radius:8px;border:1px solid #ffeeba;'>"
                "<b>Historical Replay Mode</b><br>"
                f"Date: {replay_info.get('date')}<br>"
                f"Time: {replay_info.get('time')}<br>"
                f"Symbol: {replay_info.get('symbol')}"
                "</div><br>"
            )

        market_bias_data = market_bias_data or {}
        geeks_data = geeks_data or {}
        regime_data = regime_data or {}
        timing_data = timing_data or {}
        dynamic_pick = dynamic_pick or {}
        calibration_data = calibration_data or {}
        quality_data = quality_data or {}
        performance_data = performance_data or {}
        execution_data = execution_data or {}
        sr_window_data = sr_window_data or {}
        if pcr > 1:
            interpretation_text = "Bullish"
            interpretation_color = "#1e8e3e"
        elif pcr < 1:
            interpretation_text = "Bearish"
            interpretation_color = "#c62828"
        else:
            interpretation_text = "Neutral"
            interpretation_color = "#6b7280"

        selected_strikes = sr_window_data.get("selected_strikes", [])
        ce_oi_change_by_strike = sr_window_data.get("ce_oi_change_by_strike", {})
        pe_oi_change_by_strike = sr_window_data.get("pe_oi_change_by_strike", {})
        call_sum = float(sr_window_data.get("call_pressure_sum", 0.0))
        put_sum = float(sr_window_data.get("put_pressure_sum", 0.0))
        pressure_direction = str(sr_window_data.get("pressure_direction", "Neutral"))

        def _strike_by_idx(idx: int):
            return selected_strikes[idx] if idx < len(selected_strikes) else None

        def _oi_change_value(oi_map: dict, strike) -> float:
            if strike is None:
                return 0.0
            return float(oi_map.get(strike, 0.0))

        s0 = _strike_by_idx(0)
        s1 = _strike_by_idx(1)
        s2 = _strike_by_idx(2)
        c1 = _oi_change_value(ce_oi_change_by_strike, s0)
        c2 = _oi_change_value(ce_oi_change_by_strike, s1)
        c3 = _oi_change_value(ce_oi_change_by_strike, s2)
        p1 = _oi_change_value(pe_oi_change_by_strike, s0)
        p2 = _oi_change_value(pe_oi_change_by_strike, s1)
        p3 = _oi_change_value(pe_oi_change_by_strike, s2)
        pressure_diff = call_sum - put_sum
        if pressure_direction == "Bullish":
            pressure_color = "#1e8e3e"
        elif pressure_direction == "Bearish":
            pressure_color = "#c62828"
        else:
            pressure_color = "#6b7280"


        why_now = "".join(f"<li>{x}</li>" for x in regime_data.get("why_now", [])) or "<li>N/A</li>"
        why_not = "".join(f"<li>{x}</li>" for x in regime_data.get("why_not_now", [])) or "<li>N/A</li>"
        blockers = "".join(f"<li>{x}</li>" for x in timing_data.get("blockers", [])) or "<li>None</li>"
        reasons = "".join(f"<li>{x}</li>" for x in timing_data.get("reasons", [])) or "<li>N/A</li>"
        dyn_reasons = "".join(f"<li>{x}</li>" for x in dynamic_pick.get("reasons", [])) or "<li>N/A</li>"
        quality_warn = "".join(f"<li>{x}</li>" for x in quality_data.get("warnings", [])) or "<li>None</li>"
        quality_flags = "".join(f"<li>{x}</li>" for x in quality_data.get("anomaly_flags", [])) or "<li>None</li>"

        checklist = [
            f"Trade Allowed: {execution_data.get('allow_trade', False)}",
            f"Side: {execution_data.get('side', 'NO TRADE')}",
            f"Selected Strike: {dynamic_pick.get('strike', 'N/A')}",
            f"Entry LTP: {dynamic_pick.get('entry_ltp', 'N/A')}",
            f"Stop Loss: {execution_data.get('stop_loss_pct', 'N/A')}%",
            f"Target: {execution_data.get('target_pct', 'N/A')}%",
            f"Time Stop: {execution_data.get('time_stop_min', 'N/A')} min",
            f"Invalidation: {execution_data.get('invalidation_pct', 'N/A')}%",
            f"Expected Move: {execution_data.get('expected_move_pct', 'N/A')}%",
        ]
        checklist_html = "".join(f"<li>{item}</li>" for item in checklist)

        return f"""
        <html>
        <body style="font-family:Arial;background:#f4f6f8;padding:20px;">
        <h2 style="color:#2c3e50;">Option Chain Analysis (10-Min)</h2>
        <h3>{symbol}</h3>
        {replay_block}

        <table cellpadding="8" cellspacing="0" width="100%" style="background:#ffffff;border-radius:8px;">
            <tr><td><b>Spot</b></td><td>{spot}</td></tr>
            <tr><td><b>ATM</b></td><td>{atm}</td></tr>
            <tr><td><b>Max Pain</b></td><td>{max_pain}</td></tr>
            <tr><td><b>Max Pain Insight</b></td><td>{maxpain_note}</td></tr>
            <tr><td><b>PCR</b></td><td>{pcr}</td></tr>
            <tr><td><b>Interpretation</b></td><td><b style="color:{interpretation_color};">{interpretation_text}</b></td></tr>
        </table>

        <hr>
        <h3>Support/Resistance Calculation (ATM to ATM+2)</h3>
        <p>
        Resistance = Strike with Maximum <b>Call OI</b> among ATM, ATM+1, ATM+2<br>
        Support = Strike with Maximum <b>Put OI</b> among ATM, ATM+1, ATM+2
        </p>
        <table cellpadding="6" cellspacing="0" width="100%" style="background:#ffffff;border-radius:6px;">
            <tr><td><b>Final Resistance</b></td><td><b style="color:#1e8e3e;">{resistance}</b></td><td colspan="2">Max Call OI strike</td></tr>
            <tr><td><b>Final Support</b></td><td><b style="color:#c62828;">{support}</b></td><td colspan="2">Max Put OI strike</td></tr>
        </table>

        <hr>
        <h3>ATM Pressure Calculation</h3>
        <p>Cumulative OI change window: <b>09:15 IST to current snapshot</b></p>
        <table cellpadding="6" cellspacing="0" width="100%" style="background:#ffffff;border-radius:6px;">
            <tr><td><b>c1 (ATM Call OI Change)</b></td><td>{c1:.2f}</td></tr>
            <tr><td><b>c2 (ATM+1 Call OI Change)</b></td><td>{c2:.2f}</td></tr>
            <tr><td><b>c3 (ATM+2 Call OI Change)</b></td><td>{c3:.2f}</td></tr>
            <tr><td><b>Call Pressure (call_sum)</b></td><td>{call_sum:.2f}</td></tr>
            <tr><td><b>p1 (ATM Put OI Change)</b></td><td>{p1:.2f}</td></tr>
            <tr><td><b>p2 (ATM+1 Put OI Change)</b></td><td>{p2:.2f}</td></tr>
            <tr><td><b>p3 (ATM+2 Put OI Change)</b></td><td>{p3:.2f}</td></tr>
            <tr><td><b>Put Pressure (put_sum)</b></td><td>{put_sum:.2f}</td></tr>
            <tr><td><b>difference = call_sum - put_sum</b></td><td>{pressure_diff:.2f}</td></tr>
            <tr><td><b>Direction</b></td><td><b style="color:{pressure_color};">{pressure_direction}</b></td></tr>
        </table>

        <hr>
        <h3>Market Condition (Regime V2)</h3>
        <table cellpadding="6" cellspacing="0" width="100%" style="background:#ffffff;border-radius:6px;">
            <tr><td><b>Regime</b></td><td>{regime_data.get('label', 'UNKNOWN')}</td></tr>
            <tr><td><b>Regime Confidence</b></td><td>{regime_data.get('confidence', 0)}%</td></tr>
            <tr><td><b>Quality Usable</b></td><td>{quality_data.get('is_usable', False)}</td></tr>
        </table>
        <b>Why Now:</b><ul>{why_now}</ul>
        <b>Why Not Now:</b><ul>{why_not}</ul>

        <hr>
        <h3>Timing and Calibration</h3>
        <table cellpadding="6" cellspacing="0" width="100%" style="background:#ffffff;border-radius:6px;">
            <tr><td><b>Timing Score V2</b></td><td>{timing_data.get('timing_score_v2', 0)} / 100</td></tr>
            <tr><td><b>Entry Window</b></td><td>{timing_data.get('entry_window', 'WAIT')}</td></tr>
            <tr><td><b>Raw Prob Input</b></td><td>{timing_data.get('calibration_input_probability', 0):.3f}</td></tr>
            <tr><td><b>Calibrated Prob</b></td><td>{calibration_data.get('calibrated_probability', 0):.3f}</td></tr>
            <tr><td><b>Calibration Method</b></td><td>{calibration_data.get('method', 'identity')}</td></tr>
            <tr><td><b>Calibration Samples</b></td><td>{calibration_data.get('sample_size', 0)}</td></tr>
        </table>
        <b>Timing Reasons:</b><ul>{reasons}</ul>
        <b>Hard Filters / Blockers:</b><ul>{blockers}</ul>

        <hr>
        <h3>Dynamic OTM Selection</h3>
        <table cellpadding="6" cellspacing="0" width="100%" style="background:#ffffff;border-radius:6px;">
            <tr><td><b>Preferred Side</b></td><td>{execution_data.get('side', 'NO TRADE')}</td></tr>
            <tr><td><b>Selected Strike</b></td><td>{dynamic_pick.get('strike', 'N/A')}</td></tr>
            <tr><td><b>Entry LTP</b></td><td>{dynamic_pick.get('entry_ltp', 'N/A')}</td></tr>
            <tr><td><b>Selection Score</b></td><td>{dynamic_pick.get('score', 0)}</td></tr>
        </table>
        <b>Selection Drivers:</b><ul>{dyn_reasons}</ul>

        <hr>
        <h3>Execution Checklist</h3>
        <ul>{checklist_html}</ul>

        <hr>
        <h3>Probability and Scalp</h3>
        <p>
        Upside Probability: <b>{prob_data['upside_probability']}%</b><br>
        Downside Probability: <b>{prob_data['downside_probability']}%</b><br>
        Breakout Probability: <b>{prob_data['breakout_probability']}%</b><br>
        Calibrated Upside Prob: <b>{prob_data.get('calibrated_upside_probability', 0):.3f}</b>
        </p>
        <p>
        Signal: <b>{scalp_data['signal']}</b><br>
        Direction: <b>{scalp_data['direction']}</b><br>
        Directional Score: <b>{scalp_data['score']}</b><br>
        Risk Level: <b>{scalp_data['risk']}</b>
        </p>

        <hr>
        <h3>Institutional and Bias</h3>
        <table cellpadding="6" cellspacing="0" width="100%" style="background:#ffffff;border-radius:6px;">
            <tr><td><b>Institutional Score</b></td><td>{confidence_data['directional_score']}</td></tr>
            <tr><td><b>Institutional Level</b></td><td>{confidence_data['level']}</td></tr>
            <tr><td><b>Market Bias</b></td><td>{market_bias_data.get('market_bias', 'N/A')}</td></tr>
            <tr><td><b>Market Score</b></td><td>{market_bias_data.get('market_score', 0)}</td></tr>
            <tr><td><b>Greeks Bias</b></td><td>{geeks_data.get('bias', 'N/A')}</td></tr>
            <tr><td><b>Greeks Timing</b></td><td>{geeks_data.get('otm_timing_score', 0)}</td></tr>
        </table>

        <hr>
        <h3>OI Delta and Outlook</h3>
        <p>
        CE OI Delta: {oi_delta_data['ce_delta']}<br>
        PE OI Delta: {oi_delta_data['pe_delta']}<br>
        Flow: {oi_delta_data['classification']}<br>
        Acceleration: {oi_delta_data['acceleration_direction']} ({oi_delta_data['acceleration_probability']}%)
        </p>
        <p>
        Next 15 Min: {intraday_data['next_15']}<br>
        Next 30 Min: {intraday_data['next_30']}<br>
        Next 1 Hour: {intraday_data['next_60']}
        </p>

        <hr>
        <h3>Data Quality Guardrails</h3>
        <b>Warnings:</b><ul>{quality_warn}</ul>
        <b>Anomaly Flags:</b><ul>{quality_flags}</ul>

        </body>
        </html>
        """

