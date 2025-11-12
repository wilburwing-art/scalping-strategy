"""
Multi-Timeframe Enhanced Scalping Strategy

Extends the base ScalpingStrategy with multi-timeframe analysis capabilities.
This is a critical Phase 2 component that enables agents to perform proper
multi-timeframe analysis.

Key Features:
- Fetches 5 timeframes in parallel (1m, 5m, 15m, 1H, 4H)
- Provides formatted multi-timeframe data to agents
- Caching to reduce API calls
- Bid/ask pricing support

Usage:
    from multi_timeframe_strategy import MultiTimeframeStrategy

    strategy = MultiTimeframeStrategy(config_file="v20.conf", environment="practice")

    # Get multi-timeframe data
    data = await strategy.get_multi_timeframe_data("EUR_USD")

    # Get formatted data for agents
    formatted = strategy.format_multi_timeframe_for_agents(data)
"""

import asyncio
import logging
from typing import Dict, List, Optional
from scalping_strategy import ScalpingStrategy
from multi_timeframe_data import MultiTimeframeDataProvider

logger = logging.getLogger(__name__)


class MultiTimeframeStrategy(ScalpingStrategy):
    """
    Enhanced scalping strategy with multi-timeframe analysis.

    Extends the base ScalpingStrategy class to add multi-timeframe
    data fetching and formatting for agent consumption.
    """

    def __init__(
        self,
        config_file="v20.conf",
        environment="practice",
        enable_caching=True,
        cache_duration_seconds=60,
    ):
        """
        Initialize multi-timeframe strategy.

        Args:
            config_file: Path to OANDA config file
            environment: "practice" or "live"
            enable_caching: Enable data caching
            cache_duration_seconds: Cache TTL
        """
        # Initialize base strategy
        super().__init__(config_file, environment)

        # Initialize multi-timeframe data provider
        self.mtf_provider = MultiTimeframeDataProvider(
            self.ctx,
            self.account_id,
            enable_caching=enable_caching,
            cache_duration_seconds=cache_duration_seconds,
        )

        logger.info("Multi-timeframe strategy initialized")

    async def get_multi_timeframe_data(
        self,
        instrument: str,
        timeframes: Optional[List[str]] = None,
        use_bid_ask: bool = True,
    ) -> Dict[str, List]:
        """
        Fetch multi-timeframe data for an instrument.

        Args:
            instrument: e.g., "EUR_USD"
            timeframes: List of timeframes (None = all)
            use_bid_ask: Use bid/ask prices vs midpoint

        Returns:
            Dictionary mapping timeframe to list of candles
        """
        return await self.mtf_provider.get_multi_timeframe_data(
            instrument,
            timeframes=timeframes,
            use_bid_ask=use_bid_ask,
        )

    def format_multi_timeframe_for_agents(self, data: Dict[str, List]) -> Dict:
        """
        Format multi-timeframe data for agent consumption.

        Args:
            data: Dictionary of timeframe -> candles

        Returns:
            Formatted dictionary with OHLCV data
        """
        return self.mtf_provider.format_for_agents(data)

    def get_current_price(self, instrument: str, use_bid_ask: bool = True) -> Optional[Dict]:
        """
        Get current bid/ask price for instrument.

        Args:
            instrument: e.g., "EUR_USD"
            use_bid_ask: Return bid/ask vs midpoint

        Returns:
            Dictionary with price info (bid, ask, spread, midpoint, time)
        """
        return self.mtf_provider.get_current_price(instrument, use_bid_ask)

    def clear_cache(self, instrument: Optional[str] = None):
        """
        Clear cached data.

        Args:
            instrument: Instrument to clear (None = clear all)
        """
        self.mtf_provider.clear_cache(instrument)

    async def analyze_instrument_multi_timeframe(
        self,
        instrument: str,
        timeframes: Optional[List[str]] = None,
    ) -> Optional[Dict]:
        """
        Analyze an instrument across multiple timeframes.

        This method fetches data from multiple timeframes and performs
        basic analysis. It can be used as input for agent decision making.

        Args:
            instrument: e.g., "EUR_USD"
            timeframes: List of timeframes to analyze (None = all)

        Returns:
            Dictionary with multi-timeframe analysis:
            {
                "instrument": "EUR_USD",
                "current_price": {...},
                "timeframes": {
                    "5m": {"ohlcv": {...}, "indicators": {...}},
                    "1H": {...},
                    ...
                }
            }
        """
        try:
            # Fetch multi-timeframe data
            mtf_data = await self.get_multi_timeframe_data(
                instrument,
                timeframes=timeframes,
                use_bid_ask=True,
            )

            # Get current price
            current_price = self.get_current_price(instrument)

            # Format for agents
            formatted_data = self.format_multi_timeframe_for_agents(mtf_data)

            # Calculate indicators for each timeframe
            analysis = {
                "instrument": instrument,
                "current_price": current_price,
                "timeframes": {},
            }

            for tf, ohlcv in formatted_data.items():
                if not ohlcv["close"]:
                    continue

                # Calculate basic indicators for each timeframe
                indicators = self._calculate_timeframe_indicators(ohlcv)

                analysis["timeframes"][tf] = {
                    "ohlcv": ohlcv,
                    "indicators": indicators,
                }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing {instrument} multi-timeframe: {e}")
            return None

    def _calculate_timeframe_indicators(self, ohlcv: Dict) -> Dict:
        """
        Calculate indicators for a single timeframe.

        Args:
            ohlcv: Dictionary with OHLCV data

        Returns:
            Dictionary with calculated indicators
        """
        import pandas as pd
        import numpy as np

        if not ohlcv["close"] or len(ohlcv["close"]) < 20:
            return {}

        close = np.array(ohlcv["close"])
        high = np.array(ohlcv["high"])
        low = np.array(ohlcv["low"])

        # RSI
        rsi = self._calculate_rsi(close, period=14)

        # Moving averages
        sma_20 = np.mean(close[-20:])
        sma_50 = np.mean(close[-50:]) if len(close) >= 50 else sma_20

        # ATR
        atr = self._calculate_atr(high, low, close, period=14)

        # Trend
        trend = "bullish" if close[-1] > sma_20 else "bearish"
        if abs(close[-1] - sma_20) < atr * 0.5:
            trend = "neutral"

        return {
            "rsi": rsi,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "atr": atr,
            "trend": trend,
            "price": close[-1],
        }

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> float:
        """Calculate Average True Range."""
        if len(high) < period + 1:
            return 0.0

        high_low = high - low
        high_close = np.abs(high[1:] - close[:-1])
        low_close = np.abs(low[1:] - close[:-1])

        true_range = np.maximum(high_low[1:], np.maximum(high_close, low_close))
        atr = np.mean(true_range[-period:])

        return atr


