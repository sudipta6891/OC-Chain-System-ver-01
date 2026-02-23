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
            <tr><td><b>Resistance</b></td><td>{resistance}</td></tr>
            <tr><td><b>Support</b></td><td>{support}</td></tr>
            <tr><td><b>Max Pain</b></td><td>{max_pain}</td></tr>
            <tr><td><b>PCR</b></td><td>{pcr}</td></tr>
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
        <p><b>PCR Interpretation:</b> {pcr_note}<br><b>Max Pain Insight:</b> {maxpain_note}</p>
        <b>Warnings:</b><ul>{quality_warn}</ul>
        <b>Anomaly Flags:</b><ul>{quality_flags}</ul>

        <hr>
        <h3>Recent Performance (30m Horizon)</h3>
        <table cellpadding="6" cellspacing="0" width="100%" style="background:#ffffff;border-radius:6px;">
            <tr><td><b>Trades</b></td><td>{performance_data.get('trades', 0)}</td></tr>
            <tr><td><b>Hit Rate</b></td><td>{performance_data.get('hit_rate', 0):.2%}</td></tr>
            <tr><td><b>Avg Return</b></td><td>{performance_data.get('avg_return_pct', 0):.2f}%</td></tr>
            <tr><td><b>Expectancy</b></td><td>{performance_data.get('expectancy', 0):.4f}</td></tr>
        </table>
        </body>
        </html>
        """

