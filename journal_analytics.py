"""
Trade Journal Analytics

Standalone script for analyzing trade journal data and generating reports.

Usage:
    # Print 30-day report
    uv run journal_analytics.py

    # Custom time period
    uv run journal_analytics.py --days 90

    # Export to CSV
    uv run journal_analytics.py --export trades_2024.csv

    # Specific instrument
    uv run journal_analytics.py --instrument EUR_USD
"""

import argparse
import logging
import sys
from datetime import datetime

from trade_journal import TradeJournal

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def print_detailed_report(journal: TradeJournal, days: int, instrument: str = None):
    """Print comprehensive performance report"""

    # Main statistics
    journal.print_report(days=days)

    # Additional analysis
    print("\n" + "="*60)
    print("📈 DETAILED ANALYSIS")
    print("="*60)

    # Performance by session
    print("\n🌍 Performance by Session (Detailed):")
    session_df = journal.get_performance_by_session(days=days)
    if not session_df.empty:
        print(session_df.to_string(index=False))
    else:
        print("  No session data available")

    # Performance by instrument
    print("\n💱 Performance by Instrument:")
    instrument_df = journal.get_performance_by_instrument(days=days)
    if not instrument_df.empty:
        print(instrument_df.to_string(index=False))
    else:
        print("  No instrument data available")

    # Performance by confidence
    print("\n🤖 Performance by AI Agent Confidence:")
    confidence_df = journal.get_performance_by_confidence(days=days)
    if not confidence_df.empty:
        print(confidence_df.to_string(index=False))
    else:
        print("  No confidence data available (agents not used?)")

    print("\n" + "="*60)


def compare_periods(journal: TradeJournal):
    """Compare performance across different time periods"""
    print("\n" + "="*60)
    print("📊 PERIOD COMPARISON")
    print("="*60)

    periods = {
        "Last 7 Days": 7,
        "Last 30 Days": 30,
        "Last 90 Days": 90,
        "All Time": None,
    }

    results = []

    for period_name, days in periods.items():
        stats = journal.get_statistics(days=days, min_trades=1)

        if stats.get("valid"):
            results.append({
                "Period": period_name,
                "Trades": stats["total_trades"],
                "Win Rate": f"{stats['win_rate']:.1%}",
                "Total P/L": f"${stats['total_profit_usd']:,.2f}",
                "Avg Trade": f"${stats['expectancy_usd']:+.2f}",
                "Sharpe": f"{stats['sharpe_ratio']:.2f}",
            })

    if results:
        import pandas as pd
        df = pd.DataFrame(results)
        print("\n" + df.to_string(index=False))
    else:
        print("\n⚠️  No data available for comparison")

    print("\n" + "="*60)


def identify_patterns(journal: TradeJournal, days: int = 30):
    """Identify winning and losing patterns"""
    print("\n" + "="*60)
    print("🔍 PATTERN ANALYSIS")
    print("="*60)

    # Best and worst instruments
    print("\n💱 Best & Worst Instruments:")
    instrument_df = journal.get_performance_by_instrument(days=days)

    if not instrument_df.empty and len(instrument_df) > 0:
        best = instrument_df.iloc[0]
        worst = instrument_df.iloc[-1]

        print(f"  🏆 Best:  {best['instrument']} - {best['win_rate']:.1%} WR, ${best['total_profit']:+.2f}")
        print(f"  ⚠️  Worst: {worst['instrument']} - {worst['win_rate']:.1%} WR, ${worst['total_profit']:+.2f}")
    else:
        print("  No data available")

    # Best and worst sessions
    print("\n🌍 Best & Worst Sessions:")
    session_df = journal.get_performance_by_session(days=days)

    if not session_df.empty and len(session_df) > 0:
        best = session_df.iloc[0]
        worst = session_df.iloc[-1]

        print(f"  🏆 Best:  {best['session']} - {best['avg_pips']:+.1f} pips avg, ${best['total_profit']:+.2f}")
        print(f"  ⚠️  Worst: {worst['session']} - {worst['avg_pips']:+.1f} pips avg, ${worst['total_profit']:+.2f}")
    else:
        print("  No data available")

    # Agent confidence correlation
    print("\n🤖 AI Agent Confidence Validation:")
    confidence_df = journal.get_performance_by_confidence(days=days)

    if not confidence_df.empty:
        print("  Does higher confidence = better performance?")
        for _, row in confidence_df.iterrows():
            print(f"    {row['confidence_bucket']:15} : {row['win_rate']:.1%} WR, ${row['total_profit']:+.2f}")
    else:
        print("  No agent data available")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Trade Journal Analytics")
    parser.add_argument("--db", default="trades.db", help="Journal database path")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--instrument", help="Filter by instrument (e.g., EUR_USD)")
    parser.add_argument("--export", help="Export to CSV file")
    parser.add_argument("--compare", action="store_true", help="Compare time periods")
    parser.add_argument("--patterns", action="store_true", help="Identify patterns")

    args = parser.parse_args()

    # Open journal
    try:
        journal = TradeJournal(db_path=args.db)
    except Exception as e:
        logger.error(f"❌ Failed to open journal database: {e}")
        logger.info(f"Make sure {args.db} exists and contains trade data")
        sys.exit(1)

    # Main report
    print_detailed_report(journal, args.days, args.instrument)

    # Optional: Period comparison
    if args.compare:
        compare_periods(journal)

    # Optional: Pattern analysis
    if args.patterns:
        identify_patterns(journal, args.days)

    # Optional: Export
    if args.export:
        try:
            journal.export_to_csv(args.export, days=args.days)
            print(f"\n✓ Exported to {args.export}")
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")

    journal.close()


if __name__ == "__main__":
    main()