# Example usage
async def example_usage():
    """Example of using the multi-timeframe strategy"""

    # Initialize strategy
    strategy = MultiTimeframeStrategy(
        config_file="v20.conf",
        environment="practice",
        enable_caching=True,
    )

    # Analyze instrument across multiple timeframes
    print("\n=== Multi-Timeframe Analysis ===")
    analysis = await strategy.analyze_instrument_multi_timeframe("EUR_USD")

    if analysis:
        print(f"\nInstrument: {analysis['instrument']}")

        # Current price
        if analysis["current_price"]:
            price = analysis["current_price"]
            print(f"\nCurrent Price:")
            print(f"  Bid: {price['bid']:.5f}")
            print(f"  Ask: {price['ask']:.5f}")
            print(f"  Spread: {price['spread']*10000:.1f} pips")

        # Timeframe analysis
        print(f"\nTimeframe Analysis:")
        for tf, tf_data in analysis["timeframes"].items():
            indicators = tf_data["indicators"]
            if indicators:
                print(f"\n  {tf}:")
                print(f"    Trend: {indicators.get('trend', 'N/A')}")
                print(f"    RSI: {indicators.get('rsi', 0):.1f}")
                print(f"    Price: {indicators.get('price', 0):.5f}")
                print(f"    SMA(20): {indicators.get('sma_20', 0):.5f}")
                print(f"    ATR: {indicators.get('atr', 0):.5f}")

    print("\n✅ Multi-timeframe analysis complete")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
