"""
Trade Journaling System

Comprehensive trade tracking with SQLite backend for performance analysis
and systematic improvement.

Usage:
    journal = TradeJournal("trades.db")

    # Log trade entry
    journal.log_entry(entry)

    # Log trade exit
    journal.log_exit(trade_id, exit_price, exit_reason, ...)

    # Get statistics
    stats = journal.get_statistics(days=30)
"""

import sqlite3
import pandas as pd
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


@dataclass
class TradeJournalEntry:
    """Complete record of a trade"""

    # Identifiers
    trade_id: str
    timestamp: datetime

    # Instrument details
    instrument: str
    direction: str  # "BUY" or "SELL"
    units: int

    # Entry
    entry_price: float
    entry_time: datetime

    # Exit (filled when trade closes)
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None  # "STOP_LOSS", "TAKE_PROFIT", "MANUAL", "TIME"

    # P/L
    gross_pips: Optional[float] = None
    costs_pips: float = 0.0
    net_pips: Optional[float] = None
    profit_usd: Optional[float] = None

    # Market context at entry
    session: Optional[str] = None  # "asian", "london", "ny", "overlap"
    rsi: Optional[float] = None
    atr: Optional[float] = None
    ma_short: Optional[float] = None
    ma_long: Optional[float] = None
    spread_pips: Optional[float] = None

    # Agent analysis (if using AI agents)
    market_intel_score: Optional[float] = None
    technical_score: Optional[float] = None
    risk_score: Optional[float] = None
    overall_confidence: Optional[float] = None
    agent_reasoning: Optional[str] = None

    # News/sentiment context
    news_events_nearby: Optional[str] = None  # JSON string of events
    sentiment_score: Optional[float] = None
    sentiment_volume: Optional[int] = None

    # Risk management
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward_ratio: Optional[float] = None
    position_size_pct: Optional[float] = None  # % of account

    # Performance metrics
    hold_time_minutes: Optional[int] = None
    max_adverse_excursion_pips: Optional[float] = None  # MAE
    max_favorable_excursion_pips: Optional[float] = None  # MFE

    # Metadata
    strategy_version: str = "3.0"
    environment: str = "practice"  # "practice" or "live"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization"""
        data = asdict(self)
        # Convert datetime to ISO string
        if isinstance(data["timestamp"], datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        if isinstance(data["entry_time"], datetime):
            data["entry_time"] = data["entry_time"].isoformat()
        if data["exit_time"] and isinstance(data["exit_time"], datetime):
            data["exit_time"] = data["exit_time"].isoformat()
        return data


class TradeJournal:
    """
    SQLite-based trade journal with analytics.

    Features:
    - Log trade entries and exits
    - Track all market context and indicators
    - Calculate performance statistics
    - Analyze by session, instrument, strategy
    - Export to CSV/Excel
    - Identify winning/losing patterns

    Usage:
        journal = TradeJournal("trades.db")

        # Log entry
        entry = TradeJournalEntry(
            trade_id="123",
            timestamp=datetime.now(),
            instrument="EUR_USD",
            direction="BUY",
            units=10000,
            entry_price=1.0850,
            entry_time=datetime.now(),
            rsi=35.5,
            atr=0.0012,
            ...
        )
        journal.log_entry(entry)

        # Log exit
        journal.log_exit(
            trade_id="123",
            exit_price=1.0865,
            exit_time=datetime.now(),
            exit_reason="TAKE_PROFIT",
            gross_pips=15.0,
            net_pips=12.0,
            profit_usd=12.00,
        )

        # Get statistics
        stats = journal.get_statistics(days=30)
        print(f"Win rate: {stats['win_rate']:.1%}")
    """

    def __init__(self, db_path: str = "trade_journal.db"):
        """
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        logger.info(f"Trade journal initialized: {db_path}")

    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            instrument TEXT NOT NULL,
            direction TEXT NOT NULL,
            units INTEGER NOT NULL,

            entry_price REAL NOT NULL,
            entry_time TEXT NOT NULL,

            exit_price REAL,
            exit_time TEXT,
            exit_reason TEXT,

            gross_pips REAL,
            costs_pips REAL DEFAULT 0,
            net_pips REAL,
            profit_usd REAL,

            session TEXT,
            rsi REAL,
            atr REAL,
            ma_short REAL,
            ma_long REAL,
            spread_pips REAL,

            market_intel_score REAL,
            technical_score REAL,
            risk_score REAL,
            overall_confidence REAL,
            agent_reasoning TEXT,

            news_events_nearby TEXT,
            sentiment_score REAL,
            sentiment_volume INTEGER,

            stop_loss REAL DEFAULT 0,
            take_profit REAL DEFAULT 0,
            risk_reward_ratio REAL,
            position_size_pct REAL,

            hold_time_minutes INTEGER,
            max_adverse_excursion_pips REAL,
            max_favorable_excursion_pips REAL,

            strategy_version TEXT DEFAULT '3.0',
            environment TEXT DEFAULT 'practice',
            notes TEXT
        )
        """)

        # Create indices for fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_instrument ON trades(instrument)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exit_time ON trades(exit_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_environment ON trades(environment)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON trades(session)")

        self.conn.commit()
        logger.debug("Database tables created/verified")

    def log_entry(self, entry: TradeJournalEntry):
        """
        Log trade entry.

        Args:
            entry: TradeJournalEntry object with entry details
        """
        cursor = self.conn.cursor()

        # Convert dataclass to dict
        data = entry.to_dict()

        # Insert
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])

        cursor.execute(
            f"INSERT OR REPLACE INTO trades ({columns}) VALUES ({placeholders})",
            list(data.values())
        )

        self.conn.commit()
        logger.info(
            f"📝 Trade entry logged: {entry.trade_id} - {entry.direction} "
            f"{entry.units} {entry.instrument} @ {entry.entry_price}"
        )

    def log_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
        gross_pips: float,
        net_pips: float,
        profit_usd: float,
        hold_time_minutes: Optional[int] = None,
        max_adverse_pips: Optional[float] = None,
        max_favorable_pips: Optional[float] = None,
    ):
        """
        Update trade with exit information.

        Args:
            trade_id: Trade ID to update
            exit_price: Exit price
            exit_time: Exit timestamp
            exit_reason: Reason for exit (STOP_LOSS, TAKE_PROFIT, MANUAL, TIME)
            gross_pips: Gross P/L in pips
            net_pips: Net P/L in pips (after costs)
            profit_usd: P/L in USD
            hold_time_minutes: How long trade was held
            max_adverse_pips: Maximum adverse excursion (MAE)
            max_favorable_pips: Maximum favorable excursion (MFE)
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        UPDATE trades SET
            exit_price = ?,
            exit_time = ?,
            exit_reason = ?,
            gross_pips = ?,
            net_pips = ?,
            profit_usd = ?,
            hold_time_minutes = ?,
            max_adverse_excursion_pips = ?,
            max_favorable_excursion_pips = ?
        WHERE trade_id = ?
        """, (
            exit_price,
            exit_time.isoformat(),
            exit_reason,
            gross_pips,
            net_pips,
            profit_usd,
            hold_time_minutes,
            max_adverse_pips,
            max_favorable_pips,
            trade_id,
        ))

        self.conn.commit()

        emoji = "✅" if net_pips > 0 else "❌"
        logger.info(
            f"{emoji} Trade exit logged: {trade_id} - {exit_reason} - "
            f"{net_pips:+.1f} pips (${profit_usd:+.2f})"
        )

    def get_statistics(
        self,
        days: Optional[int] = None,
        instrument: Optional[str] = None,
        environment: str = "practice",
        min_trades: int = 5,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance statistics.

        Args:
            days: Last N days (None = all time)
            instrument: Filter by instrument (None = all)
            environment: "practice" or "live"
            min_trades: Minimum trades required for valid stats

        Returns:
            Dictionary of statistics
        """
        # Build query
        query = "SELECT * FROM trades WHERE environment = ? AND exit_time IS NOT NULL"
        params = [environment]

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND exit_time >= ?"
            params.append(cutoff)

        if instrument:
            query += " AND instrument = ?"
            params.append(instrument)

        # Fetch data
        df = pd.read_sql_query(query, self.conn, params=params)

        if len(df) < min_trades:
            return {
                "total_trades": len(df),
                "message": f"Insufficient trades ({len(df)} < {min_trades} required)",
                "valid": False,
            }

        # Basic stats
        total_trades = len(df)
        winners = df[df["net_pips"] > 0]
        losers = df[df["net_pips"] < 0]
        breakeven = df[df["net_pips"] == 0]

        win_rate = len(winners) / total_trades if total_trades > 0 else 0

        # P/L stats
        total_profit_usd = df["profit_usd"].sum()
        total_pips = df["net_pips"].sum()

        avg_win_pips = winners["net_pips"].mean() if len(winners) > 0 else 0
        avg_loss_pips = losers["net_pips"].mean() if len(losers) > 0 else 0
        avg_win_usd = winners["profit_usd"].mean() if len(winners) > 0 else 0
        avg_loss_usd = losers["profit_usd"].mean() if len(losers) > 0 else 0

        # Profit factor
        gross_profit = winners["profit_usd"].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers["profit_usd"].sum()) if len(losers) > 0 else 0.01
        profit_factor = gross_profit / gross_loss

        # Expectancy
        expectancy = (win_rate * avg_win_usd) + ((1 - win_rate) * avg_loss_usd)

        # Sharpe ratio (simplified)
        returns = df["profit_usd"]
        sharpe = (returns.mean() / returns.std()) if returns.std() > 0 else 0

        # Consecutive wins/losses
        is_winner = (df["net_pips"] > 0).astype(int)
        consecutive = is_winner.diff().ne(0).cumsum()
        max_consecutive_wins = is_winner.groupby(consecutive).sum().max()
        max_consecutive_losses = (1 - is_winner).groupby(consecutive).sum().max()

        # Drawdown
        cumulative_pl = df["profit_usd"].cumsum()
        running_max = cumulative_pl.cummax()
        drawdown = cumulative_pl - running_max
        max_drawdown_usd = drawdown.min()

        # Exit reason breakdown
        exit_reasons = df["exit_reason"].value_counts().to_dict()

        # Average hold time
        avg_hold_time = df["hold_time_minutes"].mean() if "hold_time_minutes" in df.columns else None

        # Cost analysis
        total_costs_pips = df["costs_pips"].sum()
        avg_cost_per_trade = total_costs_pips / total_trades

        stats = {
            "valid": True,
            "total_trades": total_trades,
            "winners": len(winners),
            "losers": len(losers),
            "breakeven": len(breakeven),
            "win_rate": win_rate,
            "total_profit_usd": total_profit_usd,
            "total_pips": total_pips,
            "avg_win_pips": avg_win_pips,
            "avg_loss_pips": avg_loss_pips,
            "avg_win_usd": avg_win_usd,
            "avg_loss_usd": avg_loss_usd,
            "profit_factor": profit_factor,
            "expectancy_usd": expectancy,
            "sharpe_ratio": sharpe,
            "max_consecutive_wins": int(max_consecutive_wins) if not pd.isna(max_consecutive_wins) else 0,
            "max_consecutive_losses": int(max_consecutive_losses) if not pd.isna(max_consecutive_losses) else 0,
            "max_drawdown_usd": max_drawdown_usd,
            "exit_reasons": exit_reasons,
            "avg_hold_time_minutes": avg_hold_time,
            "total_costs_pips": total_costs_pips,
            "avg_cost_per_trade_pips": avg_cost_per_trade,
        }

        return stats

    def get_performance_by_session(self, days: Optional[int] = None) -> pd.DataFrame:
        """Analyze performance by trading session"""
        query = "SELECT session, COUNT(*) as trades, AVG(net_pips) as avg_pips, SUM(profit_usd) as total_profit FROM trades WHERE exit_time IS NOT NULL"
        params = []

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND exit_time >= ?"
            params.append(cutoff)

        query += " GROUP BY session ORDER BY total_profit DESC"

        return pd.read_sql_query(query, self.conn, params=params)

    def get_performance_by_instrument(self, days: Optional[int] = None) -> pd.DataFrame:
        """Analyze performance by instrument"""
        query = """
        SELECT
            instrument,
            COUNT(*) as trades,
            SUM(CASE WHEN net_pips > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate,
            AVG(net_pips) as avg_pips,
            SUM(profit_usd) as total_profit
        FROM trades
        WHERE exit_time IS NOT NULL
        """
        params = []

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND exit_time >= ?"
            params.append(cutoff)

        query += " GROUP BY instrument ORDER BY total_profit DESC"

        return pd.read_sql_query(query, self.conn, params=params)

    def get_performance_by_confidence(self, days: Optional[int] = None) -> pd.DataFrame:
        """Analyze how agent confidence correlates with performance"""
        query = """
        SELECT
            CASE
                WHEN overall_confidence >= 0.7 THEN 'High (>70%)'
                WHEN overall_confidence >= 0.5 THEN 'Medium (50-70%)'
                ELSE 'Low (<50%)'
            END as confidence_bucket,
            COUNT(*) as trades,
            SUM(CASE WHEN net_pips > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate,
            AVG(net_pips) as avg_pips,
            SUM(profit_usd) as total_profit
        FROM trades
        WHERE exit_time IS NOT NULL AND overall_confidence IS NOT NULL
        """
        params = []

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND exit_time >= ?"
            params.append(cutoff)

        query += " GROUP BY confidence_bucket ORDER BY win_rate DESC"

        return pd.read_sql_query(query, self.conn, params=params)

    def export_to_csv(self, filepath: str, days: Optional[int] = None):
        """
        Export journal to CSV.

        Args:
            filepath: Output CSV file path
            days: Last N days (None = all trades)
        """
        query = "SELECT * FROM trades WHERE exit_time IS NOT NULL"
        params = []

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND exit_time >= ?"
            params.append(cutoff)

        query += " ORDER BY exit_time DESC"

        df = pd.read_sql_query(query, self.conn, params=params)
        df.to_csv(filepath, index=False)
        logger.info(f"📤 Exported {len(df)} trades to {filepath}")

    def print_report(self, days: int = 30):
        """
        Print formatted performance report.

        Args:
            days: Last N days to analyze
        """
        stats = self.get_statistics(days=days)

        if not stats.get("valid"):
            print(f"\n⚠️  {stats.get('message', 'Insufficient data')}\n")
            return

        print("\n" + "="*60)
        print(f"📊 PERFORMANCE REPORT - Last {days} Days")
        print("="*60)

        print(f"\n📈 Overall Performance:")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Winners: {stats['winners']} | Losers: {stats['losers']} | Breakeven: {stats['breakeven']}")
        print(f"  Win Rate: {stats['win_rate']:.1%}")
        print(f"  Total P/L: ${stats['total_profit_usd']:,.2f} ({stats['total_pips']:+.1f} pips)")

        print(f"\n💰 Trade Averages:")
        print(f"  Avg Win: {stats['avg_win_pips']:+.1f} pips (${stats['avg_win_usd']:+.2f})")
        print(f"  Avg Loss: {stats['avg_loss_pips']:+.1f} pips (${stats['avg_loss_usd']:+.2f})")
        print(f"  Expectancy: ${stats['expectancy_usd']:+.2f} per trade")

        print(f"\n📊 Risk Metrics:")
        print(f"  Profit Factor: {stats['profit_factor']:.2f}")
        print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: ${stats['max_drawdown_usd']:,.2f}")
        print(f"  Max Consecutive Wins: {stats['max_consecutive_wins']}")
        print(f"  Max Consecutive Losses: {stats['max_consecutive_losses']}")

        if stats['avg_hold_time_minutes']:
            print(f"\n⏱️  Trading Behavior:")
            print(f"  Avg Hold Time: {stats['avg_hold_time_minutes']:.0f} minutes")

        print(f"\n💸 Costs:")
        print(f"  Total Costs: {stats['total_costs_pips']:.1f} pips")
        print(f"  Avg Cost per Trade: {stats['avg_cost_per_trade_pips']:.1f} pips")

        print(f"\n🎯 Exit Reasons:")
        for reason, count in stats['exit_reasons'].items():
            pct = (count / stats['total_trades']) * 100
            print(f"  {reason}: {count} ({pct:.1f}%)")

        # Performance by session
        print(f"\n🌍 Performance by Session:")
        session_df = self.get_performance_by_session(days=days)
        if not session_df.empty:
            for _, row in session_df.iterrows():
                print(f"  {row['session']:8} : {row['trades']:3} trades, {row['avg_pips']:+6.1f} pips avg, ${row['total_profit']:+8.2f} total")

        # Performance by instrument
        print(f"\n💱 Top 5 Instruments:")
        instrument_df = self.get_performance_by_instrument(days=days)
        if not instrument_df.empty:
            for _, row in instrument_df.head(5).iterrows():
                print(f"  {row['instrument']:8} : {row['trades']:3} trades, {row['win_rate']:.1%} win rate, ${row['total_profit']:+8.2f}")

        # Performance by confidence
        print(f"\n🤖 Performance by AI Confidence:")
        confidence_df = self.get_performance_by_confidence(days=days)
        if not confidence_df.empty:
            for _, row in confidence_df.iterrows():
                print(f"  {row['confidence_bucket']:15} : {row['trades']:3} trades, {row['win_rate']:.1%} win rate, ${row['total_profit']:+8.2f}")

        print("\n" + "="*60 + "\n")

    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Trade journal closed")


# Example usage
def example():
    """Example of how to use TradeJournal"""
    from datetime import datetime

    # Create journal
    journal = TradeJournal("example_trades.db")

    # Log a winning trade
    entry = TradeJournalEntry(
        trade_id="trade_001",
        timestamp=datetime.now(),
        instrument="EUR_USD",
        direction="BUY",
        units=10000,
        entry_price=1.0850,
        entry_time=datetime.now(),
        session="london",
        rsi=35.2,
        atr=0.0012,
        ma_short=1.0855,
        ma_long=1.0840,
        overall_confidence=0.75,
        stop_loss=1.0835,
        take_profit=1.0870,
    )
    journal.log_entry(entry)

    # Exit the trade
    journal.log_exit(
        trade_id="trade_001",
        exit_price=1.0870,
        exit_time=datetime.now(),
        exit_reason="TAKE_PROFIT",
        gross_pips=20.0,
        net_pips=17.5,
        profit_usd=17.50,
        hold_time_minutes=45,
    )

    # Get statistics
    stats = journal.get_statistics()
    print(f"Win rate: {stats['win_rate']:.1%}")

    # Print report
    journal.print_report(days=30)

    journal.close()


if __name__ == "__main__":
    example()
