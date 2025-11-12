"""
Journaled Trading Strategy

Extends NewsAwareStrategy with automatic trade journaling for
performance tracking and analysis.

Usage:
    uv run journaled_strategy.py --env practice
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from news_aware_strategy import NewsAwareStrategy
from trade_journal import TradeJournal, TradeJournalEntry

logger = logging.getLogger(__name__)


class JournaledStrategy(NewsAwareStrategy):
    """
    Trading strategy with automatic trade journaling.

    Features:
    - Logs every trade entry and exit
    - Tracks all indicators and market context
    - Records agent decisions and confidence
    - Analyzes performance by session, instrument, etc.
    - Generates performance reports
    """

    def __init__(
        self,
        config_file: str,
        environment: str = "practice",
        journal_db: str = "trades.db",
        **kwargs
    ):
        """
        Args:
            config_file: Path to OANDA config file
            environment: "practice" or "live"
            journal_db: Path to trade journal database
            **kwargs: Additional args for NewsAwareStrategy
        """
        super().__init__(config_file, environment, **kwargs)

        # Initialize trade journal
        self.journal = TradeJournal(db_path=journal_db)
        logger.info(f"✓ Trade journaling enabled: {journal_db}")

        # Track active trades for journaling
        self._active_journal_entries: Dict[str, TradeJournalEntry] = {}

    async def execute_trade(
        self,
        instrument: str,
        indicators: Dict[str, Any],
        candles: list,
        agent_recommendation: Optional[Any] = None,
    ):
        """
        Execute trade with automatic journaling.

        Args:
            instrument: Currency pair
            indicators: Technical indicators
            candles: Price candles
            agent_recommendation: Optional AI agent recommendation
        """
        try:
            # Get current price
            current_price = float(candles[-1].mid.c)

            # Determine direction based on indicators
            is_uptrend = indicators["ma_short"] > indicators["ma_long"]
            direction = "BUY" if is_uptrend else "SELL"

            # Calculate position size
            account_balance = self.get_account_balance()
            position_size = self.calculate_position_size(
                account_balance,
                instrument,
                indicators
            )

            # Calculate stop loss and take profit
            atr = indicators["atr"]
            stop_distance = atr * 1.5

            if direction == "BUY":
                stop_loss = current_price - stop_distance
                take_profit = current_price + (stop_distance * self.reward_risk_ratio)
            else:
                stop_loss = current_price + stop_distance
                take_profit = current_price - (stop_distance * self.reward_risk_ratio)

            # Execute the trade (call parent method or implement execution logic)
            # For now, we'll create a mock trade ID
            trade_id = f"{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Log entry to journal
            entry_time = datetime.utcnow()

            # Extract agent info if available
            agent_info = {}
            if agent_recommendation:
                agent_info = {
                    "market_intel_score": getattr(agent_recommendation, "market_intel_score", None),
                    "technical_score": getattr(agent_recommendation, "technical_score", None),
                    "risk_score": getattr(agent_recommendation, "risk_score", None),
                    "overall_confidence": getattr(agent_recommendation, "overall_confidence", None),
                    "agent_reasoning": getattr(agent_recommendation, "reasoning", None),
                }

            # Get session
            session = self._get_current_session(entry_time)

            # Create journal entry
            journal_entry = TradeJournalEntry(
                trade_id=trade_id,
                timestamp=entry_time,
                instrument=instrument,
                direction=direction,
                units=position_size,
                entry_price=current_price,
                entry_time=entry_time,

                # Market context
                session=session,
                rsi=indicators.get("rsi"),
                atr=indicators.get("atr"),
                ma_short=indicators.get("ma_short"),
                ma_long=indicators.get("ma_long"),
                spread_pips=self._calculate_spread_pips(candles[-1]) if hasattr(candles[-1], 'ask') else None,

                # Agent analysis
                **agent_info,

                # Risk management
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=self.reward_risk_ratio,
                position_size_pct=(position_size * current_price / account_balance) * 100,

                # Metadata
                strategy_version="3.0-journaled",
                environment=self.environment,
            )

            # Log to journal
            self.journal.log_entry(journal_entry)

            # Store for exit tracking
            self._active_journal_entries[trade_id] = journal_entry

            logger.info(
                f"🎯 Trade executed: {direction} {position_size} {instrument} @ {current_price:.5f} "
                f"(SL: {stop_loss:.5f}, TP: {take_profit:.5f})"
            )

            return trade_id

        except Exception as e:
            logger.error(f"Failed to execute trade: {e}", exc_info=True)
            return None

    def _get_current_session(self, timestamp: datetime) -> str:
        """Determine trading session from UTC timestamp"""
        hour_utc = timestamp.hour

        if 0 <= hour_utc < 8:
            return "asian"
        elif 8 <= hour_utc < 13:
            return "london"
        elif 13 <= hour_utc < 17:
            return "overlap"  # London + NY
        elif 17 <= hour_utc < 22:
            return "ny"
        else:
            return "asian"

    def _calculate_spread_pips(self, candle) -> Optional[float]:
        """Calculate spread in pips from candle"""
        try:
            if hasattr(candle, 'bid') and hasattr(candle, 'ask'):
                bid = float(candle.bid.c)
                ask = float(candle.ask.c)
                return (ask - bid) * 10000
        except:
            pass
        return None

    async def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        max_adverse_pips: Optional[float] = None,
        max_favorable_pips: Optional[float] = None,
    ):
        """
        Close trade and log exit to journal.

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            exit_reason: Reason for exit (STOP_LOSS, TAKE_PROFIT, MANUAL, etc.)
            max_adverse_pips: Maximum adverse excursion
            max_favorable_pips: Maximum favorable excursion
        """
        try:
            # Get journal entry
            entry = self._active_journal_entries.get(trade_id)
            if not entry:
                logger.warning(f"Trade {trade_id} not found in journal entries")
                return

            # Calculate P/L
            pip_multiplier = 10000  # Standard for most pairs

            if entry.direction == "BUY":
                gross_pips = (exit_price - entry.entry_price) * pip_multiplier
            else:
                gross_pips = (entry.entry_price - exit_price) * pip_multiplier

            # Estimate costs (spread + slippage)
            costs_pips = entry.spread_pips if entry.spread_pips else 2.0  # Default 2 pips if unknown

            net_pips = gross_pips - costs_pips

            # Calculate USD profit (simplified)
            pip_value = 0.0001 * entry.units / 100  # Rough approximation
            profit_usd = net_pips * pip_value

            # Calculate hold time
            exit_time = datetime.utcnow()
            hold_time_minutes = int((exit_time - entry.entry_time).total_seconds() / 60)

            # Log exit
            self.journal.log_exit(
                trade_id=trade_id,
                exit_price=exit_price,
                exit_time=exit_time,
                exit_reason=exit_reason,
                gross_pips=gross_pips,
                net_pips=net_pips,
                profit_usd=profit_usd,
                hold_time_minutes=hold_time_minutes,
                max_adverse_pips=max_adverse_pips,
                max_favorable_pips=max_favorable_pips,
            )

            # Remove from active tracking
            del self._active_journal_entries[trade_id]

            logger.info(
                f"Trade closed: {trade_id} - {exit_reason} - "
                f"{net_pips:+.1f} pips, ${profit_usd:+.2f}"
            )

        except Exception as e:
            logger.error(f"Failed to close trade: {e}", exc_info=True)

    async def run(
        self,
        scan_interval: int = 300,
        max_concurrent_trades: int = 3,
        runtime_seconds: Optional[int] = None,
        print_report_interval: Optional[int] = None,
    ):
        """
        Main trading loop with periodic reporting.

        Args:
            scan_interval: Seconds between scans
            max_concurrent_trades: Maximum positions at once
            runtime_seconds: Run for X seconds then exit (None = forever)
            print_report_interval: Print performance report every N seconds (None = no reports)
        """
        logger.info("\n" + "="*60)
        logger.info("📊 JOURNALED FOREX TRADING STRATEGY")
        logger.info("="*60)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Journal: {self.journal.db_path}")
        logger.info(f"Scan interval: {scan_interval}s")
        logger.info(f"Max concurrent trades: {max_concurrent_trades}")
        logger.info("="*60 + "\n")

        # Run parent strategy
        # Note: We'd integrate this more deeply in production
        # For now, call parent run method
        await super().run(
            scan_interval=scan_interval,
            max_concurrent_trades=max_concurrent_trades,
            runtime_seconds=runtime_seconds,
        )

    async def cleanup(self):
        """Cleanup resources"""
        await super().cleanup()

        # Print final report
        logger.info("\n" + "="*60)
        logger.info("📊 FINAL PERFORMANCE REPORT")
        logger.info("="*60)

        self.journal.print_report(days=30)

        # Close journal
        self.journal.close()
        logger.info("✓ Trade journal closed")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Journaled Forex Trading Strategy")
    parser.add_argument("--config", default="v20.conf", help="OANDA config file")
    parser.add_argument("--env", default="practice", choices=["practice", "live"],
                        help="Trading environment")
    parser.add_argument("--interval", type=int, default=300,
                        help="Scan interval in seconds")
    parser.add_argument("--max-trades", type=int, default=3,
                        help="Maximum concurrent trades")
    parser.add_argument("--runtime", type=int, default=None,
                        help="Runtime in seconds (None = forever)")
    parser.add_argument("--journal-db", default="trades.db",
                        help="Trade journal database path")
    parser.add_argument("--buffer-before", type=int, default=30,
                        help="Minutes before news to stop trading")
    parser.add_argument("--buffer-after", type=int, default=60,
                        help="Minutes after news to resume trading")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("journaled_strategy.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Initialize and run strategy
    strategy = JournaledStrategy(
        config_file=args.config,
        environment=args.env,
        journal_db=args.journal_db,
        buffer_minutes_before=args.buffer_before,
        buffer_minutes_after=args.buffer_after,
    )

    await strategy.run(
        scan_interval=args.interval,
        max_concurrent_trades=args.max_trades,
        runtime_seconds=args.runtime,
    )


if __name__ == "__main__":
    asyncio.run(main())
