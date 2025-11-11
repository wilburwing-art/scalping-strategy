"""
Example Backtest Using Unified Strategy

This demonstrates how to backtest the unified strategy with:
- FIXED RSI logic (mean reversion)
- Realistic costs (spread, slippage, swap)
- Risk management enforcement
- Multi-timeframe analysis
- Comprehensive performance metrics

Usage:
    # Basic backtest with CSV data
    uv run example_backtest.py --data historical_data.csv

    # Backtest with OANDA data (requires credentials)
    uv run example_backtest.py --oanda --instrument EUR_USD --start 2024-01-01 --end 2024-12-31

    # Generate sample data for testing
    uv run example_backtest.py --generate-sample
"""

import argparse
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, Optional

# Our modules
from backtester import Backtester
from unified_strategy import UnifiedStrategy
from v20 import Context
import configparser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_sample_data(
    instrument: str = "EUR_USD",
    start_price: float = 1.0850,
    num_candles: int = 10000,
    output_file: str = "sample_backtest_data.csv"
) -> pd.DataFrame:
    """
    Generate sample market data for backtesting.

    Creates realistic-looking price data with:
    - Realistic bid/ask spreads
    - Trending and ranging periods
    - Volume patterns
    - Volatility clustering

    Args:
        instrument: Instrument name
        start_price: Starting price
        num_candles: Number of candles to generate
        output_file: CSV file to save data

    Returns:
        DataFrame with sample data
    """
    logger.info(f"Generating {num_candles} sample candles for {instrument}...")

    # Generate timestamps (5-min candles)
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [start_time + timedelta(minutes=5*i) for i in range(num_candles)]

    # Generate price data with trends
    np.random.seed(42)

    # Random walk with drift and trends
    returns = np.random.normal(0.00001, 0.0002, num_candles)

    # Add trend periods
    for i in range(0, num_candles, 500):
        trend_direction = np.random.choice([-1, 1])
        trend_strength = np.random.uniform(0.00002, 0.00005)
        returns[i:i+500] += trend_direction * trend_strength

    # Calculate prices
    close_prices = start_price * np.exp(np.cumsum(returns))

    # Generate OHLC
    data = []
    for i, close in enumerate(close_prices):
        # Intrabar volatility
        volatility = 0.0001 * (1 + abs(returns[i]) * 20)

        high = close + np.random.uniform(0, volatility)
        low = close - np.random.uniform(0, volatility)
        open_price = low + np.random.uniform(0, high - low)

        # Bid/ask spread (0.5-2.0 pips)
        spread = 0.00005 + np.random.uniform(0, 0.00015)

        mid_close = close
        bid_close = mid_close - spread / 2
        ask_close = mid_close + spread / 2

        # Volume (higher during trends and volatility)
        base_volume = 5000
        vol_multiplier = 1 + abs(returns[i]) * 100
        volume = int(base_volume * vol_multiplier * np.random.uniform(0.8, 1.2))

        row = {
            'time': timestamps[i],
            'instrument': instrument,
            'bid_open': open_price - spread / 2,
            'bid_high': high - spread / 2,
            'bid_low': low - spread / 2,
            'bid_close': bid_close,
            'ask_open': open_price + spread / 2,
            'ask_high': high + spread / 2,
            'ask_low': low + spread / 2,
            'ask_close': ask_close,
            'volume': volume,
        }
        data.append(row)

    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)

    logger.info(f"✅ Sample data saved to {output_file}")
    logger.info(f"Date range: {df['time'].min()} to {df['time'].max()}")
    logger.info(f"Price range: {df['bid_close'].min():.5f} to {df['bid_close'].max():.5f}")

    return df


