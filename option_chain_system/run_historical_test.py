# run_historical_test.py

from historical_test_runner import HistoricalTestRunner

HistoricalTestRunner.run(
    symbol="NSE:NIFTYBANK-INDEX",
    date_str="2026-02-20",
    time_str="10:00"
)