"""Persist generated reports as browsable web pages."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import html
import json
import re
from zoneinfo import ZoneInfo

from database.db_connection import DatabaseConnection
from config.settings import settings
from historical_test_runner import HistoricalTestRunner


class ReportWebStore:
    @staticmethod
    def _app_timezone() -> ZoneInfo:
        try:
            return ZoneInfo(getattr(settings, "TIMEZONE", "Asia/Kolkata"))
        except Exception:
            return ZoneInfo("Asia/Kolkata")

    @classmethod
    def _to_app_timezone(cls, dt: datetime) -> datetime:
        tz = cls._app_timezone()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tz)
        return dt.astimezone(tz)

    @classmethod
    def _format_timestamp(cls, dt: datetime) -> tuple[str, str]:
        local_dt = cls._to_app_timezone(dt)
        iso_value = local_dt.isoformat(timespec="seconds")
        display_value = local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        return iso_value, display_value

    @staticmethod
    def _base_dir() -> Path:
        return Path(__file__).resolve().parents[1] / "reports" / "web"

    @staticmethod
    def _slugify_symbol(symbol: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol).strip("_") or "symbol"

    @classmethod
    def save_report(cls, symbol: str, subject: str, report_html: str) -> Path:
        base = cls._base_dir()
        symbol_dir = base / "symbols"
        history_root = base / "history"
        meta_dir = base / "meta"
        symbol_dir.mkdir(parents=True, exist_ok=True)
        history_root.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

        slug = cls._slugify_symbol(symbol)
        now_dt = datetime.now(tz=cls._app_timezone())
        now_iso, now_display = cls._format_timestamp(now_dt)
        ts_key = now_dt.strftime("%Y%m%d_%H%M%S")
        wrapped_html = cls._wrap_page(symbol=symbol, subject=subject, generated_at=now_display, body=report_html)
        report_path = symbol_dir / f"{slug}.html"
        history_dir = history_root / slug
        history_dir.mkdir(parents=True, exist_ok=True)
        history_path = history_dir / f"{ts_key}.html"
        report_path.write_text(wrapped_html, encoding="utf-8")
        history_path.write_text(wrapped_html, encoding="utf-8")

        meta = {
            "symbol": symbol,
            "slug": slug,
            "subject": subject,
            "generated_at": now_iso,
            "generated_at_iso": now_iso,
            "generated_at_display": now_display,
            "path": f"history/{slug}/{ts_key}.html",
            "source": "live",
        }
        (meta_dir / f"{slug}__{ts_key}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        cls._write_index()
        return report_path

    @classmethod
    def refresh_index(cls) -> None:
        cls._write_index()

    @classmethod
    def _backfill_from_database(cls, max_rows: int = 400) -> None:
        base = cls._base_dir()
        meta_dir = base / "meta"
        history_root = base / "history"
        meta_dir.mkdir(parents=True, exist_ok=True)
        history_root.mkdir(parents=True, exist_ok=True)

        query = """
            WITH ranked AS (
                SELECT
                    symbol,
                    snapshot_time,
                    spot_price,
                    atm_strike,
                    pcr,
                    resistance,
                    support,
                    max_pain,
                    structure,
                    trap_signal,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY snapshot_time DESC) AS rn
                FROM option_chain_summary
            )
            SELECT
                symbol, snapshot_time, spot_price, atm_strike, pcr,
                resistance, support, max_pain, structure, trap_signal
            FROM ranked
            WHERE rn <= %s
            ORDER BY snapshot_time DESC
        """
        conn = None
        cursor = None
        try:
            conn = DatabaseConnection.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (max_rows,))
            rows = cursor.fetchall()
        except Exception as exc:
            print(f"ReportWebStore DB backfill skipped: {exc}")
            return
        finally:
            if cursor:
                cursor.close()
            if conn:
                DatabaseConnection.release_connection(conn)

        for row in rows:
            symbol = str(row[0] or "UNKNOWN")
            snapshot_time = row[1]
            if snapshot_time is None:
                continue
            slug = cls._slugify_symbol(symbol)
            snapshot_local = cls._to_app_timezone(snapshot_time)
            ts_key = snapshot_local.strftime("%Y%m%d_%H%M%S")
            ts_iso, ts_display = cls._format_timestamp(snapshot_local)
            history_dir = history_root / slug
            history_dir.mkdir(parents=True, exist_ok=True)
            history_path = history_dir / f"{ts_key}.html"
            needs_rebuild = True
            if history_path.exists():
                try:
                    existing = history_path.read_text(encoding="utf-8", errors="ignore")
                    if "Option Chain Analysis (10-Min)" in existing:
                        needs_rebuild = False
                except Exception:
                    needs_rebuild = True

            if needs_rebuild:
                try:
                    full = HistoricalTestRunner.generate_report_html(symbol=symbol, target_time=snapshot_time)
                    wrapped = cls._wrap_page(
                        symbol=symbol,
                        subject=full["subject_line"],
                        generated_at=ts_display,
                        body=full["report_html"],
                    )
                    history_path.write_text(wrapped, encoding="utf-8")
                except Exception:
                    history_path.write_text(
                        cls._build_db_summary_page(
                            symbol=symbol,
                            snapshot_display=ts_display,
                            spot=row[2],
                            atm=row[3],
                            pcr=row[4],
                            resistance=row[5],
                            support=row[6],
                            max_pain=row[7],
                            structure=row[8],
                            trap=row[9],
                        ),
                        encoding="utf-8",
                    )

            meta = {
                "symbol": symbol,
                "slug": slug,
                "subject": f"Historical DB Snapshot - {symbol}",
                "generated_at": ts_iso,
                "generated_at_iso": ts_iso,
                "generated_at_display": ts_display,
                "path": f"history/{slug}/{ts_key}.html",
                "source": "db",
            }
            (meta_dir / f"{slug}__{ts_key}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @classmethod
    def _write_index(cls) -> None:
        base = cls._base_dir()
        meta_dir = base / "meta"
        limit = max(1, int(getattr(settings, "WEB_HISTORY_LIMIT", 20)))
        cls._backfill_from_database(max_rows=limit)

        rows: list[dict] = []
        if meta_dir.exists():
            for p in sorted(meta_dir.glob("*.json")):
                try:
                    rows.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception:
                    continue

        rows.sort(key=lambda x: x.get("generated_at_iso", x.get("generated_at", "")), reverse=True)

        # Keep latest `limit` rows per symbol in payload.
        counts: dict[str, int] = {}
        filtered_rows: list[dict] = []
        for row in rows:
            symbol = str(row.get("symbol", "UNKNOWN"))
            c = counts.get(symbol, 0)
            if c >= limit:
                continue
            counts[symbol] = c + 1
            filtered_rows.append(row)
        rows = filtered_rows

        # Ensure selector semantics: only latest row per symbol is shown as live,
        # all older rows are labeled db.
        live_assigned: set[str] = set()
        for row in rows:
            symbol = str(row.get("symbol", "UNKNOWN"))
            if symbol not in live_assigned:
                row["source"] = "live"
                live_assigned.add(symbol)
            else:
                row["source"] = "db"

        rows_json = json.dumps(rows)
        default_path = rows[0]["path"] if rows else ""
        page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Option Chain Report Viewer</title>
  <style>
    :root {{
      --bg: #0e1320;
      --panel: #151d30;
      --text: #eaf0ff;
      --muted: #9fb0d3;
      --accent: #33b8ff;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: radial-gradient(1200px 600px at 10% -10%, #1f2b47 0%, var(--bg) 45%);
      color: var(--text);
    }}
    .wrap {{
      max-width: 1200px;
      margin: 18px auto;
      padding: 0 14px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid #25355d;
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 12px;
    }}
    .title {{
      margin: 0 0 8px 0;
      font-size: 20px;
    }}
    .hint {{
      color: var(--muted);
      font-size: 13px;
      margin: 0 0 10px 0;
    }}
    .live-clock {{
      color: #d8e6ff;
      font-size: 13px;
      margin: 0 0 10px 0;
    }}
    select {{
      width: 100%;
      background: #0d1424;
      border: 1px solid #2a3e6b;
      color: var(--text);
      padding: 10px;
      border-radius: 8px;
    }}
    iframe {{
      width: 100%;
      height: calc(100vh - 180px);
      border: 1px solid #2a3e6b;
      border-radius: 10px;
      background: #ffffff;
    }}
    .empty {{
      color: var(--muted);
      text-align: center;
      padding: 28px;
      border: 1px dashed #345;
      border-radius: 10px;
    }}
    .footer {{
      margin-top: 14px;
      background: linear-gradient(90deg, #15284f, #1f3b75);
      border: 1px solid #36579c;
      border-radius: 10px;
      padding: 12px 14px;
      text-align: center;
      color: #ffffff;
      font-weight: 700;
      letter-spacing: 0.2px;
    }}
    .footer small {{
      display: block;
      margin-top: 4px;
      font-weight: 600;
      color: #d8e6ff;
    }}
    a {{
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1 class="title">Option Chain Report Viewer</h1>
      <p class="hint">Select symbol, then time. Data includes live HTML reports + DB historical snapshots.</p>
      <p class="live-clock">Current Time: <b id="liveCurrentTime">--</b></p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        <select id="symbolSelect"></select>
        <select id="timeSelect"></select>
      </div>
    </div>
    <div class="card">
      {f"<iframe id='reportFrame' src='{html.escape(default_path)}'></iframe>" if default_path else "<div class='empty'>No generated reports yet. Run one cycle first.</div>"}
    </div>
    <div class="footer">
      Copyrighted to: Sudipta Bhattacharya
      <small>Contact: +91-9831619260</small>
    </div>
  </div>
  <script>
    const rows = {rows_json};
    const symbolEl = document.getElementById("symbolSelect");
    const timeEl = document.getElementById("timeSelect");
    const frame = document.getElementById("reportFrame");
    const liveCurrentTimeEl = document.getElementById("liveCurrentTime");

    function updateLiveCurrentTime() {{
      if (!liveCurrentTimeEl) return;
      const now = new Date();
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, "0");
      const d = String(now.getDate()).padStart(2, "0");
      const hh = String(now.getHours()).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      const ss = String(now.getSeconds()).padStart(2, "0");
      liveCurrentTimeEl.textContent = `${{y}}-${{m}}-${{d}} ${{hh}}:${{mm}}:${{ss}}`;
    }}

    function uniqueSymbols() {{
      const set = new Set();
      rows.forEach(r => set.add(r.symbol || "UNKNOWN"));
      return Array.from(set);
    }}

    function fillSymbols() {{
      if (!symbolEl) return;
      const symbols = uniqueSymbols();
      symbolEl.innerHTML = symbols.length
        ? symbols.map((s, i) => `<option value="${{s}}"${{i===0 ? " selected" : ""}}>${{s}}</option>`).join("")
        : "<option value=''>No symbols</option>";
    }}

    function fillTimes() {{
      if (!symbolEl || !timeEl) return;
      const symbol = symbolEl.value;
      const filtered = rows.filter(r => (r.symbol || "UNKNOWN") === symbol);
      filtered.sort((a, b) => ((a.generated_at_iso || a.generated_at || "") < (b.generated_at_iso || b.generated_at || "") ? 1 : -1));
      timeEl.innerHTML = filtered.length
        ? filtered.map((r, i) => `<option value="${{r.path}}"${{i===0 ? " selected" : ""}}>${{r.generated_at_display || r.generated_at}} (${{r.source || "n/a"}})</option>`).join("")
        : "<option value=''>No time points</option>";
      if (frame) {{
        frame.src = timeEl.value || "about:blank";
      }}
    }}

    if (symbolEl && timeEl && frame) {{
      updateLiveCurrentTime();
      setInterval(updateLiveCurrentTime, 1000);
      fillSymbols();
      fillTimes();
      const AUTO_REFRESH_MS = 120000;
      let lastManualInteractionAt = Date.now();

      const markManualInteraction = () => {{
        lastManualInteractionAt = Date.now();
      }};

      symbolEl.addEventListener("change", () => {{
        markManualInteraction();
        fillTimes();
      }});
      timeEl.addEventListener("change", () => {{
        markManualInteraction();
        frame.src = timeEl.value || "about:blank";
      }});

      setInterval(() => {{
        if (Date.now() - lastManualInteractionAt < AUTO_REFRESH_MS) {{
          return;
        }}
        if (timeEl.value && !timeEl.value.endsWith("about:blank")) {{
          const q = "t=" + Date.now();
          frame.src = timeEl.value + (timeEl.value.includes("?") ? "&" : "?") + q;
        }}
      }}, AUTO_REFRESH_MS);
    }}
  </script>
</body>
</html>
"""
        (base / "index.html").write_text(page, encoding="utf-8")

    @staticmethod
    def _build_db_summary_page(
        symbol: str,
        snapshot_display: str,
        spot,
        atm,
        pcr,
        resistance,
        support,
        max_pain,
        structure,
        trap,
    ) -> str:
        def fmt(x) -> str:
            if x is None:
                return "N/A"
            try:
                return f"{float(x):.2f}"
            except Exception:
                return html.escape(str(x))

        safe_symbol = html.escape(symbol)
        safe_ts = html.escape(snapshot_display)
        safe_structure = html.escape(str(structure or "N/A"))
        safe_trap = html.escape(str(trap or "N/A"))
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DB Snapshot - {safe_symbol}</title>
</head>
<body style="font-family:Segoe UI,Tahoma,sans-serif;background:#f4f6f8;padding:20px;">
  <h2>Historical DB Snapshot</h2>
  <p><b>Symbol:</b> {safe_symbol}<br><b>Snapshot Time:</b> {safe_ts}</p>
  <table cellpadding="8" cellspacing="0" width="100%" style="background:#ffffff;border-radius:8px;">
    <tr><td><b>Spot</b></td><td>{fmt(spot)}</td></tr>
    <tr><td><b>ATM</b></td><td>{fmt(atm)}</td></tr>
    <tr><td><b>PCR</b></td><td>{fmt(pcr)}</td></tr>
    <tr><td><b>Resistance</b></td><td>{fmt(resistance)}</td></tr>
    <tr><td><b>Support</b></td><td>{fmt(support)}</td></tr>
    <tr><td><b>Max Pain</b></td><td>{fmt(max_pain)}</td></tr>
    <tr><td><b>Structure</b></td><td>{safe_structure}</td></tr>
    <tr><td><b>Trap Signal</b></td><td>{safe_trap}</td></tr>
  </table>
  <div style="margin-top:18px;background:#1f3b75;color:#fff;border-radius:10px;padding:12px 14px;text-align:center;font-weight:700;">
    Copyrighted to: Sudipta Bhattacharya<br>
    <span style="font-weight:600;color:#d8e6ff;">Contact: +91-9831619260</span>
  </div>
