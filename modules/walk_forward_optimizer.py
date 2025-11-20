#!/usr/bin/env python3
"""
Walk-Forward Optimization Framework

Validates strategy parameters by testing on out-of-sample data.

Methodology:
1. Split data into training and testing windows
2. Optimize parameters on training window
3. Test optimized parameters on testing window (out-of-sample)
4. Roll forward and repeat
5. Aggregate results to measure parameter stability

This prevents overfitting by ensuring parameters work on unseen data.

Example:
    12 months data, 6-month training, 2-month testing

    Window 1: Train on months 1-6, test on months 7-8
    Window 2: Train on months 3-8, test on months 9-10
    Window 3: Train on months 5-10, test on months 11-12

    Result: 3 out-of-sample test periods
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os

# Import our backtester
from swing_backtest_optimized import OptimizedSwingBacktester

# Setup output directory
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Create timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(OUTPUT_DIR, f"walk_forward_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to: {log_file}")


@dataclass
class ParameterSet:
    """Parameter combination to test"""
    rsi_oversold: int
    rsi_overbought: int
    reward_risk_ratio: float
    atr_multiplier: float
    ma_short_period: int
    ma_long_period: int
    min_volume: int
    min_trend_strength: float

    def to_dict(self):
        return {
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'reward_risk_ratio': self.reward_risk_ratio,
            'atr_multiplier': self.atr_multiplier,
            'ma_short_period': self.ma_short_period,
            'ma_long_period': self.ma_long_period,
            'min_volume': self.min_volume,
            'min_trend_strength': self.min_trend_strength,
        }


@dataclass
class BacktestResult:
    """Results from a single backtest"""
    params: ParameterSet
    total_return: float
    win_rate: float
    sharpe_ratio: float
    profit_factor: float
    max_drawdown: float
    total_trades: int

    def fitness_score(self) -> float:
        """
        Calculate fitness score for optimization.
        Weighted combination of key metrics.
        """
        # Weights
        return_weight = 0.3
        sharpe_weight = 0.3
        win_rate_weight = 0.2
        profit_factor_weight = 0.2

        # Normalize metrics (0-100 scale)
        return_score = min(max(self.total_return, -50), 50) + 50  # -50% to +50% -> 0 to 100
        sharpe_score = min(max(self.sharpe_ratio, -2), 3) * 20  # -2 to 3 -> 0 to 100
        win_rate_score = self.win_rate * 100
        pf_score = min(self.profit_factor, 3) * 33.33  # 0 to 3 -> 0 to 100

        fitness = (
            return_score * return_weight +
            sharpe_score * sharpe_weight +
            win_rate_score * win_rate_weight +
            pf_score * profit_factor_weight
        )

        return fitness


@dataclass
class WalkForwardWindow:
    """Single walk-forward window"""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    best_params: Optional[ParameterSet] = None
    train_result: Optional[BacktestResult] = None
    test_result: Optional[BacktestResult] = None


class WalkForwardOptimizer:
    """
    Walk-forward optimization framework.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        train_months: int = 6,
        test_months: int = 2,
        step_months: int = 2,
        initial_balance: float = 10000.0,
    ):
        self.data = data
        self.data['time'] = pd.to_datetime(self.data['time'])
        self.train_months = train_months
        self.test_months = test_months
        self.step_months = step_months
        self.initial_balance = initial_balance

        self.windows = []
        self.results = []

    def create_windows(self) -> List[WalkForwardWindow]:
        """
        Create walk-forward windows.
        """
        logger.info(f"Creating walk-forward windows...")
        logger.info(f"Train: {self.train_months} months, Test: {self.test_months} months, Step: {self.step_months} months")

        data_start = self.data['time'].min()
        data_end = self.data['time'].max()

        logger.info(f"Data range: {data_start} to {data_end}")

        windows = []
        window_id = 1

        current_start = data_start

        while True:
            # Calculate window boundaries
            train_start = current_start
            train_end = train_start + pd.DateOffset(months=self.train_months)
            test_start = train_end
            test_end = test_start + pd.DateOffset(months=self.test_months)

            # Check if we have enough data
            if test_end > data_end:
                break

            window = WalkForwardWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )

            windows.append(window)

            logger.info(f"Window {window_id}: Train {train_start.date()} to {train_end.date()}, "
                       f"Test {test_start.date()} to {test_end.date()}")

            # Step forward
            current_start = current_start + pd.DateOffset(months=self.step_months)
            window_id += 1

        logger.info(f"Created {len(windows)} walk-forward windows")
        self.windows = windows
        return windows

    def generate_parameter_grid(self, mode: str = 'focused') -> List[ParameterSet]:
        """
        Generate parameter combinations to test.

        Modes:
        - 'focused': Test around current optimal parameters (faster)
        - 'broad': Wide search across parameter space (slower)
        """
        if mode == 'focused':
            # Test variations around our optimized parameters
            param_grid = {
                'rsi_oversold': [25, 30, 35],  # Current: 30
                'rsi_overbought': [65, 70, 75],  # Current: 70
                'reward_risk_ratio': [1.0, 1.5, 2.0],  # Current: 1.5
                'atr_multiplier': [1.0, 1.5, 2.0],  # Current: 1.5
                'ma_short_period': [15, 20, 25],  # Current: 20
                'ma_long_period': [45, 50, 55],  # Current: 50
                'min_volume': [300, 400, 500],  # Current: 400
                'min_trend_strength': [0.0003, 0.0005, 0.0007],  # Current: 0.0005
            }
        else:  # broad
            param_grid = {
                'rsi_oversold': [20, 25, 30, 35, 40],
                'rsi_overbought': [60, 65, 70, 75, 80],
                'reward_risk_ratio': [1.0, 1.5, 2.0, 2.5],
                'atr_multiplier': [1.0, 1.5, 2.0, 2.5],
                'ma_short_period': [10, 15, 20, 25, 30],
                'ma_long_period': [40, 50, 60, 70],
                'min_volume': [200, 300, 400, 500],
                'min_trend_strength': [0.0001, 0.0003, 0.0005, 0.0007, 0.001],
            }

        # Generate all combinations
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

        # Filter invalid combinations
        valid_params = []
        for combo in combinations:
            # RSI oversold must be < overbought
            if combo['rsi_oversold'] >= combo['rsi_overbought']:
                continue

            # Short MA must be < long MA
            if combo['ma_short_period'] >= combo['ma_long_period']:
                continue

            valid_params.append(ParameterSet(**combo))

        logger.info(f"Generated {len(valid_params)} parameter combinations ({mode} mode)")
        return valid_params

    def backtest_params(self, params: ParameterSet, data: pd.DataFrame) -> BacktestResult:
        """
        Run backtest with specific parameters.
        """
        # Create backtester with custom parameters
        backtester = OptimizedSwingBacktester(
            initial_balance=self.initial_balance,
            risk_per_trade=0.01,
            reward_risk_ratio=params.reward_risk_ratio,
            max_positions=2,
        )

        # Override parameters
        backtester.rsi_oversold = params.rsi_oversold
        backtester.rsi_overbought = params.rsi_overbought
        backtester.atr_multiplier = params.atr_multiplier
        backtester.ma_short_period = params.ma_short_period
        backtester.ma_long_period = params.ma_long_period
        backtester.min_volume = params.min_volume
        backtester.min_trend_strength = params.min_trend_strength

        # Save data temporarily in outputs directory
        temp_file = os.path.join(OUTPUT_DIR, f"temp_data_{datetime.now().timestamp()}.csv")
        data.to_csv(temp_file, index=False)

        # Run backtest
        try:
            results = backtester.run_backtest(temp_file)

            # Clean up
            os.remove(temp_file)

            return BacktestResult(
                params=params,
                total_return=results.get('total_return', 0.0),
                win_rate=results.get('win_rate', 0.0),
                sharpe_ratio=results.get('sharpe_ratio', 0.0),
                profit_factor=results.get('profit_factor', 0.0),
                max_drawdown=results.get('max_drawdown', 0.0),
                total_trades=results.get('total_trades', 0),
            )
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)

            return BacktestResult(
                params=params,
                total_return=-100.0,
                win_rate=0.0,
                sharpe_ratio=-10.0,
                profit_factor=0.0,
                max_drawdown=100.0,
                total_trades=0,
            )

    def optimize_window(self, window: WalkForwardWindow, param_grid: List[ParameterSet]) -> WalkForwardWindow:
        """
        Optimize parameters for a single window.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"OPTIMIZING WINDOW {window.window_id}")
        logger.info(f"{'='*60}")

        # Get training data
        train_data = self.data[
            (self.data['time'] >= window.train_start) &
            (self.data['time'] < window.train_end)
        ].copy()

        logger.info(f"Training on {len(train_data)} candles ({window.train_start.date()} to {window.train_end.date()})")
        logger.info(f"Testing {len(param_grid)} parameter combinations...")

        # Test all parameter combinations
        best_result = None
        best_fitness = -float('inf')

        for i, params in enumerate(param_grid):
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(param_grid)} combinations tested...")

            result = self.backtest_params(params, train_data)
            fitness = result.fitness_score()

            if fitness > best_fitness:
                best_fitness = fitness
                best_result = result

        logger.info(f"\n✅ Best parameters found (fitness: {best_fitness:.2f}):")
        logger.info(f"   RSI: {best_result.params.rsi_oversold}/{best_result.params.rsi_overbought}")
        logger.info(f"   R:R: {best_result.params.reward_risk_ratio}")
        logger.info(f"   ATR: {best_result.params.atr_multiplier}x")
        logger.info(f"   Training Performance:")
        logger.info(f"     Return: {best_result.total_return:.2f}%")
        logger.info(f"     Win Rate: {best_result.win_rate*100:.1f}%")
        logger.info(f"     Sharpe: {best_result.sharpe_ratio:.2f}")

        # Test on out-of-sample data
        logger.info(f"\n📊 Testing on out-of-sample data...")
        test_data = self.data[
            (self.data['time'] >= window.test_start) &
            (self.data['time'] < window.test_end)
        ].copy()

        logger.info(f"Testing on {len(test_data)} candles ({window.test_start.date()} to {window.test_end.date()})")

        test_result = self.backtest_params(best_result.params, test_data)

        logger.info(f"\n📈 Out-of-Sample Performance:")
        logger.info(f"   Return: {test_result.total_return:.2f}%")
        logger.info(f"   Win Rate: {test_result.win_rate*100:.1f}%")
        logger.info(f"   Sharpe: {test_result.sharpe_ratio:.2f}")
        logger.info(f"   Trades: {test_result.total_trades}")

        # Update window
        window.best_params = best_result.params
        window.train_result = best_result
        window.test_result = test_result

        return window

    def run_optimization(self, mode: str = 'focused') -> List[WalkForwardWindow]:
        """
        Run complete walk-forward optimization.
        """
        logger.info("\n" + "="*60)
        logger.info("WALK-FORWARD OPTIMIZATION")
        logger.info("="*60)

        # Create windows
        windows = self.create_windows()

        if not windows:
            logger.error("No windows created! Check data range.")
            return []

        # Generate parameter grid
        param_grid = self.generate_parameter_grid(mode=mode)

        # Optimize each window
        optimized_windows = []

        for window in windows:
            optimized = self.optimize_window(window, param_grid)
            optimized_windows.append(optimized)

        self.results = optimized_windows
        return optimized_windows

    def analyze_results(self):
        """
        Analyze walk-forward results for parameter stability.
        """
        if not self.results:
            logger.error("No results to analyze. Run optimization first.")
            return

        logger.info("\n" + "="*60)
        logger.info("WALK-FORWARD ANALYSIS")
        logger.info("="*60)

        # Aggregate out-of-sample results
        oos_returns = [w.test_result.total_return for w in self.results]
        oos_win_rates = [w.test_result.win_rate for w in self.results]
        oos_sharpes = [w.test_result.sharpe_ratio for w in self.results]
        oos_trades = [w.test_result.total_trades for w in self.results]

        logger.info(f"\nOut-of-Sample Performance Summary:")
        logger.info(f"{'='*60}")
        logger.info(f"Windows Tested: {len(self.results)}")
        logger.info(f"\nReturns:")
        logger.info(f"  Mean:   {np.mean(oos_returns):.2f}%")
        logger.info(f"  Median: {np.median(oos_returns):.2f}%")
        logger.info(f"  Std:    {np.std(oos_returns):.2f}%")
        logger.info(f"  Min:    {np.min(oos_returns):.2f}%")
        logger.info(f"  Max:    {np.max(oos_returns):.2f}%")

        logger.info(f"\nWin Rate:")
        logger.info(f"  Mean:   {np.mean(oos_win_rates)*100:.1f}%")
        logger.info(f"  Median: {np.median(oos_win_rates)*100:.1f}%")
        logger.info(f"  Std:    {np.std(oos_win_rates)*100:.1f}%")

        logger.info(f"\nSharpe Ratio:")
        logger.info(f"  Mean:   {np.mean(oos_sharpes):.2f}")
        logger.info(f"  Median: {np.median(oos_sharpes):.2f}")
        logger.info(f"  Std:    {np.std(oos_sharpes):.2f}")

        logger.info(f"\nTotal Trades (per window):")
        logger.info(f"  Mean:   {np.mean(oos_trades):.1f}")
        logger.info(f"  Total:  {np.sum(oos_trades)}")

        # Parameter stability
        logger.info(f"\n{'='*60}")
        logger.info("PARAMETER STABILITY ANALYSIS")
        logger.info(f"{'='*60}")

        rsi_oversold = [w.best_params.rsi_oversold for w in self.results]
        rsi_overbought = [w.best_params.rsi_overbought for w in self.results]
        rr_ratios = [w.best_params.reward_risk_ratio for w in self.results]
        atr_mults = [w.best_params.atr_multiplier for w in self.results]

        logger.info(f"\nRSI Oversold: {np.mean(rsi_oversold):.0f} ± {np.std(rsi_oversold):.1f}")
        logger.info(f"RSI Overbought: {np.mean(rsi_overbought):.0f} ± {np.std(rsi_overbought):.1f}")
        logger.info(f"R:R Ratio: {np.mean(rr_ratios):.2f} ± {np.std(rr_ratios):.2f}")
        logger.info(f"ATR Multiplier: {np.mean(atr_mults):.2f} ± {np.std(atr_mults):.2f}")

        # Consistency check
        positive_windows = sum(1 for r in oos_returns if r > 0)
        consistency = (positive_windows / len(oos_returns)) * 100

        logger.info(f"\n{'='*60}")
        logger.info("ROBUSTNESS METRICS")
        logger.info(f"{'='*60}")
        logger.info(f"Positive Windows: {positive_windows}/{len(self.results)} ({consistency:.1f}%)")

        if consistency > 60:
            logger.info("✅ ROBUST: Parameters work consistently across time periods")
        elif consistency > 40:
            logger.info("⚠️  MODERATE: Parameters show some inconsistency")
        else:
            logger.info("❌ UNSTABLE: Parameters likely overfit or strategy fundamentally flawed")

        # Save results
        self.save_results()

    def save_results(self):
        """Save results to JSON file with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUT_DIR, f"walk_forward_results_{timestamp}.json")

        results_data = []

        for window in self.results:
            results_data.append({
                'window_id': window.window_id,
                'train_period': f"{window.train_start.date()} to {window.train_end.date()}",
                'test_period': f"{window.test_start.date()} to {window.test_end.date()}",
                'best_params': window.best_params.to_dict(),
                'train_performance': {
                    'return': window.train_result.total_return,
                    'win_rate': window.train_result.win_rate,
                    'sharpe': window.train_result.sharpe_ratio,
                    'trades': window.train_result.total_trades,
                },
                'test_performance': {
                    'return': window.test_result.total_return,
                    'win_rate': window.test_result.win_rate,
                    'sharpe': window.test_result.sharpe_ratio,
                    'trades': window.test_result.total_trades,
                }
            })

        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)

        logger.info(f"\n💾 Results saved to: {filename}")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Walk-Forward Optimization")
    parser.add_argument('--data', default='swing_backtest_data.csv', help='Data file')
    parser.add_argument('--train-months', type=int, default=6, help='Training window months')
    parser.add_argument('--test-months', type=int, default=2, help='Testing window months')
    parser.add_argument('--step-months', type=int, default=2, help='Step size months')
    parser.add_argument('--mode', choices=['focused', 'broad'], default='focused',
                       help='Parameter search mode')

    args = parser.parse_args()

    # Load data
    logger.info(f"Loading data from {args.data}...")
    data = pd.read_csv(args.data)

    # Create optimizer
    optimizer = WalkForwardOptimizer(
        data=data,
        train_months=args.train_months,
        test_months=args.test_months,
        step_months=args.step_months,
    )

    # Run optimization
    results = optimizer.run_optimization(mode=args.mode)

    # Analyze results
    optimizer.analyze_results()

    logger.info("\n✅ Walk-forward optimization complete!")


if __name__ == "__main__":
    main()