def create_strategy_function(strategy: UnifiedStrategy):
    """
    Create a strategy function for the backtester.

    This wraps the unified strategy's logic for use with the backtester.
    """
    def strategy_func(recent_data: pd.DataFrame, current_candle) -> Optional[Dict]:
        """
        Strategy function called by backtester for each candle.

        Args:
            recent_data: Recent historical data
            current_candle: Current candle being evaluated

        Returns:
            Signal dict or None
        """
        try:
            # Convert DataFrame to candle-like objects for indicators
            # This is a simplified version - you might need to adapt
            # based on your actual data structure

            class FakeCandle:
                def __init__(self, row):
                    self.mid = type('obj', (object,), {
                        'c': row.get('bid_close', 0),
                        'h': row.get('bid_high', 0),
                        'l': row.get('bid_low', 0),
                        'o': row.get('bid_open', 0),
                    })
                    self.volume = row.get('volume', 0)

            candles = [FakeCandle(row) for _, row in recent_data.iterrows()]

            if len(candles) < 20:
                return None

            # Calculate indicators
            indicators = strategy.calculate_indicators(candles)
            if not indicators:
                return None

            # Check entry criteria (FIXED RSI logic)
            if not strategy.should_enter_trade(indicators):
                return None

            # Get direction (FIXED RSI logic)
            direction = strategy.get_trade_direction(indicators)
            if not direction:
                return None

            # Calculate position size
            current_price = indicators["price"]
            atr = indicators["atr"]
            stop_loss_distance = atr * 1.5

            # Simple position size for backtest
            units = 10000  # 1 mini lot

            if direction == "BUY":
                stop_loss = current_price - stop_loss_distance
                take_profit = current_price + (stop_loss_distance * strategy.reward_risk_ratio)
            else:
                units = -units
                stop_loss = current_price + stop_loss_distance
                take_profit = current_price - (stop_loss_distance * strategy.reward_risk_ratio)

            return {
                "action": direction,
                "units": units,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "metadata": {
                    "rsi": indicators["rsi"],
                    "atr": atr,
                    "ma_short": indicators["ma_short"],
                    "ma_long": indicators["ma_long"],
                }
            }

        except Exception as e:
            logger.debug(f"Strategy evaluation error: {e}")
            return None

    return strategy_func


def run_backtest_csv(csv_file: str, initial_balance: float = 10000):
    """Run backtest using CSV data"""
    logger.info(f"\n{'='*70}")
    logger.info("BACKTEST: CSV DATA")
    logger.info(f"{'='*70}")

    # Initialize strategy
    strategy = UnifiedStrategy(
        enable_economic_calendar=False,  # No calendar for backtest
        enable_sentiment_analysis=False,  # No sentiment for backtest
        enable_journaling=False,  # No journal for backtest
        enable_monitoring=False,  # No monitoring for backtest
        enable_agents=False,  # No agents for backtest
        backtest_mode=True,  # Skip OANDA API initialization
    )

    # Initialize backtester
    backtester = Backtester(
        initial_balance=initial_balance,
        max_positions=3,
        risk_per_trade=1.0,
        use_realistic_costs=True,
        enable_risk_management=True,
    )

    # Load data
    backtester.load_csv_data(csv_file)

    # Create strategy function
    strategy_func = create_strategy_function(strategy)

    # Run backtest
    logger.info("\n🚀 Running backtest...\n")
    results = backtester.run(
        strategy_func,
        max_hold_bars=100,
        time_limit_hours=24,
    )

    # Display results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print(f"Initial Balance:    ${initial_balance:,.2f}")
    print(f"Final Balance:      ${results['final_balance']:,.2f}")
    print(f"Total Return:       {results['total_return']:+.2f}%")
    print(f"Total Trades:       {results['total_trades']}")
    print(f"Winning Trades:     {results['winning_trades']}")
    print(f"Losing Trades:      {results['losing_trades']}")
    print(f"Win Rate:           {results['win_rate']:.1f}%")
    print(f"Average Win:        ${results['avg_win']:+.2f}")
    print(f"Average Loss:       ${results['avg_loss']:+.2f}")
    print(f"Profit Factor:      {results['profit_factor']:.2f}")
    print(f"Sharpe Ratio:       {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:       {results['max_drawdown']:.2f}%")
    print(f"Total Costs:        ${results['total_costs']:.2f}")
    print(f"Avg Hold Time:      {results['avg_hold_days']:.2f} days")
    print("="*70)

    # Analysis
    print("\n📊 ANALYSIS:")
    if results['total_return'] > 0:
        print("✅ Strategy is PROFITABLE")
    else:
        print("❌ Strategy is UNPROFITABLE")

    if results['sharpe_ratio'] > 1.0:
        print("✅ Good risk-adjusted returns (Sharpe > 1.0)")
    else:
        print("⚠️  Poor risk-adjusted returns (Sharpe < 1.0)")

    if results['max_drawdown'] < 20:
        print("✅ Acceptable drawdown (< 20%)")
    else:
        print("⚠️  High drawdown (> 20%)")

    if results['win_rate'] > 50:
        print("✅ Win rate above 50%")
    else:
        print("⚠️  Win rate below 50%")

    # Get trades DataFrame for analysis
    trades_df = backtester.get_trades_dataframe()
    if not trades_df.empty:
        output_file = "backtest_trades.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"\n💾 Trade-by-trade results saved to: {output_file}")

    # Get equity curve
    equity_df = backtester.get_equity_curve()
    if not equity_df.empty:
        output_file = "backtest_equity_curve.csv"
        equity_df.to_csv(output_file, index=False)
        print(f"💾 Equity curve saved to: {output_file}")

    print("\n" + "="*70 + "\n")

    return results


