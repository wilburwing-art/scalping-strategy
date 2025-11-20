"""
Test Parameter Optimization Framework

Demonstrates parameter optimization using historical trade data.

Usage:
    # Quick test with mock data
    uv run test_optimizer.py

    # Full optimization with real trade journal
    uv run test_optimizer.py --real-data --journal trades.db
"""

import asyncio
import logging
import sys
import random
from datetime import datetime, timedelta
from parameter_optimizer import ParameterOptimizer, ParameterSet, BacktestResult
from trade_journal import TradeJournal, TradeJournalEntry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def create_mock_trades(journal: TradeJournal, num_trades: int = 100, instrument: str = "EUR_USD"):
    """Create mock trades for testing"""

    logger.info(f"Generating {num_trades} mock trades for {instrument}...")

    # Focus on the instrument we're optimizing
    instruments = [instrument] * 3 + ["GBP_USD", "USD_JPY"]  # 60% EUR_USD
    directions = ["BUY", "SELL"]
    sessions = ["asian", "london", "ny", "overlap"]
    exit_reasons = ["TAKE_PROFIT", "STOP_LOSS", "MANUAL", "TIME"]

    start_date = datetime.now() - timedelta(days=180)  # 6 months of data

    for i in range(num_trades):
        instrument = random.choice(instruments)
        direction = random.choice(directions)

        # Random entry time
        entry_time = start_date + timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        # Random indicators
        rsi = random.uniform(20, 80)
        atr = random.uniform(0.0005, 0.0030)
        ma_short = 1.0850 + random.uniform(-0.01, 0.01)
        ma_long = 1.0840 + random.uniform(-0.01, 0.01)

        # Generate trade outcome (biased towards wins for variety)
        is_winner = random.random() < 0.55

        if is_winner:
            net_pips = random.uniform(5, 25)
            profit_usd = net_pips * 10  # $10/pip for 10k units
            exit_reason = random.choice(["TAKE_PROFIT", "MANUAL", "TIME"])
        else:
            net_pips = random.uniform(-20, -5)
            profit_usd = net_pips * 10
            exit_reason = random.choice(["STOP_LOSS", "MANUAL", "TIME"])

        # Random exit time (5 minutes to 4 hours later)
        hold_time_minutes = random.randint(5, 240)
        exit_time = entry_time + timedelta(minutes=hold_time_minutes)

        # Random confidence score
        confidence = random.uniform(0.4, 0.9)

        entry = TradeJournalEntry(
            trade_id=f"mock_{i+1:04d}",
            timestamp=entry_time,
            instrument=instrument,
            direction=direction,
            units=10000,
            entry_price=1.0850 + random.uniform(-0.01, 0.01),
            entry_time=entry_time,
            exit_price=1.0850 + random.uniform(-0.01, 0.01),
            exit_time=exit_time,
            exit_reason=exit_reason,
            gross_pips=net_pips,
            net_pips=net_pips,
            profit_usd=profit_usd,
            session=random.choice(sessions),
            rsi=rsi,
            atr=atr,
            ma_short=ma_short,
            ma_long=ma_long,
            overall_confidence=confidence,
            hold_time_minutes=hold_time_minutes,
            environment="practice",
        )

        journal.log_entry(entry)

    logger.info(f"✅ Generated {num_trades} mock trades")


