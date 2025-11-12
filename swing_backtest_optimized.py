#!/usr/bin/env python3
"""
Optimized Swing Trading Strategy Backtest
Tests adjusted parameters to improve win rate and profitability.

Key changes from swing_backtest.py:
- Tighter RSI thresholds: 30/70 (was 35/65)
- Lower R:R ratio: 1.5 (was 2.0)
- Tighter stops: 1.5x ATR (was 2.0x)
- Added volume filter
- Added trend strength filter
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OptimizedSwingBacktester:
    """
    Optimized swing trading backtester with improved parameters.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade: float = 0.01,
        reward_risk_ratio: float = 1.5,  # Lower R:R (was 2.0)
        max_positions: int = 2,
    ):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.reward_risk_ratio = reward_risk_ratio
        self.max_positions = max_positions

        # OPTIMIZED swing trading parameters
        self.rsi_period = 14
        self.rsi_oversold = 30  # Tighter (was 35)
        self.rsi_overbought = 70  # Tighter (was 65)
        self.ma_short_period = 20
        self.ma_long_period = 50
        self.atr_period = 14
        self.atr_multiplier = 1.5  # Tighter stops (was 2.0)

        # NEW: Filters
        self.min_volume = 400  # Minimum 4H candle volume
        self.min_trend_strength = 0.0005  # MA separation (5 pips minimum)

        # Trade tracking
        self.trades = []
        self.active_positions = []
        self.equity_curve = []
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate swing trading indicators."""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Moving Averages
        df['ma_short'] = df['close'].rolling(window=self.ma_short_period).mean()
        df['ma_long'] = df['close'].rolling(window=self.ma_long_period).mean()

        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=self.atr_period).mean()

        # Trend strength (MA separation)
        df['trend_strength'] = abs(df['ma_short'] - df['ma_long'])

        return df

    def should_enter_long(self, row: pd.Series) -> bool:
        """
        OPTIMIZED long entry:
        - Uptrend + RSI < 30 (more extreme)
        - Volume filter
        - Trend strength filter
        """
        has_uptrend = row['ma_short'] > row['ma_long']
        is_oversold = row['rsi'] < self.rsi_oversold
        has_volume = row['volume'] >= self.min_volume
        has_trend = row['trend_strength'] >= self.min_trend_strength

        return (
            has_uptrend
            and is_oversold
            and has_volume
            and has_trend
            and not pd.isna(row['atr'])
        )

    def should_enter_short(self, row: pd.Series) -> bool:
        """
        OPTIMIZED short entry:
        - Downtrend + RSI > 70 (more extreme)
        - Volume filter
        - Trend strength filter
        """
        has_downtrend = row['ma_short'] < row['ma_long']
        is_overbought = row['rsi'] > self.rsi_overbought
        has_volume = row['volume'] >= self.min_volume
        has_trend = row['trend_strength'] >= self.min_trend_strength

        return (
            has_downtrend
            and is_overbought
            and has_volume
            and has_trend
            and not pd.isna(row['atr'])
        )

    def calculate_position_size(self, entry_price: float, stop_distance: float) -> int:
        """Calculate position size based on risk per trade."""
        risk_amount = self.current_balance * self.risk_per_trade
        units = int(risk_amount / stop_distance)
        max_units = int(self.current_balance * 10 / entry_price)  # 10:1 leverage max
        units = min(units, max_units)
        return max(units, 1000)

    def run_backtest(self, data_file: str) -> Dict:
        """Run backtest on 4H swing trading data."""
        logger.info(f"Loading data from {data_file}...")
        df = pd.read_csv(data_file)
        df['time'] = pd.to_datetime(df['time'])

        logger.info(f"Calculating indicators...")
        df = self.calculate_indicators(df)

        logger.info(f"Running OPTIMIZED swing backtest...")

        for idx, row in df.iterrows():
            if pd.isna(row['atr']) or pd.isna(row['ma_long']):
                continue

            self.equity_curve.append({'time': row['time'], 'balance': self.current_balance})

            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance

            current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown

            # Check active positions for exit
            for position in self.active_positions[:]:
                if position['direction'] == 'long':
                    if row['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        pnl = (exit_price - position['entry_price']) * position['units']
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']
                        pnl -= (spread_cost + slippage_cost)
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

                    if row['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        pnl = (exit_price - position['entry_price']) * position['units']
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']
                        pnl -= (spread_cost + slippage_cost)
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

                else:  # short
                    if row['high'] >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        pnl = (position['entry_price'] - exit_price) * position['units']
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']
                        pnl -= (spread_cost + slippage_cost)
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

                    if row['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        pnl = (position['entry_price'] - exit_price) * position['units']
                        spread_cost = (row['ask'] - row['bid']) * position['units']
                        slippage_cost = 0.00005 * position['units']
                        pnl -= (spread_cost + slippage_cost)
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

            # Check for new entries
            if len(self.active_positions) < self.max_positions:
                if self.should_enter_long(row):
                    entry_price = row['ask']
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
                    logger.info(f"LONG at {row['time']}: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")

                elif self.should_enter_short(row):
                    entry_price = row['bid']
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
                    logger.info(f"SHORT at {row['time']}: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")

        # Close remaining positions
        if self.active_positions:
            final_row = df.iloc[-1]
            for position in self.active_positions:
                exit_price = final_row['bid'] if position['direction'] == 'long' else final_row['ask']
                pnl = ((exit_price - position['entry_price']) if position['direction'] == 'long'
                       else (position['entry_price'] - exit_price)) * position['units']
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
        """Calculate comprehensive results."""
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

        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0

        total_profit = sum([t['pnl'] for t in winning_trades])
        total_loss = abs(sum([t['pnl'] for t in losing_trades]))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        total_return = ((self.current_balance - self.initial_balance) / self.initial_balance) * 100

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
        """Print formatted results."""
        print("\n" + "="*60)
        print("OPTIMIZED SWING TRADING BACKTEST RESULTS")
        print("="*60)

        print(f"\nParameters:")
        print(f"  RSI Thresholds:     {self.rsi_oversold}/{self.rsi_overbought} (was 35/65)")
        print(f"  R:R Ratio:          {self.reward_risk_ratio}:1 (was 2.0:1)")
        print(f"  ATR Multiplier:     {self.atr_multiplier}x (was 2.0x)")
        print(f"  Min Volume:         {self.min_volume}")
        print(f"  Min Trend Strength: {self.min_trend_strength}")

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

        print("\n" + "="*60)
        print("COMPARISON TO ORIGINAL SWING BACKTEST:")
        print("-" * 60)
        print("Original (RSI 35/65, R:R 2.0, ATR 2.0x):")
        print("  Total Return:       -15.36%")
        print("  Win Rate:           14.3%")
        print("  Sharpe Ratio:       -9.16")
        print("-" * 60)
        print("Optimized (RSI 30/70, R:R 1.5, ATR 1.5x + filters):")
        print(f"  Total Return:       {results['total_return']:+.2f}%")
        print(f"  Win Rate:           {results['win_rate']*100:.1f}%")
        print(f"  Sharpe Ratio:       {results['sharpe_ratio']:.2f}")
        print("-" * 60)

        if results['total_return'] > -15.36:
            improvement = results['total_return'] - (-15.36)
            print(f"  Improvement:        +{improvement:.2f}% return")
        print("="*60 + "\n")


def main():
    """Run optimized swing backtest."""
    print("\nOptimized Swing Trading Backtest")
    print("="*60)

    # Use existing swing data
    data_file = "swing_backtest_data.csv"

    backtester = OptimizedSwingBacktester(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        reward_risk_ratio=1.5,  # Lower R:R
        max_positions=2,
    )

    results = backtester.run_backtest(data_file)
    backtester.print_results(results)

    print("\nRECOMMENDATION:")
    print("-" * 60)

    if results.get('error'):
        print("⚠️  No trades executed with optimized parameters.")
        print("    Strategy is too conservative. Consider:")
        print("    - Relaxing filters (volume, trend strength)")
        print("    - Using real OANDA data instead of sample")
    elif results['total_return'] > 0 and results['sharpe_ratio'] > 0.5:
        print("✅ OPTIMIZED PARAMETERS SHOW PROMISE!")
        print(f"   Return: {results['total_return']:.2f}%, Sharpe: {results['sharpe_ratio']:.2f}")
        print("\nNext steps:")
        print("1. Test with real OANDA historical data")
        print("2. Paper trade with these parameters + AI agents")
        print("3. Monitor for 30-60 days")
    elif results['total_return'] > -5.0:
        print("⚠️  MARGINALLY IMPROVED")
        print(f"   Return: {results['total_return']:.2f}%")
        print("\nStill need AI agents and real market conditions to be profitable.")
        print("Recommend: Paper trade with Phase 3 features enabled.")
    else:
        print("❌ STILL NOT PROFITABLE")
        print(f"   Return: {results['total_return']:.2f}%")
        print("\nSample data backtests are not reliable.")
        print("Recommend: Skip to paper trading with AI agents.")

    print("-" * 60)


if __name__ == "__main__":
    main()
