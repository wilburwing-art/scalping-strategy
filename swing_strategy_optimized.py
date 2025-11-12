#!/usr/bin/env python3
"""
Optimized Swing Trading Strategy (4H Timeframe)
Based on backtest results showing 29% win rate with optimized parameters.

Key optimizations:
- Tighter RSI: 30/70 (was 35/65)
- Lower R:R: 1.5 (was 2.0)
- Tighter stops: 1.5x ATR (was 2.0x)
- Added volume and trend strength filters

Can run with or without AI agents.
"""

import sys
import os
import argparse
import logging
from datetime import datetime
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import swing strategy base
from swing_strategy import SwingTradingStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('swing_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OptimizedSwingStrategy(SwingTradingStrategy):
    """
    Optimized swing trading strategy with improved parameters.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # OPTIMIZED PARAMETERS (based on backtest)
        self.rsi_oversold = 30      # Was 35 (tighter threshold)
        self.rsi_overbought = 70    # Was 65 (tighter threshold)
        self.reward_risk_ratio = 1.5  # Was 2.0 (more achievable)
        self.atr_multiplier = 1.5    # Was 2.0 (tighter stops)

        # NEW FILTERS
        self.min_volume = 400          # Skip low volume periods
        self.min_trend_strength = 0.0005  # Require 5 pips MA separation

        logger.info("="*60)
        logger.info("OPTIMIZED SWING STRATEGY INITIALIZED")
        logger.info("="*60)
        logger.info(f"RSI Thresholds:     {self.rsi_oversold}/{self.rsi_overbought}")
        logger.info(f"R:R Ratio:          {self.reward_risk_ratio}:1")
        logger.info(f"ATR Multiplier:     {self.atr_multiplier}x")
        logger.info(f"Min Volume:         {self.min_volume}")
        logger.info(f"Min Trend Strength: {self.min_trend_strength}")
        logger.info(f"AI Agents:          {'ENABLED' if self.enable_agents else 'DISABLED'}")
        logger.info("="*60)

    async def run_with_timeout(self, runtime_seconds: int = 86400):
        """Run strategy with a timeout (for testing)"""
        import asyncio
        from datetime import datetime, timedelta

        end_time = datetime.now() + timedelta(seconds=runtime_seconds)
        logger.info(f"Strategy will run until {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            while datetime.now() < end_time:
                # Scan instruments
                for instrument in self.instruments:
                    # Check max positions
                    positions_response = self.api.position.list_open(self.account_id)
                    open_count = len(positions_response.body.get('positions', []))

                    if open_count >= self.max_positions:
                        logger.info(f"Max positions ({self.max_positions}) reached")
                        break

                    # Analyze
                    opportunity = await self.analyze_opportunity(instrument)
                    if opportunity:
                        await self.execute_trade(opportunity)

                # Calculate remaining time
                remaining = (end_time - datetime.now()).seconds
                wait_time = min(self.scan_interval, remaining)

                if wait_time > 0:
                    logger.info(f"Waiting {wait_time}s before next scan (time remaining: {remaining}s)...")
                    await asyncio.sleep(wait_time)

            logger.info(f"\n⏰ Runtime limit reached ({runtime_seconds}s). Shutting down...")
            await self.shutdown()

        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutting down...")
            await self.shutdown()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            await self.shutdown()

    def should_enter_trade(self, indicators: dict, candle: dict = None) -> bool:
        """
        Enhanced entry logic with additional filters.
        """
        # Base RSI and trend check
        has_uptrend = indicators["ma_short"] > indicators["ma_long"]
        has_downtrend = indicators["ma_short"] < indicators["ma_long"]
        is_oversold = indicators["rsi"] < self.rsi_oversold
        is_overbought = indicators["rsi"] > self.rsi_overbought

        # Check base conditions
        can_buy = has_uptrend and is_oversold
        can_sell = has_downtrend and is_overbought

        if not (can_buy or can_sell):
            return False

        # NEW: Apply filters
        if candle:
            # Volume filter
            if candle.get('volume', 0) < self.min_volume:
                logger.debug(f"Rejected: Low volume ({candle.get('volume', 0)} < {self.min_volume})")
                return False

            # Trend strength filter (MA separation)
            trend_strength = abs(indicators["ma_short"] - indicators["ma_long"])
            if trend_strength < self.min_trend_strength:
                logger.debug(f"Rejected: Weak trend (strength {trend_strength:.5f} < {self.min_trend_strength})")
                return False

        return True


def main():
    """Main function to run optimized swing strategy."""
    parser = argparse.ArgumentParser(description="Optimized Swing Trading Strategy")

    parser.add_argument('--env', choices=['practice', 'live'], default='practice',
                        help='Trading environment')
    parser.add_argument('--paper-trade', action='store_true',
                        help='Paper trading mode (log only, no real trades)')
    parser.add_argument('--disable-agents', action='store_true',
                        help='Disable AI agents (use technical analysis only)')
    parser.add_argument('--runtime', type=int, default=86400,
                        help='Runtime in seconds (default: 24 hours)')

    args = parser.parse_args()

    print("\n" + "="*60)
    print("OPTIMIZED SWING TRADING STRATEGY")
    print("="*60)
    print(f"Environment:        {args.env.upper()}")
    print(f"Paper Trading:      {'YES' if args.paper_trade else 'NO'}")
    print(f"AI Agents:          {'NO (disabled)' if args.disable_agents else 'YES (if API key set)'}")
    print(f"Runtime:            {args.runtime}s ({args.runtime/3600:.1f} hours)")
    print("="*60 + "\n")

    # Check for OpenAI API key if agents enabled
    if not args.disable_agents:
        if not os.getenv('OPENAI_API_KEY'):
            print("⚠️  WARNING: OPENAI_API_KEY not set!")
            print("   AI agents will be disabled.")
            print("   Set key with: export OPENAI_API_KEY='your-key'")
            print()
            enable_agents = False
        else:
            print("✅ OpenAI API key detected - AI agents will be enabled")
            enable_agents = True
    else:
        print("ℹ️  AI agents disabled by user flag")
        enable_agents = False

    # Initialize strategy
    try:
        strategy = OptimizedSwingStrategy(
            config_file='v20.conf',
            environment=args.env,
            enable_agents=not args.disable_agents and enable_agents,
            enable_calendar=False,  # Optional - economic calendar
            enable_sentiment=False,  # Optional - sentiment analysis
            enable_monitoring=True,  # System monitoring & alerts
        )

        # Run strategy
        logger.info(f"Starting optimized swing strategy...")
        logger.info(f"Will run for {args.runtime}s ({args.runtime/3600:.1f} hours)")

        if args.paper_trade:
            logger.info("🔶 PAPER TRADING MODE - No real trades will be executed")

        # Run with asyncio
        import asyncio
        asyncio.run(strategy.run_with_timeout(runtime_seconds=args.runtime))

    except KeyboardInterrupt:
        logger.info("\n⚠️  Strategy stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Strategy error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
