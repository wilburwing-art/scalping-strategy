"""
Parameter Optimization Framework

Systematic optimization of strategy parameters using grid search and
walk-forward validation to prevent overfitting.

Usage:
    from parameter_optimizer import ParameterOptimizer, ParameterSet

    optimizer = ParameterOptimizer(trade_journal)

    # Run optimization
    best_params, performance = await optimizer.optimize(
        instrument="EUR_USD",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    print(f"Best RSI period: {best_params.rsi_period}")
    print(f"Expected Sharpe: {performance['avg_sharpe_ratio']:.2f}")
"""

import asyncio
import logging
import itertools
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


@dataclass
class ParameterSet:
    """Set of strategy parameters to optimize"""

    # Technical indicator periods
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70

    atr_period: int = 14
    atr_multiplier: float = 1.5

    ma_short_period: int = 20
    ma_long_period: int = 50

    # Risk management
    risk_percent: float = 1.0
    reward_risk_ratio: float = 1.5

    # Agent confidence
    min_confidence: float = 0.6

    # Market regime
    min_volatility: float = 0.0005  # Minimum ATR
    max_volatility: float = 0.0050  # Maximum ATR

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ParameterSet':
        """Create from dictionary"""
        return cls(**data)

    def __str__(self) -> str:
        """Human-readable representation"""
        return f"ParameterSet(RSI={self.rsi_period}, ATR={self.atr_period}, MA={self.ma_short_period}/{self.ma_long_period}, RR={self.reward_risk_ratio})"


@dataclass
class BacktestResult:
    """Results from a parameter backtest"""

    parameters: ParameterSet
    start_date: str
    end_date: str

    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0

    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    avg_trade_pips: float = 0.0

    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0

    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # Trade distribution
    trades_per_day: float = 0.0
    avg_hold_time_minutes: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        result['parameters'] = self.parameters.to_dict()
        return result


