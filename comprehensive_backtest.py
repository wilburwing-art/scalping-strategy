"""
Comprehensive 12-24 Month Backtest

Validates the unified strategy with extensive historical data and detailed analysis.

Options:
1. Extended sample data (immediate, no credentials needed)
2. Real OANDA data (requires v20.conf)

Usage:
    # Quick test with 12 months sample data
    uv run python comprehensive_backtest.py --months 12

    # Full 24 months sample data
    uv run python comprehensive_backtest.py --months 24

    # Real OANDA data (requires v20.conf)
    uv run python comprehensive_backtest.py --oanda --instrument EUR_USD --months 12
"""

import argparse
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, Optional
import os

from backtester import Backtester
from unified_strategy import UnifiedStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_extended_sample_data(
    instrument: str = "EUR_USD",
    months: int = 12,
    granularity_minutes: int = 5,
    output_file: str = "extended_historical_data.csv"
) -> pd.DataFrame:
    """
    Generate extended sample market data for multi-month backtesting.

    Creates realistic-looking price data with:
    - Multiple market regimes (trending, ranging, volatile)
    - Realistic bid/ask spreads
    - Volume patterns
    - Seasonal effects
    - News event spikes

    Args:
        instrument: Instrument name
        months: Number of months to generate
        granularity_minutes: Candle size in minutes
        output_file: CSV file to save data

    Returns:
        DataFrame with extended historical data
    """
    logger.info(f"Generating {months} months of sample data for {instrument}...")

    # Calculate number of candles
    candles_per_day = (24 * 60) // granularity_minutes
    total_days = months * 30
    num_candles = candles_per_day * total_days

    logger.info(f"Creating {num_candles:,} candles ({candles_per_day} per day, {total_days} days)")

    # Generate timestamps
    end_time = datetime(2024, 11, 1, 0, 0, 0)
    start_time = end_time - timedelta(days=total_days)
    timestamps = [start_time + timedelta(minutes=granularity_minutes*i) for i in range(num_candles)]

    # Starting price
    start_price = 1.0850

    # Generate returns with different market regimes
    np.random.seed(42)
    returns = np.zeros(num_candles)

    # Create market regimes (trending, ranging, volatile)
    regime_length = 500  # candles per regime
    num_regimes = num_candles // regime_length

    for i in range(num_regimes):
        start_idx = i * regime_length
        end_idx = min((i + 1) * regime_length, num_candles)

        # Randomly select regime type
        regime_type = np.random.choice(['trending_up', 'trending_down', 'ranging', 'volatile'])

        if regime_type == 'trending_up':
            # Uptrend with drift
            drift = 0.00003
            volatility = 0.0001
            returns[start_idx:end_idx] = np.random.normal(drift, volatility, end_idx - start_idx)

        elif regime_type == 'trending_down':
            # Downtrend with drift
            drift = -0.00003
            volatility = 0.0001
            returns[start_idx:end_idx] = np.random.normal(drift, volatility, end_idx - start_idx)

        elif regime_type == 'ranging':
            # Mean-reverting range
            volatility = 0.00008
            returns[start_idx:end_idx] = np.random.normal(0, volatility, end_idx - start_idx)
            # Add mean reversion
            for j in range(start_idx + 1, end_idx):
                # Pull back to mean
                cumulative = np.sum(returns[start_idx:j])
                returns[j] -= cumulative * 0.01

        else:  # volatile
            # High volatility period
            volatility = 0.0003
            returns[start_idx:end_idx] = np.random.normal(0, volatility, end_idx - start_idx)

    # Add occasional news spikes (5-10 per month)
    num_spikes = months * 7
    spike_indices = np.random.choice(num_candles, num_spikes, replace=False)
    for idx in spike_indices:
        spike_magnitude = np.random.choice([-1, 1]) * np.random.uniform(0.0005, 0.0015)
        returns[idx] += spike_magnitude

    # Calculate prices
    price_series = start_price * np.exp(np.cumsum(returns))

    # Generate OHLC with bid/ask
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, price_series)):
        # Intrabar volatility
        volatility = 0.00008 * (1 + abs(returns[i]) * 20)

        high = close + np.random.uniform(0, volatility)
        low = close - np.random.uniform(0, volatility)
        open_price = low + np.random.uniform(0, high - low)

        # Ensure OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Bid/ask spread (0.5-2.0 pips, wider during volatility)
        base_spread = 0.00005
        volatility_spread = abs(returns[i]) * 10
        spread = base_spread + volatility_spread
        spread = min(spread, 0.0002)  # Cap at 2 pips

        bid_close = close - spread / 2
        ask_close = close + spread / 2

        # Volume (higher during volatility and news)
        base_volume = 5000
        vol_multiplier = 1 + abs(returns[i]) * 100
        if i in spike_indices:
            vol_multiplier *= 2  # Double volume on news
        volume = int(base_volume * vol_multiplier * np.random.uniform(0.8, 1.2))

        row = {
            'time': timestamp,
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

    logger.info(f"✅ Extended data saved to {output_file}")
    logger.info(f"Date range: {df['time'].min()} to {df['time'].max()}")
    logger.info(f"Price range: {df['bid_close'].min():.5f} to {df['bid_close'].max():.5f}")
    logger.info(f"Total candles: {len(df):,}")

    return df


def run_comprehensive_backtest(
    data_file: str,
    initial_balance: float = 10000,
    output_prefix: str = "comprehensive_backtest"
):
    """
    Run comprehensive backtest with detailed analysis.

    Args:
        data_file: Path to CSV with historical data
        initial_balance: Starting balance
        output_prefix: Prefix for output files
    """
    logger.info("\n" + "="*70)
    logger.info("COMPREHENSIVE BACKTEST")
    logger.info("="*70)

    # Initialize strategy (backtest mode)
    strategy = UnifiedStrategy(
        enable_economic_calendar=False,
        enable_sentiment_analysis=False,
        enable_journaling=False,
        enable_monitoring=False,
        enable_agents=False,
        backtest_mode=True,
    )

    # Adjust parameters for backtesting
    strategy.volume_threshold = 100
    strategy.volatility_min = 0.00001

    # Initialize backtester
    backtester = Backtester(
        initial_balance=initial_balance,
        max_positions=3,
        risk_per_trade=1.0,
        use_realistic_costs=True,
        enable_risk_management=True,
    )

    # Load data
    backtester.load_csv_data(data_file)

    # Create strategy function
    def strategy_func(recent_data: pd.DataFrame, current_candle) -> Optional[Dict]:
        try:
            # Convert to candle objects
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

            # Check entry criteria
            if not strategy.should_enter_trade(indicators):
                return None

            # Get direction
            direction = strategy.get_trade_direction(indicators)
            if not direction:
                return None

            # Position sizing
            current_price = indicators["price"]
            atr = indicators["atr"]
            stop_loss_distance = atr * 1.5

            units = 10000

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
                }
            }

        except Exception as e:
            return None

    # Run backtest
    logger.info("\n🚀 Running backtest...\n")
    results = backtester.run(
        strategy_func,
        max_hold_bars=100,
        time_limit_hours=24,
    )

    # Display comprehensive results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print(f"\n📊 PERFORMANCE METRICS")
    print(f"{'─'*70}")
    print(f"Initial Balance:       ${initial_balance:,.2f}")
    print(f"Final Balance:         ${results['final_balance']:,.2f}")
    print(f"Total Return:          {results['total_return']:+.2f}%")
    print(f"Annualized Return:     {(results['total_return'] / (len(backtester.data) / (365 * 288))) if len(backtester.data) > 0 else 0:+.2f}%")
    print(f"\n📈 TRADE STATISTICS")
    print(f"{'─'*70}")
    print(f"Total Trades:          {results['total_trades']}")
    print(f"Winning Trades:        {results['winning_trades']}")
    print(f"Losing Trades:         {results['losing_trades']}")
    print(f"Win Rate:              {results['win_rate']:.1f}%")
    print(f"Average Win:           ${results['avg_win']:+.2f}")
    print(f"Average Loss:          ${results['avg_loss']:+.2f}")
    print(f"Profit Factor:         {results['profit_factor']:.2f}")
    print(f"\n⚡ RISK METRICS")
    print(f"{'─'*70}")
    print(f"Sharpe Ratio:          {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:          {results['max_drawdown']:.2f}%")
    print(f"Total Costs:           ${results['total_costs']:.2f}")
    print(f"Avg Hold Time:         {results['avg_hold_days']:.2f} days")
    print("="*70)

    # Analysis and recommendations
    print(f"\n📊 ANALYSIS")
    print(f"{'─'*70}")

    # Overall profitability
    if results['total_return'] > 5:
        print("✅ Strategy is PROFITABLE")
    elif results['total_return'] > 0:
        print("⚠️  Strategy is marginally profitable")
    else:
        print("❌ Strategy is UNPROFITABLE")

    # Risk-adjusted returns
    if results['sharpe_ratio'] > 1.5:
        print("✅ Excellent risk-adjusted returns (Sharpe > 1.5)")
    elif results['sharpe_ratio'] > 1.0:
        print("✅ Good risk-adjusted returns (Sharpe > 1.0)")
    elif results['sharpe_ratio'] > 0.5:
        print("⚠️  Moderate risk-adjusted returns (Sharpe 0.5-1.0)")
    else:
        print("❌ Poor risk-adjusted returns (Sharpe < 0.5)")

    # Drawdown
    if results['max_drawdown'] < 15:
        print("✅ Acceptable drawdown (< 15%)")
    elif results['max_drawdown'] < 25:
        print("⚠️  Moderate drawdown (15-25%)")
    else:
        print("❌ High drawdown (> 25%)")

    # Win rate
    if results['win_rate'] > 55:
        print("✅ Strong win rate (> 55%)")
    elif results['win_rate'] > 45:
        print("✅ Acceptable win rate (45-55%)")
    else:
        print("⚠️  Low win rate (< 45%)")

    # Trade frequency
    if results['total_trades'] > 0:
        trades_per_month = results['total_trades'] / (len(backtester.data) / (30 * 288))
        print(f"\n📅 Trade Frequency: {trades_per_month:.1f} trades per month")
        if trades_per_month < 1:
            print("⚠️  Very low trade frequency - strategy is highly selective")
        elif trades_per_month < 5:
            print("✅ Conservative trade frequency")
        else:
            print("✅ Active trading strategy")

    # Recommendation
    print(f"\n🎯 RECOMMENDATION")
    print(f"{'─'*70}")

    if (results['total_return'] > 5 and
        results['sharpe_ratio'] > 1.0 and
        results['max_drawdown'] < 20 and
        results['win_rate'] > 45):
        print("✅ Strategy shows promise! Proceed to:")
        print("   1. Run walk-forward validation (Phase 4B)")
        print("   2. Test on multiple instruments")
        print("   3. Paper trade for 60-90 days")
        print("   4. Consider Phase 4A (visualization) for detailed analysis")
    elif results['total_return'] > 0:
        print("⚠️  Strategy needs optimization:")
        print("   1. Consider parameter tuning (RSI thresholds, MA periods)")
        print("   2. Add more filters (volume, ATR)")
        print("   3. Test different entry/exit logic")
        print("   4. Run sensitivity analysis")
    else:
        print("❌ Strategy not viable in current form:")
        print("   1. Fundamental issues with entry logic")
        print("   2. Consider different timeframe or approach")
        print("   3. Review transaction costs impact")
        print("   4. May need complete redesign")

    print("="*70 + "\n")

    # Export results
    trades_df = backtester.get_trades_dataframe()
    if not trades_df.empty:
        trades_file = f"{output_prefix}_trades.csv"
        trades_df.to_csv(trades_file, index=False)
        logger.info(f"💾 Trade details saved to: {trades_file}")

    equity_df = backtester.get_equity_curve()
    if not equity_df.empty:
        equity_file = f"{output_prefix}_equity.csv"
        equity_df.to_csv(equity_file, index=False)
        logger.info(f"💾 Equity curve saved to: {equity_file}")

    # Save summary
    summary_file = f"{output_prefix}_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write("COMPREHENSIVE BACKTEST SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Date Range: {backtester.data['time'].min()} to {backtester.data['time'].max()}\n")
        f.write(f"Total Candles: {len(backtester.data):,}\n")
        f.write(f"Initial Balance: ${initial_balance:,.2f}\n")
        f.write(f"Final Balance: ${results['final_balance']:,.2f}\n")
        f.write(f"Total Return: {results['total_return']:+.2f}%\n")
        f.write(f"Total Trades: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate']:.1f}%\n")
        f.write(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}\n")
        f.write(f"Max Drawdown: {results['max_drawdown']:.2f}%\n")
        f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")

    logger.info(f"💾 Summary saved to: {summary_file}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="Comprehensive 12-24 Month Backtest")
    parser.add_argument("--months", type=int, default=12,
                       help="Number of months to backtest (default: 12)")
    parser.add_argument("--instrument", default="EUR_USD",
                       help="Instrument to test")
    parser.add_argument("--oanda", action="store_true",
                       help="Use real OANDA data (requires v20.conf)")
    parser.add_argument("--balance", type=float, default=10000,
                       help="Initial balance")
    parser.add_argument("--data-file", help="Use existing CSV data file")

    args = parser.parse_args()

    # Determine data source
    if args.data_file:
        # Use provided data file
        logger.info(f"Using existing data file: {args.data_file}")
        data_file = args.data_file
    elif args.oanda:
        # Check for OANDA credentials
        if not os.path.exists("v20.conf"):
            logger.error("❌ v20.conf not found. Create it from config.example.ini first.")
            logger.info("\nTo use OANDA data:")
            logger.info("1. Copy config.example.ini to v20.conf")
            logger.info("2. Add your OANDA API credentials")
            logger.info("3. Run: uv run python comprehensive_backtest.py --oanda --months 12")
            return

        # TODO: Implement OANDA data fetching
        logger.error("OANDA data fetching not yet implemented in this script")
        logger.info("For now, use sample data with: uv run python comprehensive_backtest.py --months 12")
        return
    else:
        # Generate extended sample data
        data_file = f"{args.instrument}_{args.months}month_sample.csv"
        if not os.path.exists(data_file):
            logger.info(f"Generating {args.months} months of sample data...")
            generate_extended_sample_data(
                instrument=args.instrument,
                months=args.months,
                output_file=data_file
            )
        else:
            logger.info(f"Using existing sample data: {data_file}")

    # Run backtest
    output_prefix = f"{args.instrument}_{args.months}month"
    run_comprehensive_backtest(
        data_file=data_file,
        initial_balance=args.balance,
        output_prefix=output_prefix
    )


if __name__ == "__main__":
    main()
