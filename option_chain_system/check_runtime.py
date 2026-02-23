"""
Runtime readiness check for env toggles and database tables.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from config.settings import settings
from database.db_connection import DatabaseConnection


REQUIRED_TABLES = [
    "option_chain_snapshot",
    "option_chain_summary",
    "scalp_score_tracking",
    "trade_signals",
    "trade_outcomes",
]


def print_settings_summary() -> None:
    print("Runtime Settings")
    print("----------------")
    print(f"TEST_MODE={settings.TEST_MODE}")
    print(f"ENABLE_ALL_ENHANCEMENTS={settings.ENABLE_ALL_ENHANCEMENTS}")
    print(f"ENABLE_GUARDRAILS={settings.ENABLE_GUARDRAILS}")
    print(f"ENABLE_OUTCOME_TRACKING={settings.ENABLE_OUTCOME_TRACKING}")
    print(f"ENABLE_TIMING_V2={settings.ENABLE_TIMING_V2}")
    print(f"ENABLE_REGIME_V2={settings.ENABLE_REGIME_V2}")
    print(f"ENABLE_DYNAMIC_OTM={settings.ENABLE_DYNAMIC_OTM}")
    print(f"ENABLE_CALIBRATION={settings.ENABLE_CALIBRATION}")
    print(f"CALIBRATION_MIN_SAMPLES={settings.CALIBRATION_MIN_SAMPLES}")
    print(f"OPTION_CHAIN_STRIKE_COUNT={settings.OPTION_CHAIN_STRIKE_COUNT}")
    print()


def validate_flag_combinations() -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    if settings.TEST_MODE and settings.ENABLE_OUTCOME_TRACKING:
        errors.append("ENABLE_OUTCOME_TRACKING=True requires TEST_MODE=False (DB writes are skipped in test mode).")

    if settings.ENABLE_ALL_ENHANCEMENTS and settings.TEST_MODE:
        warnings.append("ENABLE_ALL_ENHANCEMENTS=True with TEST_MODE=True limits outcome tracking due skipped DB writes.")

    if settings.ENABLE_CALIBRATION and not settings.ENABLE_OUTCOME_TRACKING:
        warnings.append("ENABLE_CALIBRATION=True without ENABLE_OUTCOME_TRACKING will usually have too few samples.")

    if settings.ENABLE_DYNAMIC_OTM and not settings.ENABLE_TIMING_V2:
        warnings.append("ENABLE_DYNAMIC_OTM=True while ENABLE_TIMING_V2=False may increase low-quality entries.")

    if settings.CALIBRATION_MIN_SAMPLES < 10:
        warnings.append("CALIBRATION_MIN_SAMPLES is very low; calibration may overfit.")

    if settings.OPTION_CHAIN_STRIKE_COUNT < 20:
        warnings.append("OPTION_CHAIN_STRIKE_COUNT < 20 can reduce regime and strike-selection quality.")

    return warnings, errors


def check_tables() -> bool:
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name = ANY(%s)
    """
    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, (REQUIRED_TABLES,))
        found = {row[0] for row in cursor.fetchall()}
    finally:
        cursor.close()
        DatabaseConnection.release_connection(conn)

    missing = [t for t in REQUIRED_TABLES if t not in found]
    if missing:
        print("Database Check: FAIL")
        print("Missing tables:", ", ".join(missing))
        return False

    print("Database Check: OK")
    return True


def apply_schema() -> None:
    schema_path = Path(__file__).resolve().parent / "database" / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")

    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"Schema applied from: {schema_path}")
    finally:
        cursor.close()
        DatabaseConnection.release_connection(conn)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check runtime readiness.")
    parser.add_argument("--skip-db", action="store_true", help="Skip database table checks")
    parser.add_argument(
        "--apply-missing-schema",
        action="store_true",
        help="If DB check fails, apply database/schema.sql and re-check once",
    )
    args = parser.parse_args()

    print_settings_summary()
    warnings, errors = validate_flag_combinations()
    if warnings:
        print("Config Warnings:")
        for w in warnings:
            print(f"- {w}")
        print()
    if errors:
        print("Config Errors:")
        for e in errors:
            print(f"- {e}")
        print()
        raise SystemExit(1)

    if args.skip_db:
        print("Database Check: SKIPPED")
        return

    ok = check_tables()
    if (not ok) and args.apply_missing_schema:
        print("Attempting schema apply...")
        apply_schema()
        ok = check_tables()

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