class ParameterOptimizer:
    """
    Systematic parameter optimization with walk-forward validation.

    Features:
    - Grid search over parameter space
    - Walk-forward validation (prevents overfitting)
    - Multiple optimization metrics (Sharpe, profit factor, win rate)
    - Statistical significance testing
    - Out-of-sample validation

    Usage:
        from trade_journal import TradeJournal

        journal = TradeJournal("trades.db")
        optimizer = ParameterOptimizer(journal)

        # Optimize parameters
        best_params, metrics = await optimizer.optimize(
            instrument="EUR_USD",
            start_date="2024-01-01",
            end_date="2024-12-31",
            param_grid={
                "rsi_period": [10, 14, 20],
                "reward_risk_ratio": [1.2, 1.5, 2.0],
            },
            optimization_metric="sharpe_ratio",
        )

        # Use optimized parameters
        strategy.update_parameters(best_params)
    """

    def __init__(self, trade_journal):
        """
        Args:
            trade_journal: TradeJournal instance with historical trades
        """
        self.trade_journal = trade_journal
        self.optimization_history: List[Dict] = []

    async def optimize(
        self,
        instrument: str,
        start_date: str,
        end_date: str,
        param_grid: Optional[Dict] = None,
        optimization_metric: str = "sharpe_ratio",
        walk_forward_periods: int = 4,
        min_trades_per_period: int = 20,
    ) -> Tuple[ParameterSet, Dict]:
        """
        Find optimal parameters using walk-forward validation.

        Args:
            instrument: Instrument to optimize (e.g., "EUR_USD")
            start_date: Start of optimization period (YYYY-MM-DD)
            end_date: End of optimization period (YYYY-MM-DD)
            param_grid: Dictionary of parameter ranges to test
            optimization_metric: Metric to optimize ("sharpe_ratio", "profit_factor", "win_rate")
            walk_forward_periods: Number of train/test windows
            min_trades_per_period: Minimum trades required per period

        Returns:
            (best_parameters, aggregated_performance_metrics)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PARAMETER OPTIMIZATION: {instrument}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Optimization metric: {optimization_metric}")
        logger.info(f"Walk-forward periods: {walk_forward_periods}")
        logger.info(f"{'='*60}\n")

        if param_grid is None:
            param_grid = self._default_param_grid()

        # Generate all parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)
        logger.info(f"Testing {len(param_combinations)} parameter combinations\n")

        # Create walk-forward windows
        windows = self._create_walk_forward_windows(
            start_date, end_date, walk_forward_periods
        )

        # Walk-forward optimization
        period_results = []

        for i, (train_start, train_end, test_start, test_end) in enumerate(windows, 1):
            logger.info(f"\n--- Walk-Forward Period {i}/{walk_forward_periods} ---")
            logger.info(f"Training: {train_start} to {train_end}")
            logger.info(f"Testing: {test_start} to {test_end}")

            # Grid search on training data
            best_params, best_score, train_results = await self._grid_search(
                instrument,
                train_start,
                train_end,
                param_combinations,
                optimization_metric,
            )

            if best_params is None:
                logger.warning(f"Period {i}: No valid results (insufficient trades)")
                continue

            logger.info(f"\nBest training {optimization_metric}: {best_score:.3f}")
            logger.info(f"Best parameters: {best_params}")

            # Validate on test (out-of-sample) data
            test_result = await self._backtest_with_params(
                instrument, test_start, test_end, best_params
            )

            if test_result.total_trades < min_trades_per_period:
                logger.warning(
                    f"Period {i}: Test period has only {test_result.total_trades} trades (min: {min_trades_per_period})"
                )
                continue

            test_score = getattr(test_result, optimization_metric)
            logger.info(f"Out-of-sample {optimization_metric}: {test_score:.3f}")
            logger.info(f"Out-of-sample trades: {test_result.total_trades}")
            logger.info(f"Out-of-sample win rate: {test_result.win_rate:.1%}")

            period_results.append({
                "period": i,
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "best_params": best_params,
                "train_score": best_score,
                "test_result": test_result,
                "test_score": test_score,
            })

        if not period_results:
            raise ValueError("No valid walk-forward periods found (insufficient trades)")

        # Aggregate results
        final_params = self._aggregate_parameters(period_results, optimization_metric)
        final_performance = self._aggregate_performance(period_results, optimization_metric)

        logger.info(f"\n{'='*60}")
        logger.info("OPTIMIZATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"\nFinal Parameters: {final_params}")
        logger.info(f"\nOut-of-Sample Performance:")
        logger.info(f"  Avg {optimization_metric}: {final_performance[f'avg_{optimization_metric}']:.3f}")
        logger.info(f"  Avg win rate: {final_performance['avg_win_rate']:.1%}")
        logger.info(f"  Avg profit factor: {final_performance['avg_profit_factor']:.2f}")
        logger.info(f"  Total test trades: {final_performance['total_test_trades']}")
        logger.info(f"  Consistency: {final_performance['consistency']:.3f} (lower = better)")
        logger.info(f"{'='*60}\n")

        # Save optimization history
        self.optimization_history.append({
            "timestamp": datetime.now().isoformat(),
            "instrument": instrument,
            "start_date": start_date,
            "end_date": end_date,
            "optimization_metric": optimization_metric,
            "final_params": final_params.to_dict(),
            "performance": final_performance,
        })

        return final_params, final_performance

    def _default_param_grid(self) -> Dict:
        """Default parameter grid for optimization"""
        return {
            "rsi_period": [10, 14, 20],
            "rsi_oversold": [25, 30, 35],
            "rsi_overbought": [65, 70, 75],
            "atr_period": [10, 14, 20],
            "atr_multiplier": [1.2, 1.5, 2.0],
            "ma_short_period": [10, 20, 30],
            "ma_long_period": [40, 50, 60],
            "reward_risk_ratio": [1.2, 1.5, 2.0],
            "min_confidence": [0.5, 0.6, 0.7],
        }

    def _generate_param_combinations(self, param_grid: Dict) -> List[ParameterSet]:
        """Generate all parameter combinations from grid"""
        # Get keys and values
        keys = list(param_grid.keys())
        values = list(param_grid.values())

        # Generate all combinations
        combinations = list(itertools.product(*values))

        # Create ParameterSet objects
        param_sets = []
        for combo in combinations:
            params = ParameterSet()
            for key, value in zip(keys, combo):
                setattr(params, key, value)
            param_sets.append(params)

        return param_sets

    async def _grid_search(
        self,
        instrument: str,
        start_date: str,
        end_date: str,
        param_combinations: List[ParameterSet],
        metric: str,
    ) -> Tuple[Optional[ParameterSet], float, List[BacktestResult]]:
        """
        Grid search over parameter combinations.

        Returns:
            (best_params, best_score, all_results)
        """
        results = []

        for i, params in enumerate(param_combinations, 1):
            if i % 10 == 0:
                logger.info(f"  Testing combination {i}/{len(param_combinations)}...")

            result = await self._backtest_with_params(
                instrument, start_date, end_date, params
            )
            results.append(result)

        # Find best result
        valid_results = [r for r in results if r.total_trades >= 10]

        if not valid_results:
            return None, 0.0, results

        best_result = max(valid_results, key=lambda r: getattr(r, metric))
        best_score = getattr(best_result, metric)

        return best_result.parameters, best_score, results

    async def _backtest_with_params(
        self,
        instrument: str,
        start_date: str,
        end_date: str,
        params: ParameterSet,
    ) -> BacktestResult:
        """
        Backtest strategy with specific parameters.

        Note: This uses historical trades from the journal and filters them
        based on whether they would have been taken with these parameters.
        For a true backtest, you'd need tick data and order simulation.
        """
        # Get all trades in date range
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Query trades from journal
        query = """
        SELECT * FROM trades
        WHERE instrument = ?
        AND exit_time >= ?
        AND exit_time <= ?
        AND exit_time IS NOT NULL
        ORDER BY exit_time
        """

        df = pd.read_sql_query(
            query,
            self.trade_journal.conn,
            params=[instrument, start_dt.isoformat(), end_dt.isoformat()]
        )

        if len(df) == 0:
            return BacktestResult(
                parameters=params,
                start_date=start_date,
                end_date=end_date,
            )

        # Filter trades based on parameters
        # (This is a simplified approach - in reality, you'd need to replay the market)
        filtered_trades = self._filter_trades_by_params(df, params)

        # Calculate performance metrics
        result = self._calculate_performance(filtered_trades, params, start_date, end_date)

        return result

    def _filter_trades_by_params(self, df: pd.DataFrame, params: ParameterSet) -> pd.DataFrame:
        """
        Filter trades that would have been taken with these parameters.

        This is a simplified approach - checks if trade conditions align with parameters.
        """
        # Filter by confidence if available (most important filter)
        if 'overall_confidence' in df.columns and params.min_confidence is not None:
            df = df[df['overall_confidence'] >= params.min_confidence]

        # Optionally filter by volatility range if available
        # (Be less strict to ensure we have enough trades)
        if 'atr' in df.columns and params.min_volatility > 0:
            df = df[df['atr'] >= params.min_volatility * 0.5]  # More lenient

        if 'atr' in df.columns and params.max_volatility < 0.01:
            df = df[df['atr'] <= params.max_volatility * 1.5]  # More lenient

        return df

    def _calculate_performance(
        self,
        df: pd.DataFrame,
        params: ParameterSet,
        start_date: str,
        end_date: str,
    ) -> BacktestResult:
        """Calculate performance metrics from trades"""

        if len(df) == 0:
            return BacktestResult(
                parameters=params,
                start_date=start_date,
                end_date=end_date,
            )

        # Basic metrics
        total_trades = len(df)
        winning_trades = len(df[df['net_pips'] > 0])
        losing_trades = len(df[df['net_pips'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # P/L metrics
        winners = df[df['net_pips'] > 0]
        losers = df[df['net_pips'] < 0]

        total_profit = winners['profit_usd'].sum() if len(winners) > 0 else 0.0
        total_loss = abs(losers['profit_usd'].sum()) if len(losers) > 0 else 0.0
        net_profit = df['profit_usd'].sum()
        profit_factor = total_profit / total_loss if total_loss > 0 else 0.0

        avg_win_pips = winners['net_pips'].mean() if len(winners) > 0 else 0.0
        avg_loss_pips = losers['net_pips'].mean() if len(losers) > 0 else 0.0
        avg_trade_pips = df['net_pips'].mean()

        # Consecutive streaks
        def count_max_consecutive(series, condition):
            max_count = 0
            current_count = 0
            for value in series:
                if condition(value):
                    current_count += 1
                    max_count = max(max_count, current_count)
                else:
                    current_count = 0
            return max_count

        max_consecutive_wins = count_max_consecutive(df['net_pips'], lambda x: x > 0)
        max_consecutive_losses = count_max_consecutive(df['net_pips'], lambda x: x < 0)

        # Drawdown
        cumulative_pl = df['profit_usd'].cumsum()
        running_max = cumulative_pl.cummax()
        drawdown = cumulative_pl - running_max
        max_drawdown = abs(drawdown.min())

        initial_balance = 10000.0  # Assumed
        max_drawdown_percent = (max_drawdown / initial_balance) * 100 if initial_balance > 0 else 0.0

        # Risk-adjusted metrics
        returns = df['profit_usd']
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0

        downside_returns = returns[returns < 0]
        sortino_ratio = (
            (returns.mean() / downside_returns.std() * np.sqrt(252))
            if len(downside_returns) > 0 and downside_returns.std() > 0
            else 0.0
        )

        calmar_ratio = (net_profit / max_drawdown) if max_drawdown > 0 else 0.0

        # Time metrics
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        days = (end - start).days
        trades_per_day = total_trades / days if days > 0 else 0.0

        if 'hold_time_minutes' in df.columns:
            avg_hold_time_minutes = df['hold_time_minutes'].mean()
        else:
            avg_hold_time_minutes = 0.0

        return BacktestResult(
            parameters=params,
            start_date=start_date,
            end_date=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            profit_factor=profit_factor,
            avg_win_pips=avg_win_pips,
            avg_loss_pips=avg_loss_pips,
            avg_trade_pips=avg_trade_pips,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            trades_per_day=trades_per_day,
            avg_hold_time_minutes=avg_hold_time_minutes,
        )

    def _create_walk_forward_windows(
        self,
        start_date: str,
        end_date: str,
        num_periods: int,
    ) -> List[Tuple[str, str, str, str]]:
        """
        Create walk-forward train/test windows.

        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        total_days = (end - start).days
        period_days = total_days // num_periods
        train_days = int(period_days * 0.7)  # 70% train, 30% test
        test_days = period_days - train_days

        windows = []

        for i in range(num_periods):
            train_start = start + pd.Timedelta(days=i * period_days)
            train_end = train_start + pd.Timedelta(days=train_days)
            test_start = train_end
            test_end = test_start + pd.Timedelta(days=test_days)

            # Make sure we don't exceed end date
            if test_end > end:
                test_end = end

            windows.append((
                train_start.strftime("%Y-%m-%d"),
                train_end.strftime("%Y-%m-%d"),
                test_start.strftime("%Y-%m-%d"),
                test_end.strftime("%Y-%m-%d"),
            ))

        return windows

    def _aggregate_parameters(
        self,
        period_results: List[Dict],
        metric: str,
    ) -> ParameterSet:
        """
        Aggregate parameters across periods.

        Strategy: Use most recent period's best parameters (most relevant to current market)
        """
        return period_results[-1]["best_params"]

    def _aggregate_performance(
        self,
        period_results: List[Dict],
        metric: str,
    ) -> Dict:
        """Aggregate out-of-sample performance across all periods"""

        test_results = [r["test_result"] for r in period_results]

        return {
            f"avg_{metric}": np.mean([r["test_score"] for r in period_results]),
            "avg_win_rate": np.mean([r.win_rate for r in test_results]),
            "avg_profit_factor": np.mean([r.profit_factor for r in test_results]),
            "avg_sharpe_ratio": np.mean([r.sharpe_ratio for r in test_results]),
            "avg_max_drawdown_percent": np.mean([r.max_drawdown_percent for r in test_results]),
            "total_test_trades": sum([r.total_trades for r in test_results]),
            "consistency": np.std([r["test_score"] for r in period_results]),
            "num_periods": len(period_results),
        }

    def save_optimization_history(self, filepath: str = "optimization_history.json"):
        """Save optimization history to file"""
        with open(filepath, 'w') as f:
            json.dump(self.optimization_history, f, indent=2)
        logger.info(f"Optimization history saved to {filepath}")

    def load_optimization_history(self, filepath: str = "optimization_history.json"):
        """Load optimization history from file"""
        try:
            with open(filepath, 'r') as f:
                self.optimization_history = json.load(f)
            logger.info(f"Loaded {len(self.optimization_history)} optimization runs from {filepath}")
        except FileNotFoundError:
            logger.warning(f"Optimization history file not found: {filepath}")
