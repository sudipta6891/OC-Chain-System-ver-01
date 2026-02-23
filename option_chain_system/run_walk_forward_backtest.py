import argparse
import json
from backtesting.walk_forward_backtester import WalkForwardBacktester, BacktestConfig


def main():
    parser = argparse.ArgumentParser(description="Run walk-forward backtest for stored trade signals.")
    parser.add_argument("--symbol", default="NSE:NIFTYBANK-INDEX")
    parser.add_argument("--start-date", default="2026-02-01")
    parser.add_argument("--end-date", default="2026-02-23")
    parser.add_argument("--slippage-pct", type=float, default=0.35)
    parser.add_argument("--txn-cost-pct", type=float, default=0.10)
    parser.add_argument("--stop-loss-pct", type=float, default=25.0)
    parser.add_argument("--target-pct", type=float, default=45.0)
    parser.add_argument("--time-stop-min", type=int, default=30)
    parser.add_argument("--as-json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    cfg = BacktestConfig(
        slippage_pct=args.slippage_pct,
        txn_cost_pct=args.txn_cost_pct,
        default_stop_loss_pct=args.stop_loss_pct,
        default_target_pct=args.target_pct,
        default_time_stop_min=args.time_stop_min,
    )
    result = WalkForwardBacktester.run(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        cfg=cfg,
    )

    if args.as_json:
        print(json.dumps(result, indent=2))
        return

    print("\nWalk-Forward Backtest Result")
    print("----------------------------")
    print(f"Symbol: {result['symbol']}")
    print(f"Range: {result['start_date']} -> {result['end_date']}")
    print(f"Trades: {result['trades']}")
    print(f"Hit Rate: {result['hit_rate']:.2%}")
    print(f"Avg Net Return: {result['avg_net_return_pct']:.3f}%")
    print(f"Expectancy: {result['expectancy']:.5f}")
    print(f"Max Drawdown: {result['max_drawdown_pct']:.3f}%")


if __name__ == "__main__":
    main()
