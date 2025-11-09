"""
Test script for Trade Journal

Creates sample trades to test journal functionality and analytics.

Usage:
    uv run test_trade_journal.py
"""

import logging
import sys
from datetime import datetime, timedelta
import random

from trade_journal import TradeJournal, TradeJournalEntry

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def generate_sample_trades(num_trades: int = 50) -> list[TradeJournalEntry]:
    """Generate realistic sample trades for testing"""

    instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "EUR_GBP"]
    sessions = ["asian", "london", "ny", "overlap"]
    exit_reasons = ["TAKE_PROFIT", "STOP_LOSS", "MANUAL", "TIME"]

    trades = []
    current_time = datetime.now() - timedelta(days=30)  # Start 30 days ago

    for i in range(num_trades):
        instrument = random.choice(instruments)
        direction = random.choice(["BUY", "SELL"])
        session = random.choice(sessions)

        # Entry details
        base_price = 1.0850 if "EUR" in instrument else 1.2500 if "GBP" in instrument else 110.50
        entry_price = base_price + random.uniform(-0.0050, 0.0050)
        units = random.choice([10000, 20000, 50000])

        # Indicators
        rsi = random.uniform(25, 75)
        atr = random.uniform(0.0008, 0.0020)
        ma_short = entry_price + random.uniform(-0.0010, 0.0010)
        ma_long = entry_price + random.uniform(-0.0015, 0.0015)

        # Risk management
        stop_distance = atr * 1.5
        stop_loss = entry_price - stop_distance if direction == "BUY" else entry_price + stop_distance
        take_profit = entry_price + (stop_distance * 1.5) if direction == "BUY" else entry_price - (stop_distance * 1.5)

        # Agent scores (simulate)
        confidence = random.uniform(0.5, 0.95)
        market_intel = random.uniform(40, 90)
        technical = random.uniform(40, 90)
        risk_score = random.uniform(40, 90)

        # Create entry
        entry_time = current_time + timedelta(hours=random.randint(1, 23))

        trade = TradeJournalEntry(
            trade_id=f"test_{i+1:03d}",
            timestamp=entry_time,
            instrument=instrument,
            direction=direction,
            units=units,
            entry_price=entry_price,
            entry_time=entry_time,
            session=session,
            rsi=rsi,
            atr=atr,
            ma_short=ma_short,
            ma_long=ma_long,
            spread_pips=random.uniform(1.0, 3.0),
            market_intel_score=market_intel,
            technical_score=technical,
            risk_score=risk_score,
            overall_confidence=confidence,
            agent_reasoning=f"Sample reasoning for trade {i+1}",
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=1.5,
            position_size_pct=random.uniform(2, 5),
            strategy_version="3.0-test",
            environment="practice",
        )

        # Simulate exit (70% win rate for testing)
        is_winner = random.random() < 0.70 if confidence > 0.6 else random.random() < 0.45

        exit_reason = random.choice(exit_reasons)
        if is_winner and exit_reason == "STOP_LOSS":
            exit_reason = "TAKE_PROFIT"
        elif not is_winner and exit_reason == "TAKE_PROFIT":
            exit_reason = "STOP_LOSS"

        # Exit details
        hold_time = random.randint(15, 240)  # 15 min to 4 hours
        exit_time = entry_time + timedelta(minutes=hold_time)

        if is_winner:
            # Winner: hit take profit (mostly)
            pips_gain = random.uniform(10, 25) if exit_reason == "TAKE_PROFIT" else random.uniform(3, 12)
            gross_pips = pips_gain if direction == "BUY" else pips_gain
            exit_price = entry_price + (gross_pips / 10000) if direction == "BUY" else entry_price - (gross_pips / 10000)
        else:
            # Loser: hit stop loss (mostly)
            pips_loss = random.uniform(-15, -8) if exit_reason == "STOP_LOSS" else random.uniform(-10, -5)
            gross_pips = pips_loss
            exit_price = entry_price + (gross_pips / 10000) if direction == "BUY" else entry_price - (gross_pips / 10000)

        # Costs
        costs_pips = random.uniform(1.5, 3.0)
        net_pips = gross_pips - costs_pips

        # USD calculation (simplified)
        pip_value = units / 100000  # Rough approximation
        profit_usd = net_pips * pip_value

        # Add exit data to trade object
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = exit_reason
        trade.gross_pips = gross_pips
        trade.costs_pips = costs_pips
        trade.net_pips = net_pips
        trade.profit_usd = profit_usd
        trade.hold_time_minutes = hold_time
        trade.max_adverse_excursion_pips = random.uniform(2, 8)
        trade.max_favorable_excursion_pips = random.uniform(5, 20) if is_winner else random.uniform(2, 8)

        trades.append(trade)

        # Advance time
        current_time = entry_time

    return trades


