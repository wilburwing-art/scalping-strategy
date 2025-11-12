"""
Sentiment-Aware Trading Strategy

Integrates social sentiment analysis with the multi-agent trading system.

Usage:
    export OPENAI_API_KEY="sk-..."
    export TWITTER_BEARER_TOKEN="..."  # Optional
    export REDDIT_CLIENT_ID="..."      # Optional
    export REDDIT_CLIENT_SECRET="..."  # Optional

    uv run sentiment_aware_strategy.py --env practice
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from journaled_strategy import JournaledStrategy
from sentiment_analyzer import SentimentAnalyzer, SentimentData
from trade_journal import TradeJournalEntry

logger = logging.getLogger(__name__)


class SentimentAwareStrategy(JournaledStrategy):
    """
    Trading strategy enhanced with social sentiment analysis.

    Features:
    - Fetches sentiment from Twitter, Reddit, StockTwits
    - Integrates sentiment with AI agent decisions
    - Uses sentiment for:
      1. Confirmation: High bullish sentiment + bullish technicals = higher confidence
      2. Contrarian signals: Extreme sentiment = fade the crowd
      3. Risk management: High conviction sentiment can adjust position size
    - Logs sentiment scores in trade journal
    """

    def __init__(
        self,
        config_file: str,
        environment: str = "practice",
        enable_sentiment: bool = True,
        sentiment_weight: float = 0.15,  # 15% weight in final decision
        contrarian_mode: bool = False,   # Fade extreme sentiment vs follow it
        **kwargs
    ):
        """
        Args:
            config_file: Path to OANDA config file
            environment: "practice" or "live"
            enable_sentiment: Enable sentiment analysis
            sentiment_weight: Weight of sentiment in decision (0.0-1.0)
            contrarian_mode: If True, fade extreme sentiment; if False, follow it
            **kwargs: Additional args for parent classes
        """
        super().__init__(config_file, environment, **kwargs)

        self.sentiment_weight = sentiment_weight
        self.contrarian_mode = contrarian_mode

        # Initialize sentiment analyzer
        if enable_sentiment:
            openai_key = os.getenv("OPENAI_API_KEY")
            twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
            reddit_id = os.getenv("REDDIT_CLIENT_ID")
            reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")
            stocktwits_token = os.getenv("STOCKTWITS_TOKEN")

            if not openai_key:
                logger.warning("OPENAI_API_KEY not set - sentiment analysis DISABLED")
                self.sentiment_analyzer = None
            else:
                self.sentiment_analyzer = SentimentAnalyzer(
                    openai_key=openai_key,
                    twitter_bearer_token=twitter_bearer,
                    reddit_client_id=reddit_id,
                    reddit_client_secret=reddit_secret,
                    stocktwits_token=stocktwits_token,
                    cache_duration_minutes=15,  # Cache for 15 min
                )
                logger.info(f"✓ Sentiment analysis enabled (weight: {sentiment_weight:.1%})")
                if contrarian_mode:
                    logger.info("  📊 Mode: CONTRARIAN (fade extreme sentiment)")
                else:
                    logger.info("  📊 Mode: MOMENTUM (follow sentiment)")
        else:
            self.sentiment_analyzer = None
            logger.info("Sentiment analysis disabled")

        # Tracking
        self.sentiment_enhanced_trades = 0
        self.sentiment_blocked_trades = 0

    async def analyze_with_sentiment(
        self,
        instrument: str,
        indicators: Dict[str, Any],
        candles: list,
    ) -> tuple[Optional[str], Optional[SentimentData], float]:
        """
        Analyze trade opportunity with sentiment data.

        Returns:
            (direction, sentiment_data, adjusted_confidence)
        """
        # Determine base direction from indicators
        is_uptrend = indicators["ma_short"] > indicators["ma_long"]
        base_direction = "BUY" if is_uptrend else "SELL"

        # Get sentiment
        sentiment_data = None
        if self.sentiment_analyzer:
            try:
                sentiment_data = await self.sentiment_analyzer.get_sentiment(
                    instrument,
                    lookback_hours=4,
                )
            except Exception as e:
                logger.error(f"Failed to fetch sentiment: {e}")

        # Calculate adjusted confidence
        base_confidence = 0.6  # Baseline from technical indicators

        if sentiment_data and sentiment_data.total_mentions >= 5:
            sentiment_score = sentiment_data.sentiment_score
            sentiment_strength = abs(sentiment_score)

            # Determine if sentiment aligns with direction
            sentiment_bullish = sentiment_score > 0.2
            sentiment_bearish = sentiment_score < -0.2

            direction_match = (
                (base_direction == "BUY" and sentiment_bullish) or
                (base_direction == "SELL" and sentiment_bearish)
            )

            # Apply sentiment weight
            if self.contrarian_mode:
                # Contrarian: Fade extreme sentiment
                if sentiment_data.is_contrarian_signal:
                    # Very extreme sentiment = fade it
                    if direction_match:
                        # Sentiment agrees with technicals, but it's TOO extreme
                        adjustment = -sentiment_strength * self.sentiment_weight
                        logger.info(
                            f"📉 Contrarian signal: Sentiment too extreme "
                            f"({sentiment_score:+.2f}), reducing confidence"
                        )
                    else:
                        # Sentiment opposes technicals, and it's extreme
                        # This is our contrarian setup!
                        adjustment = +sentiment_strength * self.sentiment_weight * 1.5
                        logger.info(
                            f"📈 Contrarian setup: Fading extreme sentiment "
                            f"({sentiment_score:+.2f})"
                        )
                else:
                    # Normal sentiment, use as confirmation
                    adjustment = (sentiment_strength if direction_match else -sentiment_strength) * self.sentiment_weight
            else:
                # Momentum: Follow sentiment
                if sentiment_data.is_high_conviction:
                    # Strong sentiment = higher confidence if aligned
                    if direction_match:
                        adjustment = +sentiment_strength * self.sentiment_weight * 1.5
                        logger.info(
                            f"📈 High conviction sentiment confirms signal "
                            f"({sentiment_score:+.2f})"
                        )
                    else:
                        adjustment = -sentiment_strength * self.sentiment_weight * 1.5
                        logger.warning(
                            f"📉 Sentiment conflicts with technicals "
                            f"({sentiment_score:+.2f})"
                        )
                else:
                    # Normal sentiment
                    adjustment = (sentiment_strength if direction_match else -sentiment_strength) * self.sentiment_weight

            adjusted_confidence = base_confidence + adjustment
        else:
            adjusted_confidence = base_confidence
            if sentiment_data:
                logger.debug(
                    f"Low mention volume ({sentiment_data.total_mentions}), "
                    f"not using sentiment"
                )

        return base_direction, sentiment_data, adjusted_confidence

    async def execute_trade(
        self,
        instrument: str,
        indicators: Dict[str, Any],
        candles: list,
        agent_recommendation: Optional[Any] = None,
    ):
        """
        Execute trade with sentiment analysis integration.

        Overrides parent to add sentiment analysis.
        """
        try:
            # Analyze with sentiment
            direction, sentiment_data, confidence = await self.analyze_with_sentiment(
                instrument,
                indicators,
                candles,
            )

            # Apply confidence threshold
            min_confidence = 0.55
            if confidence < min_confidence:
                logger.info(
                    f"⏸️  Skipping {instrument} - Confidence too low "
                    f"({confidence:.1%} < {min_confidence:.1%})"
                )
                self.sentiment_blocked_trades += 1
                return None

            # Get current price
            current_price = float(candles[-1].mid.c)

            # Calculate position size
            account_balance = self.get_account_balance()
            position_size = self.calculate_position_size(
                account_balance,
                instrument,
                indicators
            )

            # Adjust position size based on sentiment conviction
            if sentiment_data and sentiment_data.is_high_conviction:
                # High conviction sentiment = 1.2x position size (capped by risk limits)
                position_size = int(position_size * 1.2)
                logger.info("  📊 High conviction sentiment: +20% position size")
                self.sentiment_enhanced_trades += 1

            # Calculate stop loss and take profit
            atr = indicators["atr"]
            stop_distance = atr * 1.5

            if direction == "BUY":
                stop_loss = current_price - stop_distance
                take_profit = current_price + (stop_distance * self.reward_risk_ratio)
            else:
                stop_loss = current_price + stop_distance
                take_profit = current_price - (stop_distance * self.reward_risk_ratio)

            # Create trade ID
            trade_id = f"{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Log entry to journal with sentiment data
            entry_time = datetime.utcnow()
            session = self._get_current_session(entry_time)

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

                # Sentiment data
                sentiment_score=sentiment_data.sentiment_score if sentiment_data else None,
                sentiment_volume=sentiment_data.total_mentions if sentiment_data else None,

                # Agent/confidence
                overall_confidence=confidence,

                # Risk management
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=self.reward_risk_ratio,
                position_size_pct=(position_size * current_price / account_balance) * 100,

                # Metadata
                strategy_version="3.0-sentiment",
                environment=self.environment,
                notes=f"Sentiment: {sentiment_data}" if sentiment_data else None,
            )

            # Log to journal
            self.journal.log_entry(journal_entry)

            # Store for exit tracking
            self._active_journal_entries[trade_id] = journal_entry

            logger.info(
                f"🎯 Trade executed: {direction} {position_size} {instrument} @ {current_price:.5f} "
                f"(Confidence: {confidence:.1%}, SL: {stop_loss:.5f}, TP: {take_profit:.5f})"
            )

            return trade_id

        except Exception as e:
            logger.error(f"Failed to execute trade: {e}", exc_info=True)
            return None

    async def run(
        self,
        scan_interval: int = 300,
        max_concurrent_trades: int = 3,
        runtime_seconds: Optional[int] = None,
    ):
        """
        Main trading loop with sentiment analysis.

        Args:
            scan_interval: Seconds between scans
            max_concurrent_trades: Maximum positions at once
            runtime_seconds: Run for X seconds then exit (None = forever)
        """
        logger.info("\n" + "="*60)
        logger.info("📊 SENTIMENT-AWARE FOREX TRADING STRATEGY")
        logger.info("="*60)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Journal: {self.journal.db_path}")
        logger.info(f"Sentiment: {'Enabled' if self.sentiment_analyzer else 'Disabled'}")
        if self.sentiment_analyzer:
            logger.info(f"Sentiment weight: {self.sentiment_weight:.1%}")
            logger.info(f"Mode: {'CONTRARIAN' if self.contrarian_mode else 'MOMENTUM'}")
        logger.info("="*60 + "\n")

        # Run parent strategy
        await super().run(
            scan_interval=scan_interval,
            max_concurrent_trades=max_concurrent_trades,
            runtime_seconds=runtime_seconds,
        )

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("\nCleaning up...")

        # Close sentiment analyzer
        if self.sentiment_analyzer:
            await self.sentiment_analyzer.close()
            logger.info("✓ Sentiment analyzer closed")

        # Log statistics
        logger.info(f"\n📊 Sentiment Statistics:")
        logger.info(f"   Enhanced trades: {self.sentiment_enhanced_trades}")
        logger.info(f"   Blocked trades: {self.sentiment_blocked_trades}")

        await super().cleanup()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Sentiment-Aware Forex Trading Strategy")
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
    parser.add_argument("--sentiment-weight", type=float, default=0.15,
                        help="Weight of sentiment in decision (0.0-1.0)")
    parser.add_argument("--contrarian", action="store_true",
                        help="Use contrarian mode (fade extreme sentiment)")
    parser.add_argument("--disable-sentiment", action="store_true",
                        help="Disable sentiment analysis")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("sentiment_aware_strategy.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Check API keys
    if not args.disable_sentiment:
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("\n⚠️  WARNING: OPENAI_API_KEY not set!")
            logger.warning("   Sentiment classification will be DISABLED\n")

        if not any([
            os.getenv("TWITTER_BEARER_TOKEN"),
            os.getenv("REDDIT_CLIENT_ID"),
        ]):
            logger.warning("\n⚠️  WARNING: No sentiment data sources configured!")
            logger.warning("   Set TWITTER_BEARER_TOKEN and/or REDDIT_CLIENT_ID/SECRET")
            logger.warning("   StockTwits will still work (public API)\n")

    # Initialize and run strategy
    strategy = SentimentAwareStrategy(
        config_file=args.config,
        environment=args.env,
        journal_db=args.journal_db,
        enable_sentiment=not args.disable_sentiment,
        sentiment_weight=args.sentiment_weight,
        contrarian_mode=args.contrarian,
    )

    await strategy.run(
        scan_interval=args.interval,
        max_concurrent_trades=args.max_trades,
        runtime_seconds=args.runtime,
    )


if __name__ == "__main__":
    asyncio.run(main())
