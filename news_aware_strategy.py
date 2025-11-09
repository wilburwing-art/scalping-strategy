"""
News-Aware Trading Strategy

Extends the base scalping strategy with economic calendar integration
to avoid trading during high-impact news events.

Usage:
    export TRADING_ECONOMICS_API_KEY="your_key"
    uv run news_aware_strategy.py --env practice
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from scalping_strategy import ScalpingStrategy
from economic_calendar import EconomicCalendar, NewsImpact

logger = logging.getLogger(__name__)


class NewsAwareStrategy(ScalpingStrategy):
    """
    Trading strategy with economic calendar integration.

    Features:
    - Blocks trades 30min before / 60min after high-impact news
    - Logs upcoming critical events at startup
    - Auto-refreshes calendar every hour
    - Graceful fallback if API unavailable
    """

    def __init__(
        self,
        config_file: str,
        environment: str = "practice",
        buffer_minutes_before: int = 30,
        buffer_minutes_after: int = 60,
    ):
        """
        Args:
            config_file: Path to OANDA config file
            environment: "practice" or "live"
            buffer_minutes_before: Minutes before news to stop trading
            buffer_minutes_after: Minutes after news to resume trading
        """
        super().__init__(config_file, environment)

        self.buffer_minutes_before = buffer_minutes_before
        self.buffer_minutes_after = buffer_minutes_after

        # Initialize economic calendar
        trading_economics_key = os.getenv("TRADING_ECONOMICS_API_KEY")
        if not trading_economics_key:
            logger.warning(
                "⚠️  TRADING_ECONOMICS_API_KEY not set - news filtering DISABLED"
            )
            logger.warning(
                "   Trading during news events is extremely risky!"
            )
            self.economic_calendar = None
        else:
            self.economic_calendar = EconomicCalendar(api_key=trading_economics_key)
            logger.info("✓ Economic calendar integration enabled")

        # Tracking
        self.trades_blocked_by_news = 0
        self.last_news_refresh = None

    async def fetch_news_calendar(self):
        """
        Fetch upcoming economic events.
        Call this once at startup and then hourly.
        """
        if not self.economic_calendar:
            return

        try:
            events = await self.economic_calendar.fetch_upcoming_events(
                hours_ahead=24,
                min_impact=NewsImpact.MEDIUM,
            )

            logger.info(f"📅 Fetched {len(events)} upcoming economic events (next 24h)")

            # Log critical events
            critical = self.economic_calendar.get_upcoming_critical_events(hours_ahead=48)
            if critical:
                logger.warning(f"\n⚠️  {len(critical)} CRITICAL events in next 48 hours:")
                for event in critical:
                    logger.warning(f"   {event}")
                logger.warning("")

            self.last_news_refresh = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to fetch economic calendar: {e}")
            logger.warning("Will continue trading without news filtering")

    def is_safe_to_trade_instrument(self, instrument: str) -> tuple[bool, Optional[str]]:
        """
        Check if it's safe to trade this instrument right now.

        Returns:
            (is_safe, reason)
                is_safe: True if safe to trade
                reason: Explanation if not safe
        """
        if not self.economic_calendar:
            # No calendar = allow trading (with earlier warning)
            return True, None

        is_safe, blocking_event = self.economic_calendar.is_safe_to_trade(
            instrument=instrument,
            current_time=None,  # Uses UTC now
            buffer_minutes_before=self.buffer_minutes_before,
            buffer_minutes_after=self.buffer_minutes_after,
        )

        if not is_safe and blocking_event:
            minutes_until = (blocking_event.timestamp - datetime.utcnow()).total_seconds() / 60
            reason = (
                f"{blocking_event.event_name} ({blocking_event.country}) "
                f"{blocking_event.impact.value.upper()} in {minutes_until:.0f} min"
            )
            return False, reason

        return True, None

    async def scan_for_opportunities(self):
        """
        Enhanced opportunity scanning with news filtering.

        Overrides base class method to add news checks.
        """
        try:
            # Refresh news calendar if needed
            await self._refresh_news_if_needed()

            # Get tradeable instruments
            instruments = self.get_tradeable_instruments()
            logger.info(f"Scanning {len(instruments)} instruments...")

            opportunities = []

            for instrument in instruments:
                try:
                    # NEWS CHECK: Skip if news event nearby
                    is_safe, reason = self.is_safe_to_trade_instrument(instrument.name)
                    if not is_safe:
                        logger.info(f"⏸️  Skipping {instrument.name} - News: {reason}")
                        self.trades_blocked_by_news += 1
                        continue

                    # Continue with normal analysis
                    candles = self.get_instrument_candles(instrument.name, count=100)

                    if not candles or len(candles) < 50:
                        continue

                    indicators = self.calculate_indicators(candles)

                    if not indicators:
                        continue

                    # Check if tradeable
                    if self.is_instrument_tradeable(instrument, indicators):
                        opportunities.append({
                            "instrument": instrument.name,
                            "indicators": indicators,
                            "candles": candles,
                        })
                        logger.info(
                            f"✓ Opportunity: {instrument.name} - "
                            f"RSI: {indicators['rsi']:.1f}, "
                            f"ATR: {indicators['atr']:.5f}"
                        )

                except Exception as e:
                    logger.error(f"Error scanning {instrument.name}: {e}")
                    continue

            return opportunities

        except Exception as e:
            logger.error(f"Error in scan_for_opportunities: {e}")
            return []

    async def _refresh_news_if_needed(self):
        """Refresh news calendar if it's been over an hour"""
        if not self.economic_calendar:
            return

        if self.last_news_refresh is None:
            # First run
            await self.fetch_news_calendar()
            return

        # Refresh every hour
        time_since_refresh = (datetime.utcnow() - self.last_news_refresh).total_seconds()
        if time_since_refresh > 3600:  # 1 hour
            logger.info("⟳ Refreshing economic calendar...")
            await self.fetch_news_calendar()

    async def run(
        self,
        scan_interval: int = 300,
        max_concurrent_trades: int = 3,
        runtime_seconds: Optional[int] = None,
    ):
        """
        Main trading loop with news integration.

        Args:
            scan_interval: Seconds between scans
            max_concurrent_trades: Maximum positions at once
            runtime_seconds: Run for X seconds then exit (None = forever)
        """
        logger.info("\n" + "="*60)
        logger.info("📰 NEWS-AWARE FOREX TRADING STRATEGY")
        logger.info("="*60)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Scan interval: {scan_interval}s")
        logger.info(f"Max concurrent trades: {max_concurrent_trades}")
        logger.info(f"News buffer: -{self.buffer_minutes_before}min / +{self.buffer_minutes_after}min")
        logger.info("="*60 + "\n")

        # Pre-fetch economic calendar
        logger.info("Fetching economic calendar...")
        await self.fetch_news_calendar()

        # Set parameters
        self.scan_interval = scan_interval
        self.max_concurrent_trades = max_concurrent_trades

        start_time = datetime.now()

        try:
            iteration = 0

            while True:
                iteration += 1
                logger.info(f"\n--- Scan #{iteration} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

                # Check runtime limit
                if runtime_seconds:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= runtime_seconds:
                        logger.info(f"Runtime limit reached ({runtime_seconds}s)")
                        break

                # Scan for opportunities
                opportunities = await self.scan_for_opportunities()

                # Get active trades
                active_trades = self.get_active_trades()
                logger.info(f"Active trades: {len(active_trades)}/{self.max_concurrent_trades}")

                # Execute trades if room available
                if opportunities and len(active_trades) < self.max_concurrent_trades:
                    for opp in opportunities[:self.max_concurrent_trades - len(active_trades)]:
                        try:
                            # Final news check before execution
                            is_safe, reason = self.is_safe_to_trade_instrument(opp["instrument"])
                            if not is_safe:
                                logger.warning(f"News event appeared - skipping {opp['instrument']}: {reason}")
                                self.trades_blocked_by_news += 1
                                continue

                            # Execute trade
                            await self.execute_trade(
                                opp["instrument"],
                                opp["indicators"],
                                opp["candles"]
                            )

                        except Exception as e:
                            logger.error(f"Failed to execute trade: {e}")

                # Monitor active trades
                if active_trades:
                    self.monitor_active_trades()

                # Log statistics
                logger.info(f"📊 Trades blocked by news: {self.trades_blocked_by_news}")

                # Sleep until next scan
                logger.info(f"Next scan in {scan_interval}s...")
                await asyncio.sleep(scan_interval)

        except KeyboardInterrupt:
            logger.info("\n\n⏹️  Shutting down gracefully...")
        except Exception as e:
            logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("\nCleaning up...")

        # Close economic calendar
        if self.economic_calendar:
            await self.economic_calendar.close()
            logger.info("✓ Economic calendar closed")

        # Close any open positions (optional - usually keep them)
        active_trades = self.get_active_trades()
        if active_trades:
            logger.warning(f"⚠️  {len(active_trades)} trades still open")
            logger.warning("   Positions will remain active after exit")

        logger.info(f"\n📊 Session Statistics:")
        logger.info(f"   Trades blocked by news: {self.trades_blocked_by_news}")

        logger.info("\n✓ Shutdown complete")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="News-Aware Forex Trading Strategy")
    parser.add_argument("--config", default="v20.conf", help="OANDA config file")
    parser.add_argument("--env", default="practice", choices=["practice", "live"],
                        help="Trading environment")
    parser.add_argument("--interval", type=int, default=300,
                        help="Scan interval in seconds")
    parser.add_argument("--max-trades", type=int, default=3,
                        help="Maximum concurrent trades")
    parser.add_argument("--runtime", type=int, default=None,
                        help="Runtime in seconds (None = forever)")
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
            logging.FileHandler("news_aware_strategy.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Check API key
    if not os.getenv("TRADING_ECONOMICS_API_KEY"):
        logger.warning("\n⚠️  WARNING: TRADING_ECONOMICS_API_KEY not set!")
        logger.warning("   Get free API key at: https://tradingeconomics.com/analytics/api/")
        logger.warning("   News filtering will be DISABLED\n")

    # Initialize and run strategy
    strategy = NewsAwareStrategy(
        config_file=args.config,
        environment=args.env,
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