def test_journal():
    """Test trade journal functionality"""

    print("\n" + "="*60)
    print("🧪 TRADE JOURNAL TEST")
    print("="*60)

    # Create test journal
    journal = TradeJournal("test_trades.db")

    # Generate sample trades
    print("\n1️⃣  Generating sample trades...")
    trades = generate_sample_trades(num_trades=50)
    print(f"   ✓ Generated {len(trades)} sample trades")

    # Log trades
    print("\n2️⃣  Logging trades to database...")
    for trade in trades:
        journal.log_entry(trade)

        # If trade is closed, log exit too
        if trade.exit_price:
            journal.log_exit(
                trade_id=trade.trade_id,
                exit_price=trade.exit_price,
                exit_time=trade.exit_time,
                exit_reason=trade.exit_reason,
                gross_pips=trade.gross_pips,
                net_pips=trade.net_pips,
                profit_usd=trade.profit_usd,
                hold_time_minutes=trade.hold_time_minutes,
                max_adverse_pips=trade.max_adverse_excursion_pips,
                max_favorable_pips=trade.max_favorable_excursion_pips,
            )

    print(f"   ✓ Logged {len(trades)} trades")

    # Test statistics
    print("\n3️⃣  Testing statistics calculation...")
    stats = journal.get_statistics(days=30)

    if stats.get("valid"):
        print(f"   ✓ Statistics calculated successfully")
        print(f"   - Total trades: {stats['total_trades']}")
        print(f"   - Win rate: {stats['win_rate']:.1%}")
        print(f"   - Total P/L: ${stats['total_profit_usd']:,.2f}")
        print(f"   - Profit factor: {stats['profit_factor']:.2f}")
    else:
        print(f"   ❌ Statistics failed: {stats.get('message')}")

    # Test session analysis
    print("\n4️⃣  Testing session analysis...")
    session_df = journal.get_performance_by_session(days=30)
    if not session_df.empty:
        print(f"   ✓ Session analysis working ({len(session_df)} sessions)")
        print(session_df.to_string(index=False))
    else:
        print("   ❌ No session data")

    # Test instrument analysis
    print("\n5️⃣  Testing instrument analysis...")
    instrument_df = journal.get_performance_by_instrument(days=30)
    if not instrument_df.empty:
        print(f"   ✓ Instrument analysis working ({len(instrument_df)} instruments)")
        print(instrument_df.to_string(index=False))
    else:
        print("   ❌ No instrument data")

    # Test confidence analysis
    print("\n6️⃣  Testing confidence analysis...")
    confidence_df = journal.get_performance_by_confidence(days=30)
    if not confidence_df.empty:
        print(f"   ✓ Confidence analysis working")
        print(confidence_df.to_string(index=False))
    else:
        print("   ❌ No confidence data")

    # Test export
    print("\n7️⃣  Testing CSV export...")
    try:
        journal.export_to_csv("test_trades_export.csv", days=30)
        print("   ✓ Export successful: test_trades_export.csv")
    except Exception as e:
        print(f"   ❌ Export failed: {e}")

    # Test reporting
    print("\n8️⃣  Testing performance report...")
    journal.print_report(days=30)

    # Cleanup
    journal.close()

    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)
    print("\nTest database created: test_trades.db")
    print("Test export created: test_trades_export.csv")
    print("\nTo view analytics:")
    print("  uv run journal_analytics.py --db test_trades.db")
    print("  uv run journal_analytics.py --db test_trades.db --compare")
    print("  uv run journal_analytics.py --db test_trades.db --patterns")
    print("")


if __name__ == "__main__":
    test_journal()