</body>
</html>
"""

    @staticmethod
    def _wrap_page(symbol: str, subject: str, generated_at: str, body: str) -> str:
        safe_symbol = html.escape(symbol)
        safe_subject = html.escape(subject)
        safe_generated_at = html.escape(generated_at)
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_subject}</title>
</head>
<body>
  <div style="font-family:Segoe UI,Tahoma,sans-serif;background:#0e1320;color:#dce8ff;padding:10px 14px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;">
    <div><b>{safe_symbol}</b> | Generated: {safe_generated_at}</div>
    <div>Current Time: <b id="liveCurrentTime">--</b></div>
  </div>
  {body}
  <script>
    (function () {{
      const clockEl = document.getElementById("liveCurrentTime");
      if (!clockEl) return;
      const tick = () => {{
        const now = new Date();
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, "0");
        const d = String(now.getDate()).padStart(2, "0");
        const hh = String(now.getHours()).padStart(2, "0");
        const mm = String(now.getMinutes()).padStart(2, "0");
        const ss = String(now.getSeconds()).padStart(2, "0");
        clockEl.textContent = `${{y}}-${{m}}-${{d}} ${{hh}}:${{mm}}:${{ss}}`;
      }};
      tick();
      setInterval(tick, 1000);
    }})();
  </script>
  <div style="font-family:Segoe UI,Tahoma,sans-serif;margin:0;background:#1f3b75;color:#fff;padding:12px 14px;text-align:center;font-weight:700;">
    Copyrighted to: Sudipta Bhattacharya<br>
    <span style="font-weight:600;color:#d8e6ff;">Contact: +91-9831619260</span>
  </div>
</body>
</html>
"""
