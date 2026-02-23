"""
Smart Scheduler
- TEST_MODE -> Every 1 minute
- PRODUCTION -> Every 10 minutes (9:10 AM - 3:30 PM IST)
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from run_engine import run_option_chain
from config.symbols import SYMBOLS
from config.settings import settings
from database.cleanup_manager import CleanupManager


TIMEZONE = pytz.timezone("Asia/Kolkata")


def _effective_symbols() -> list[str]:
    if settings.TEST_MODE and settings.TEST_SYMBOLS:
        return settings.TEST_SYMBOLS
    return SYMBOLS


def print_feature_flags() -> None:
    print("Feature Flags")
    print("-------------")
    print(f"TEST_MODE={settings.TEST_MODE}")
    print(f"ENABLE_ALL_ENHANCEMENTS={settings.ENABLE_ALL_ENHANCEMENTS}")
    print(f"ENABLE_GUARDRAILS={settings.ENABLE_GUARDRAILS}")
    print(f"ENABLE_OUTCOME_TRACKING={settings.ENABLE_OUTCOME_TRACKING}")
    print(f"ENABLE_TIMING_V2={settings.ENABLE_TIMING_V2}")
    print(f"ENABLE_REGIME_V2={settings.ENABLE_REGIME_V2}")
    print(f"ENABLE_DYNAMIC_OTM={settings.ENABLE_DYNAMIC_OTM}")
    print(f"ENABLE_CALIBRATION={settings.ENABLE_CALIBRATION}")
    print(f"CALIBRATION_MIN_SAMPLES={settings.CALIBRATION_MIN_SAMPLES}")
    print(f"OPTION_CHAIN_STRIKE_COUNT={settings.OPTION_CHAIN_STRIKE_COUNT}\n")
    print(f"TEST_INTERVAL_MINUTES={settings.TEST_INTERVAL_MINUTES}")
    print(f"TEST_SYMBOLS={settings.TEST_SYMBOLS if settings.TEST_SYMBOLS else 'ALL_DEFAULT'}")
    print(f"EFFECTIVE_SYMBOLS={_effective_symbols()}\n")


def job():
    now = datetime.now(TIMEZONE)
    print("\n===========================================")
    print(f"Running Market Cycle at {now}")
    print("===========================================\n")
    for symbol in _effective_symbols():
        print(f"Processing {symbol}...\n")
        run_option_chain(symbol)
    print("\nCycle Completed\n")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    print_feature_flags()

    if settings.TEST_MODE:
        interval = settings.TEST_INTERVAL_MINUTES
        scheduler.add_job(
            job,
            "interval",
            minutes=interval,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
        print("TEST MODE ENABLED")
        print(f"Running every {interval} minute(s) (No market time restriction)\n")
    else:
        scheduler.add_job(
            job,
            CronTrigger(day_of_week="mon-fri", hour="9", minute="10,20,30,40,50"),
            misfire_grace_time=30,
        )
        scheduler.add_job(
            job,
            CronTrigger(day_of_week="mon-fri", hour="10-14", minute="0,10,20,30,40,50"),
            misfire_grace_time=30,
        )
        scheduler.add_job(
            job,
            CronTrigger(day_of_week="mon-fri", hour="15", minute="0,10,20,30"),
            misfire_grace_time=30,
        )
        scheduler.add_job(
            CleanupManager.cleanup_old_data,
            CronTrigger(day_of_week="mon-fri", hour="9", minute="25"),
            misfire_grace_time=60,
        )
        print("PRODUCTION MODE ENABLED")
        print("Running every 10 minutes (9:10 AM - 3:30 PM, Mon-Fri)\n")

    scheduler.start()