async def test_parameter_optimizer():
    """Test the parameter optimizer"""

    print("\n" + "="*60)
    print("🔬 PARAMETER OPTIMIZATION TEST")
    print("="*60)

    # Create test database
    journal = TradeJournal("test_optimizer.db")

    # Generate mock trades
    print("\n📊 Setting up test data...")
    create_mock_trades(journal, num_trades=300, instrument="EUR_USD")

    # Get date range
    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    print(f"\nOptimization period: {start_date} to {end_date}")

    # Initialize optimizer
    optimizer = ParameterOptimizer(journal)

    # Test 1: Small grid search (fast)
    print("\n" + "="*60)
    print("TEST 1: Quick Parameter Grid Search")
    print("="*60)

    small_grid = {
        "rsi_period": [10, 14],
        "reward_risk_ratio": [1.5, 2.0],
        "min_confidence": [0.5, 0.6],
    }

    best_params, performance = await optimizer.optimize(
        instrument="EUR_USD",
        start_date=start_date,
        end_date=end_date,
        param_grid=small_grid,
        optimization_metric="sharpe_ratio",
        walk_forward_periods=2,  # Fewer periods = more trades per period
        min_trades_per_period=10,
    )

    print("\n✅ Optimization complete!")
    print(f"\nBest Parameters:")
    print(f"  RSI Period: {best_params.rsi_period}")
    print(f"  Reward:Risk Ratio: {best_params.reward_risk_ratio}")
    print(f"  Min Confidence: {best_params.min_confidence}")

    print(f"\nOut-of-Sample Performance:")
    print(f"  Avg Sharpe Ratio: {performance['avg_sharpe_ratio']:.3f}")
    print(f"  Avg Win Rate: {performance['avg_win_rate']:.1%}")
    print(f"  Avg Profit Factor: {performance['avg_profit_factor']:.2f}")
    print(f"  Total Test Trades: {performance['total_test_trades']}")
    print(f"  Consistency: {performance['consistency']:.3f} (lower = better)")

    # Test 2: Different optimization metrics
    print("\n" + "="*60)
    print("TEST 2: Optimize for Win Rate")
    print("="*60)

    best_params_wr, performance_wr = await optimizer.optimize(
        instrument="EUR_USD",
        start_date=start_date,
        end_date=end_date,
        param_grid=small_grid,
        optimization_metric="win_rate",
        walk_forward_periods=3,
        min_trades_per_period=5,
    )

    print("\n✅ Optimization complete!")
    print(f"\nBest Parameters (Win Rate):")
    print(f"  RSI Period: {best_params_wr.rsi_period}")
    print(f"  Reward:Risk Ratio: {best_params_wr.reward_risk_ratio}")
    print(f"  Min Confidence: {best_params_wr.min_confidence}")

    # Test 3: Profit factor optimization
    print("\n" + "="*60)
    print("TEST 3: Optimize for Profit Factor")
    print("="*60)

    best_params_pf, performance_pf = await optimizer.optimize(
        instrument="EUR_USD",
        start_date=start_date,
        end_date=end_date,
        param_grid=small_grid,
        optimization_metric="profit_factor",
        walk_forward_periods=3,
        min_trades_per_period=5,
    )

    print("\n✅ Optimization complete!")
    print(f"\nBest Parameters (Profit Factor):")
    print(f"  RSI Period: {best_params_pf.rsi_period}")
    print(f"  Reward:Risk Ratio: {best_params_pf.reward_risk_ratio}")
    print(f"  Min Confidence: {best_params_pf.min_confidence}")

    # Compare results
    print("\n" + "="*60)
    print("COMPARISON OF OPTIMIZATION OBJECTIVES")
    print("="*60)

    print("\n1. Sharpe Ratio Optimization:")
    print(f"   RSI Period: {best_params.rsi_period}")
    print(f"   R:R Ratio: {best_params.reward_risk_ratio}")
    print(f"   Min Conf: {best_params.min_confidence}")
    print(f"   → Sharpe: {performance['avg_sharpe_ratio']:.3f}, Win Rate: {performance['avg_win_rate']:.1%}")

    print("\n2. Win Rate Optimization:")
    print(f"   RSI Period: {best_params_wr.rsi_period}")
    print(f"   R:R Ratio: {best_params_wr.reward_risk_ratio}")
    print(f"   Min Conf: {best_params_wr.min_confidence}")
    print(f"   → Sharpe: {performance_wr['avg_sharpe_ratio']:.3f}, Win Rate: {performance_wr['avg_win_rate']:.1%}")

    print("\n3. Profit Factor Optimization:")
    print(f"   RSI Period: {best_params_pf.rsi_period}")
    print(f"   R:R Ratio: {best_params_pf.reward_risk_ratio}")
    print(f"   Min Conf: {best_params_pf.min_confidence}")
    print(f"   → Sharpe: {performance_pf['avg_sharpe_ratio']:.3f}, Win Rate: {performance_pf['avg_win_rate']:.1%}")

    # Save optimization history
    print("\n📁 Saving optimization history...")
    optimizer.save_optimization_history("test_optimization_history.json")

    # Cleanup
    journal.close()

    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)

    print("\n💡 Key Takeaways:")
    print("  1. Different objectives yield different optimal parameters")
    print("  2. Walk-forward validation prevents overfitting")
    print("  3. Consistency metric shows stability across periods")
    print("  4. Use Sharpe ratio for risk-adjusted performance")
    print("\n📚 For production use:")
    print("  - Use larger parameter grids (more combinations)")
    print("  - Require minimum 50+ trades per test period")
    print("  - Run on multiple instruments")
    print("  - Re-optimize quarterly as markets change")


async def demo_optimization_workflow():
    """Demonstrate full optimization workflow"""

    print("\n" + "="*60)
    print("📋 OPTIMIZATION WORKFLOW DEMO")
    print("="*60)

    journal = TradeJournal("test_optimizer.db")
    optimizer = ParameterOptimizer(journal)

    print("\n1. Define parameter grid")
    print("   Testing combinations of:")
    print("   - RSI periods: 10, 14, 20")
    print("   - R:R ratios: 1.2, 1.5, 2.0")
    print("   - Min confidence: 0.5, 0.6, 0.7")
    print("   = 3 × 3 × 3 = 27 combinations")

    print("\n2. Walk-forward validation (4 periods)")
    print("   Each period:")
    print("   - Train on 70% of data")
    print("   - Test on remaining 30%")
    print("   - Prevents overfitting to historical data")

    print("\n3. Select best parameters")
    print("   - Use most recent period (market relevance)")
    print("   - Validate performance is consistent across periods")

    print("\n4. Apply to live trading")
    print("   - Monitor performance vs. optimization results")
    print("   - Re-optimize if performance degrades")
    print("   - Typical re-optimization: quarterly")

    journal.close()

    print("\n✅ Workflow demo complete")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        asyncio.run(demo_optimization_workflow())
    else:
        asyncio.run(test_parameter_optimizer())