def run_backtest_oanda(
    config_file: str,
    instrument: str,
    start_date: str,
    end_date: str,
    granularity: str = "M5",
    initial_balance: float = 10000
):
    """Run backtest using OANDA data"""
    logger.info(f"\n{'='*70}")
    logger.info("BACKTEST: OANDA DATA")
    logger.info(f"{'='*70}")
    logger.info(f"Instrument: {instrument}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Granularity: {granularity}")

    # Load config
    parser = configparser.ConfigParser()
    parser.read(config_file)

    config = {
        "hostname": parser["practice"]["hostname"],
        "token": parser["practice"]["token"],
        "account_id": parser["practice"]["account_id"],
    }

    # Create API context
    ctx = Context(config["hostname"], config["token"])

    # Initialize strategy
    strategy = UnifiedStrategy(
        config_file=config_file,
        enable_economic_calendar=False,
        enable_sentiment_analysis=False,
        enable_journaling=False,
        enable_monitoring=False,
        enable_agents=False,
    )

    # Initialize backtester
    backtester = Backtester(
        initial_balance=initial_balance,
        max_positions=3,
        risk_per_trade=1.0,
        use_realistic_costs=True,
        enable_risk_management=True,
    )

    # Load data from OANDA
    logger.info("\n📥 Fetching historical data from OANDA...")
    backtester.load_oanda_data(
        ctx,
        instrument,
        start_date,
        end_date,
        granularity
    )

    # Create strategy function
    strategy_func = create_strategy_function(strategy)

    # Run backtest
    logger.info("\n🚀 Running backtest...\n")
    results = backtester.run(
        strategy_func,
        max_hold_bars=100,
        time_limit_hours=24,
    )

    # Display results (same as CSV version)
    # ... (copy display code from run_backtest_csv)

    return results


def main():
    parser = argparse.ArgumentParser(description="Backtest Unified Strategy")
    parser.add_argument("--generate-sample", action="store_true",
                       help="Generate sample data for testing")
    parser.add_argument("--data", default="sample_backtest_data.csv",
                       help="CSV file with historical data")
    parser.add_argument("--oanda", action="store_true",
                       help="Use OANDA data instead of CSV")
    parser.add_argument("--config", default="v20.conf",
                       help="OANDA config file")
    parser.add_argument("--instrument", default="EUR_USD",
                       help="Instrument to backtest")
    parser.add_argument("--start", default="2024-01-01",
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2024-12-31",
                       help="End date (YYYY-MM-DD)")
    parser.add_argument("--balance", type=float, default=10000,
                       help="Initial balance")

    args = parser.parse_args()

    if args.generate_sample:
        # Generate sample data
        generate_sample_data(
            instrument=args.instrument,
            num_candles=10000,
            output_file=args.data
        )
        print(f"\n✅ Sample data generated: {args.data}")
        print(f"Run backtest with: uv run example_backtest.py --data {args.data}\n")
        return

    if args.oanda:
        # Run with OANDA data
        run_backtest_oanda(
            args.config,
            args.instrument,
            args.start,
            args.end,
            initial_balance=args.balance
        )
    else:
        # Run with CSV data
        run_backtest_csv(args.data, initial_balance=args.balance)


if __name__ == "__main__":
    main()
