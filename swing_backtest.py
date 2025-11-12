#!/usr/bin/env python3
"""
Swing Trading Strategy Backtest
Tests the 4H swing strategy over 12-24 months to validate profitability
before paper trading or live deployment.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_4h_sample_data(
    instrument: str = "EUR_USD",
    months: int = 12,
    output_file: str = "swing_backtest_data.csv"
) -> str:
    """
    Generate 12 months of 4H candle data for swing trading backtest.

    4H candles = 6 candles per day = ~2,160 candles per year
    """
    logger.info(f"Generating {months} months of 4H sample data...")

    # Calculate number of candles (6 per day)
    candles_per_day = 6
    total_candles = months * 30 * candles_per_day  # ~2,160 for 12 months

    # Start date
    start_date = datetime(2024, 1, 1)

    # Generate realistic price data
    base_price = 1.1000  # EUR/USD base
    current_price = base_price

    candles = []

    # Market regimes (each lasts ~1 month)
    regimes = ["trending_up", "ranging", "trending_down", "volatile"] * (months // 4 + 1)
    candles_per_regime = total_candles // len(regimes)

    for i in range(total_candles):
        # Determine current regime
        regime_idx = i // candles_per_regime
        if regime_idx >= len(regimes):
            regime_idx = len(regimes) - 1
        regime = regimes[regime_idx]

        # 4H candle timestamp
        timestamp = start_date + timedelta(hours=4 * i)

        # Skip weekends (forex closed)
        if timestamp.weekday() >= 5:  # Saturday or Sunday
            continue

        # Generate OHLC based on regime
        if regime == "trending_up":
            # Strong uptrend: +30-50 pips per 4H candle on average
            trend = random.uniform(0.0015, 0.0025)  # 15-25 pips
            volatility = random.uniform(0.0005, 0.0015)  # 5-15 pips
        elif regime == "trending_down":
            # Strong downtrend: -30-50 pips per 4H candle on average
            trend = random.uniform(-0.0025, -0.0015)
            volatility = random.uniform(0.0005, 0.0015)
        elif regime == "ranging":
            # Sideways: small moves
            trend = random.uniform(-0.0005, 0.0005)  # +/- 5 pips
            volatility = random.uniform(0.0003, 0.0008)  # 3-8 pips
        else:  # volatile
            # High volatility, no clear direction
            trend = random.uniform(-0.0010, 0.0010)
            volatility = random.uniform(0.0020, 0.0040)  # 20-40 pips

        # Calculate OHLC
        open_price = current_price

        # Add some randomness to each candle
        high_move = abs(random.gauss(volatility, volatility * 0.3))
        low_move = abs(random.gauss(volatility, volatility * 0.3))

        high = open_price + high_move
        low = open_price - low_move
        close = open_price + trend + random.gauss(0, volatility * 0.5)

        # Ensure OHLC relationships are valid
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Volume (higher during trending periods)
        if regime in ["trending_up", "trending_down"]:
            volume = random.randint(800, 2000)
        else:
            volume = random.randint(400, 1200)

        # Bid/Ask spread (typical EUR/USD: 0.5-1.5 pips)
        spread = random.uniform(0.00005, 0.00015)
        bid = close
        ask = close + spread

        candles.append({
            "time": timestamp.isoformat(),
            "volume": volume,
            "open": round(open_price, 5),
            "high": round(high, 5),
            "low": round(low, 5),
            "close": round(close, 5),
            "bid": round(bid, 5),
            "ask": round(ask, 5),
        })

        # Update current price for next candle
        current_price = close

    # Create DataFrame
    df = pd.DataFrame(candles)

    # Save to CSV
    df.to_csv(output_file, index=False)

    logger.info(f"Generated {len(candles)} 4H candles")
    logger.info(f"Date range: {candles[0]['time']} to {candles[-1]['time']}")
    logger.info(f"Saved to: {output_file}")

    return output_file


class SwingBacktester:
    """
    Backtester specifically for swing trading strategy (4H timeframe).
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade: float = 0.01,  # 1% risk per trade
        reward_risk_ratio: float = 2.0,
        max_positions: int = 2,
    ):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.reward_risk_ratio = reward_risk_ratio
        self.max_positions = max_positions

        # Swing trading parameters (from swing_strategy.py)
        self.rsi_period = 14
        self.rsi_oversold = 35  # More relaxed for swing
        self.rsi_overbought = 65
        self.ma_short_period = 20
        self.ma_long_period = 50
        self.atr_period = 14
        self.atr_multiplier = 2.0  # Wider stops for swing

        # Trade tracking
        self.trades = []
        self.active_positions = []
        self.equity_curve = []

        # Performance tracking
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate swing trading indicators with longer periods.
        """
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Moving Averages (longer periods for swing)
        df['ma_short'] = df['close'].rolling(window=self.ma_short_period).mean()
        df['ma_long'] = df['ma_long'] = df['close'].rolling(window=self.ma_long_period).mean()

        # ATR (wider stops for swing trading)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=self.atr_period).mean()

        return df

    def should_enter_long(self, row: pd.Series) -> bool:
        """
        Swing long entry: Uptrend + RSI pullback to oversold (35).
        """
        has_uptrend = row['ma_short'] > row['ma_long']
        is_oversold = row['rsi'] < self.rsi_oversold

        return has_uptrend and is_oversold and not pd.isna(row['atr'])

    def should_enter_short(self, row: pd.Series) -> bool:
        """
        Swing short entry: Downtrend + RSI bounce to overbought (65).
        """
        has_downtrend = row['ma_short'] < row['ma_long']
        is_overbought = row['rsi'] > self.rsi_overbought

        return has_downtrend and is_overbought and not pd.isna(row['atr'])

    def calculate_position_size(self, entry_price: float, stop_distance: float) -> int:
        """
        Calculate position size based on risk per trade.
        For swing trading, we use more conservative position sizing.
        """
        risk_amount = self.current_balance * self.risk_per_trade

        # Units = Risk Amount / Stop Distance
        units = int(risk_amount / stop_distance)

        # Cap at reasonable max (don't over-leverage)
        max_units = int(self.current_balance * 10 / entry_price)  # 10:1 leverage max
        units = min(units, max_units)

        return max(units, 1000)  # Minimum 1000 units

    def run_backtest(self, data_file: str) -> Dict:
        """
        Run backtest on 4H swing trading data.
        """
        logger.info(f"Loading data from {data_file}...")
        df = pd.read_csv(data_file)
        df['time'] = pd.to_datetime(df['time'])

        logger.info(f"Calculating indicators...")
        df = self.calculate_indicators(df)

        logger.info(f"Running swing backtest...")

        # Iterate through candles
        for idx, row in df.iterrows():
            # Skip if indicators not ready
            if pd.isna(row['atr']) or pd.isna(row['ma_long']):
                continue

            # Update equity curve
            self.equity_curve.append({
                'time': row['time'],
                'balance': self.current_balance,
            })

            # Update peak and drawdown
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance

            current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown

            # Check active positions for exit
            for position in self.active_positions[:]:
                # Check stop loss
                if position['direction'] == 'long':
                    if row['low'] <= position['stop_loss']:
                        # Stop loss hit
                        exit_price = position['stop_loss']
                        pnl = (exit_price - position['entry_price']) * position['units']

                        # Apply costs (spread + slippage)
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']  # 0.5 pip slippage
                        total_cost = spread_cost + slippage_cost
                        pnl -= total_cost

                        self.current_balance += pnl

                        self.trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': row['time'],
                            'direction': position['direction'],
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'units': position['units'],
                            'pnl': pnl,
                            'exit_reason': 'stop_loss',
                        })

                        self.active_positions.remove(position)
                        continue

                    # Check take profit
                    if row['high'] >= position['take_profit']:
                        # Take profit hit
                        exit_price = position['take_profit']
                        pnl = (exit_price - position['entry_price']) * position['units']

                        # Apply costs
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']
                        total_cost = spread_cost + slippage_cost
                        pnl -= total_cost

                        self.current_balance += pnl

                        self.trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': row['time'],
                            'direction': position['direction'],
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'units': position['units'],
                            'pnl': pnl,
                            'exit_reason': 'take_profit',
                        })

                        self.active_positions.remove(position)
                        continue

                else:  # short position
                    if row['high'] >= position['stop_loss']:
                        # Stop loss hit
                        exit_price = position['stop_loss']
                        pnl = (position['entry_price'] - exit_price) * position['units']

                        # Apply costs
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']
                        total_cost = spread_cost + slippage_cost
                        pnl -= total_cost

                        self.current_balance += pnl

                        self.trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': row['time'],
                            'direction': position['direction'],
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'units': position['units'],
                            'pnl': pnl,
                            'exit_reason': 'stop_loss',
                        })

                        self.active_positions.remove(position)
                        continue

                    # Check take profit
                    if row['low'] <= position['take_profit']:
                        # Take profit hit
                        exit_price = position['take_profit']
                        pnl = (position['entry_price'] - exit_price) * position['units']

                        # Apply costs
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']
                        total_cost = spread_cost + slippage_cost
                        pnl -= total_cost

                        self.current_balance += pnl

                        self.trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': row['time'],
                            'direction': position['direction'],
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'units': position['units'],
                            'pnl': pnl,
                            'exit_reason': 'take_profit',
                        })

                        self.active_positions.remove(position)

            # Check for new entry signals
            if len(self.active_positions) < self.max_positions:
                # Long entry
                if self.should_enter_long(row):
                    entry_price = row['ask']  # Buy at ask
                    stop_distance = row['atr'] * self.atr_multiplier
                    stop_loss = entry_price - stop_distance
                    take_profit = entry_price + (stop_distance * self.reward_risk_ratio)

                    units = self.calculate_position_size(entry_price, stop_distance)

                    self.active_positions.append({
                        'entry_time': row['time'],
                        'direction': 'long',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'units': units,
                    })

                    logger.info(f"LONG entry at {row['time']}: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")

                # Short entry
                elif self.should_enter_short(row):
                    entry_price = row['bid']  # Sell at bid
                    stop_distance = row['atr'] * self.atr_multiplier
                    stop_loss = entry_price + stop_distance
                    take_profit = entry_price - (stop_distance * self.reward_risk_ratio)

                    units = self.calculate_position_size(entry_price, stop_distance)

                    self.active_positions.append({
                        'entry_time': row['time'],
                        'direction': 'short',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'units': units,
                    })

                    logger.info(f"SHORT entry at {row['time']}: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")

        # Close any remaining positions at final price
        if self.active_positions:
            final_row = df.iloc[-1]
            for position in self.active_positions:
                if position['direction'] == 'long':
                    exit_price = final_row['bid']
                    pnl = (exit_price - position['entry_price']) * position['units']
                else:
                    exit_price = final_row['ask']
                    pnl = (position['entry_price'] - exit_price) * position['units']

                self.current_balance += pnl

                self.trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': final_row['time'],
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'units': position['units'],
                    'pnl': pnl,
                    'exit_reason': 'final_close',
                })

        return self._calculate_results()

    def _calculate_results(self) -> Dict:
        """
        Calculate comprehensive backtest results.
        """
        if not self.trades:
            return {
                "final_balance": self.current_balance,
                "total_return": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "error": "No trades executed",
            }

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0

        total_profit = sum([t['pnl'] for t in winning_trades])
        total_loss = abs(sum([t['pnl'] for t in losing_trades]))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        # Returns
        total_return = ((self.current_balance - self.initial_balance) / self.initial_balance) * 100

        # Sharpe ratio (simplified)
        if len(self.trades) > 1:
            returns = [t['pnl'] / self.initial_balance for t in self.trades]
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0.0

        return {
            "final_balance": self.current_balance,
            "total_return": total_return,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": self.max_drawdown * 100,
            "profit_factor": profit_factor,
            "largest_win": max([t['pnl'] for t in self.trades]),
            "largest_loss": min([t['pnl'] for t in self.trades]),
        }

    def print_results(self, results: Dict):
        """
        Print formatted backtest results.
        """
        print("\n" + "="*60)
        print("SWING TRADING BACKTEST RESULTS (4H Timeframe)")
        print("="*60)

        print(f"\nAccount Performance:")
        print(f"  Initial Balance:    ${self.initial_balance:,.2f}")
        print(f"  Final Balance:      ${results['final_balance']:,.2f}")
        print(f"  Total Return:       {results['total_return']:+.2f}%")
        print(f"  Max Drawdown:       {results['max_drawdown']:.2f}%")

        print(f"\nTrade Statistics:")
        print(f"  Total Trades:       {results['total_trades']}")
        print(f"  Winning Trades:     {results['winning_trades']}")
        print(f"  Losing Trades:      {results['losing_trades']}")
        print(f"  Win Rate:           {results['win_rate']*100:.1f}%")

        print(f"\nPerformance Metrics:")
        print(f"  Average Win:        ${results['avg_win']:.2f}")
        print(f"  Average Loss:       ${results['avg_loss']:.2f}")
        print(f"  Profit Factor:      {results['profit_factor']:.2f}")
        print(f"  Sharpe Ratio:       {results['sharpe_ratio']:.2f}")

        print(f"\nBest/Worst:")
        print(f"  Largest Win:        ${results['largest_win']:.2f}")
        print(f"  Largest Loss:       ${results['largest_loss']:.2f}")

        print("\n" + "="*60)

        # Comparison to scalping
        print("\nCOMPARISON TO SCALPING STRATEGY:")
        print("-" * 60)
        print("Scalping (5m) Results:")
        print("  Total Return:       -4.52%")
        print("  Win Rate:           10.5%")
        print("  Sharpe Ratio:       -0.46")
        print("-" * 60)
        print("Swing (4H) Results:")
        print(f"  Total Return:       {results['total_return']:+.2f}%")
        print(f"  Win Rate:           {results['win_rate']*100:.1f}%")
        print(f"  Sharpe Ratio:       {results['sharpe_ratio']:.2f}")
        print("-" * 60)

        if results['total_return'] > -4.52:
            improvement = results['total_return'] - (-4.52)
            print(f"  Improvement:        +{improvement:.2f}% return")
        else:
            print(f"  Improvement:        Worse by {abs(results['total_return'] + 4.52):.2f}%")

        print("="*60 + "\n")


def main():
    """
    Main function to run swing trading backtest.
    """
    print("\nSwing Trading Strategy Backtest (4H Timeframe)")
    print("="*60)

    # Step 1: Generate sample data
    print("\nStep 1: Generating 12 months of 4H sample data...")
    data_file = generate_4h_sample_data(
        instrument="EUR_USD",
        months=12,
        output_file="swing_backtest_data.csv"
    )

    # Step 2: Run backtest
    print("\nStep 2: Running swing trading backtest...")
    backtester = SwingBacktester(
        initial_balance=10000.0,
        risk_per_trade=0.01,  # 1% risk per trade
        reward_risk_ratio=2.0,  # 2:1 R:R
        max_positions=2,  # Max 2 concurrent positions
    )

    results = backtester.run_backtest(data_file)

    # Step 3: Display results
    print("\nStep 3: Analyzing results...")
    backtester.print_results(results)

    # Step 4: Recommendation
    print("\nRECOMMENDATION:")
    print("-" * 60)

    if results.get('error'):
        print("⚠️  No trades executed. Strategy too conservative or data quality issue.")
        print("    Consider adjusting entry thresholds or using real OANDA data.")
    elif results['total_return'] > 0 and results['sharpe_ratio'] > 1.0:
        print("✅ PROFITABLE STRATEGY - Ready for paper trading!")
        print(f"   Return: {results['total_return']:.2f}%, Sharpe: {results['sharpe_ratio']:.2f}")
        print("\nNext steps:")
        print("1. Run backtest with real OANDA data (not sample)")
        print("2. Paper trade for 30-60 days")
        print("3. Monitor performance vs backtest expectations")
        print("4. Go live if paper trading confirms profitability")
    elif results['total_return'] > 0:
        print("⚠️  MARGINALLY PROFITABLE - Needs improvement")
        print(f"   Return: {results['total_return']:.2f}%, Sharpe: {results['sharpe_ratio']:.2f}")
        print("\nConsider:")
        print("- Adjusting RSI thresholds (try 30/70 vs 35/65)")
        print("- Testing different MA periods")
        print("- Adding AI agents for better entry timing")
        print("- Walk-forward optimization (Phase 4B)")
    else:
        print("❌ NOT PROFITABLE - Strategy needs work")
        print(f"   Return: {results['total_return']:.2f}%, Sharpe: {results['sharpe_ratio']:.2f}")
        print("\nOptions:")
        print("1. Try different parameters (RSI, MA, R:R)")
        print("2. Add filters (volume, volatility)")
        print("3. Enable AI agents for signal quality")
        print("4. Consider different timeframe (Daily)")

    print("-" * 60)


if __name__ == "__main__":
    main()
