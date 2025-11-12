"""
Multi-Timeframe Data Fetching Module

Provides parallel fetching of multiple timeframes for comprehensive technical analysis.
This is a critical Phase 2 component - agents need multi-timeframe data to work properly.

Usage:
    from multi_timeframe_data import MultiTimeframeDataProvider

    provider = MultiTimeframeDataProvider(api_context, account_id)
    data = await provider.get_multi_timeframe_data("EUR_USD")

    # Access different timeframes
    print(f"5m candles: {len(data['5m'])}")
    print(f"1H candles: {len(data['1H'])}")
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from v20 import Context

logger = logging.getLogger(__name__)


class MultiTimeframeDataProvider:
    """
    Fetches and manages multi-timeframe data from OANDA API.

    Features:
    - Parallel fetching of multiple timeframes (faster than sequential)
    - Configurable timeframe selection
    - Bid/ask pricing (more accurate than midpoint)
    - Error handling and fallbacks
    - Caching to reduce API calls

    Timeframes supported:
    - 1m (M1): Scalping/noise filtering
    - 5m (M5): Primary scalping timeframe
    - 15m (M15): Short-term trend confirmation
    - 1H (H1): Medium-term trend
    - 4H (H4): Major trend direction
    """

    # Timeframe configurations: (OANDA_code, candle_count, description)
    TIMEFRAMES = {
        "1m": ("M1", 100, "Last ~100 minutes - scalping/noise"),
        "5m": ("M5", 100, "Last ~8 hours - primary signals"),
        "15m": ("M15", 100, "Last ~25 hours - short-term trend"),
        "1H": ("H1", 100, "Last ~4 days - medium-term trend"),
        "4H": ("H4", 100, "Last ~17 days - major trend"),
    }

    def __init__(
        self,
        api_context: Context,
        account_id: str,
        enable_caching: bool = True,
        cache_duration_seconds: int = 60,
    ):
        """
        Args:
            api_context: OANDA v20 API context
            account_id: OANDA account ID
            enable_caching: Enable caching to reduce API calls
            cache_duration_seconds: How long to cache data (default 60s)
        """
        self.ctx = api_context
        self.account_id = account_id
        self.enable_caching = enable_caching
        self.cache_duration_seconds = cache_duration_seconds

        # Cache storage: {instrument: {timeframe: (data, timestamp)}}
        self._cache: Dict[str, Dict[str, Tuple[List, datetime]]] = {}

    async def get_multi_timeframe_data(
        self,
        instrument: str,
        timeframes: Optional[List[str]] = None,
        use_bid_ask: bool = True,
    ) -> Dict[str, List]:
        """
        Fetch multiple timeframes in parallel.

        Args:
            instrument: e.g., "EUR_USD"
            timeframes: List of timeframes to fetch (None = all)
            use_bid_ask: Use bid/ask prices (True) vs midpoint (False)

        Returns:
            Dictionary mapping timeframe to list of candles:
            {
                "1m": [candle1, candle2, ...],
                "5m": [candle1, candle2, ...],
                "15m": [candle1, candle2, ...],
                "1H": [candle1, candle2, ...],
                "4H": [candle1, candle2, ...],
            }
        """
        if timeframes is None:
            timeframes = list(self.TIMEFRAMES.keys())

        # Check cache first
        if self.enable_caching:
            cached_data = self._get_from_cache(instrument, timeframes)
            if cached_data is not None:
                logger.debug(f"Using cached data for {instrument}")
                return cached_data

        logger.info(f"Fetching {len(timeframes)} timeframes for {instrument} in parallel...")

        # Create async tasks for each timeframe
        tasks = []
        for tf in timeframes:
            if tf not in self.TIMEFRAMES:
                logger.warning(f"Unknown timeframe: {tf}, skipping")
                continue

            oanda_code, count, _ = self.TIMEFRAMES[tf]
            task = self._fetch_candles_async(
                instrument,
                oanda_code,
                count,
                use_bid_ask
            )
            tasks.append((tf, task))

        # Execute all fetches in parallel
        results = {}
        fetch_results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )

        # Process results
        for (tf, _), result in zip(tasks, fetch_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {tf} for {instrument}: {result}")
                results[tf] = []
            else:
                results[tf] = result
                logger.debug(f"Fetched {len(result)} {tf} candles for {instrument}")

        # Update cache
        if self.enable_caching:
            self._update_cache(instrument, results)

        return results

    async def _fetch_candles_async(
        self,
        instrument: str,
        granularity: str,
        count: int,
        use_bid_ask: bool,
    ) -> List:
        """
        Fetch candles for a single timeframe (async).

        Args:
            instrument: e.g., "EUR_USD"
            granularity: OANDA granularity code (M1, M5, H1, etc.)
            count: Number of candles to fetch
            use_bid_ask: Use bid/ask (True) vs midpoint (False)

        Returns:
            List of candle objects
        """
        # Run synchronous OANDA API call in executor to avoid blocking
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                # Determine price type
                price_type = "BA" if use_bid_ask else "M"

                response = self.ctx.instrument.candles(
                    instrument,
                    count=count,
                    granularity=granularity,
                    price=price_type
                )

                candles = response.get("candles", [])

                # Log if we got incomplete data
                if len(candles) < count:
                    logger.warning(
                        f"Only got {len(candles)}/{count} {granularity} candles for {instrument}"
                    )

                return candles

            except Exception as e:
                logger.error(f"Unexpected error fetching {granularity} for {instrument}: {e}")
                raise

        # Run in thread pool executor (OANDA SDK is synchronous)
        return await loop.run_in_executor(None, _fetch)

    def get_single_timeframe(
        self,
        instrument: str,
        timeframe: str,
        use_bid_ask: bool = True,
    ) -> List:
        """
        Synchronous fetch of single timeframe (for compatibility).

        Args:
            instrument: e.g., "EUR_USD"
            timeframe: e.g., "5m", "1H"
            use_bid_ask: Use bid/ask prices

        Returns:
            List of candles
        """
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        oanda_code, count, _ = self.TIMEFRAMES[timeframe]
        price_type = "BA" if use_bid_ask else "M"

        try:
            response = self.ctx.instrument.candles(
                instrument,
                count=count,
                granularity=oanda_code,
                price=price_type
            )
            return response.get("candles", [])
        except Exception as e:
            logger.error(f"Error fetching {timeframe} for {instrument}: {e}")
            return []

    def _get_from_cache(
        self,
        instrument: str,
        timeframes: List[str],
    ) -> Optional[Dict[str, List]]:
        """
        Get data from cache if available and fresh.

        Returns:
            Cached data if available and fresh, None otherwise
        """
        if instrument not in self._cache:
            return None

        instrument_cache = self._cache[instrument]
        now = datetime.now()

        # Check if all requested timeframes are cached and fresh
        result = {}
        for tf in timeframes:
            if tf not in instrument_cache:
                return None  # Missing timeframe

            data, timestamp = instrument_cache[tf]
            age_seconds = (now - timestamp).total_seconds()

            if age_seconds > self.cache_duration_seconds:
                return None  # Stale data

            result[tf] = data

        return result

    def _update_cache(self, instrument: str, data: Dict[str, List]):
        """Update cache with fetched data"""
        if instrument not in self._cache:
            self._cache[instrument] = {}

        now = datetime.now()
        for tf, candles in data.items():
            self._cache[instrument][tf] = (candles, now)

    def clear_cache(self, instrument: Optional[str] = None):
        """
        Clear cache for instrument (or all if None).

        Args:
            instrument: Instrument to clear (None = clear all)
        """
        if instrument:
            if instrument in self._cache:
                del self._cache[instrument]
                logger.debug(f"Cleared cache for {instrument}")
        else:
            self._cache.clear()
            logger.debug("Cleared all cache")

    def format_for_agents(self, data: Dict[str, List]) -> Dict:
        """
        Format multi-timeframe data for agent consumption.

        Converts raw OANDA candles to structured format that agents expect.

        Args:
            data: Dictionary of timeframe -> candles

        Returns:
            Formatted dictionary with OHLCV data:
            {
                "1m": {"open": [...], "high": [...], "low": [...], "close": [...], "volume": [...]},
                "5m": {...},
                ...
            }
        """
        formatted = {}

        for timeframe, candles in data.items():
            if not candles:
                formatted[timeframe] = {
                    "open": [],
                    "high": [],
                    "low": [],
                    "close": [],
                    "volume": [],
                    "time": [],
                }
                continue

            # Extract OHLCV data
            # Note: Using bid/ask average for now, could separate bid/ask later
            ohlcv = {
                "time": [],
                "open": [],
                "high": [],
                "low": [],
                "close": [],
                "volume": [],
            }

            for candle in candles:
                ohlcv["time"].append(candle.time)
                ohlcv["volume"].append(int(candle.volume))

                # Use bid/ask average if available, otherwise midpoint
                if hasattr(candle, 'bid') and candle.bid:
                    ohlcv["open"].append((float(candle.bid.o) + float(candle.ask.o)) / 2)
                    ohlcv["high"].append((float(candle.bid.h) + float(candle.ask.h)) / 2)
                    ohlcv["low"].append((float(candle.bid.l) + float(candle.ask.l)) / 2)
                    ohlcv["close"].append((float(candle.bid.c) + float(candle.ask.c)) / 2)
                elif hasattr(candle, 'mid') and candle.mid:
                    ohlcv["open"].append(float(candle.mid.o))
                    ohlcv["high"].append(float(candle.mid.h))
                    ohlcv["low"].append(float(candle.mid.l))
                    ohlcv["close"].append(float(candle.mid.c))
                else:
                    logger.warning(f"Candle missing price data: {candle}")
                    continue

            formatted[timeframe] = ohlcv

        return formatted

    def get_current_price(self, instrument: str, use_bid_ask: bool = True) -> Optional[Dict]:
        """
        Get current bid/ask or midpoint price for instrument.

        Args:
            instrument: e.g., "EUR_USD"
            use_bid_ask: Return bid/ask (True) vs midpoint (False)

        Returns:
            Dictionary with price info:
            {
                "bid": 1.0850,
                "ask": 1.0852,
                "spread": 0.0002,
                "midpoint": 1.0851,
                "time": "2025-11-09T20:30:00Z"
            }
        """
        try:
            response = self.ctx.pricing.get(
                self.account_id,
                instruments=instrument
            )

            prices = response.get("prices", [])
            if not prices:
                logger.warning(f"No prices returned for {instrument}")
                return None

            price = prices[0]

            bid = float(price.bids[0].price) if price.bids else None
            ask = float(price.asks[0].price) if price.asks else None

            if bid is None or ask is None:
                logger.warning(f"Missing bid/ask for {instrument}")
                return None

            return {
                "instrument": instrument,
                "bid": bid,
                "ask": ask,
                "spread": ask - bid,
                "midpoint": (bid + ask) / 2,
                "time": price.time,
            }

        except Exception as e:
            logger.error(f"Error getting current price for {instrument}: {e}")
            return None


# Example usage and testing
async def test_multi_timeframe():
    """Test multi-timeframe data fetching"""
    import configparser

    # Load config
    config = configparser.ConfigParser()
    config.read("v20.conf")

    ctx = Context(
        config["practice"]["hostname"],
        config["practice"]["token"],
        application="MultiTimeframeTest"
    )
    account_id = config["practice"]["account_id"]

    # Create provider
    provider = MultiTimeframeDataProvider(ctx, account_id)

    # Test parallel fetching
    print("\n=== Testing Multi-Timeframe Parallel Fetch ===")
    data = await provider.get_multi_timeframe_data("EUR_USD")

    for tf, candles in data.items():
        print(f"{tf}: {len(candles)} candles")

    # Test formatting for agents
    print("\n=== Testing Agent Format ===")
    formatted = provider.format_for_agents(data)

    for tf, ohlcv in formatted.items():
        print(f"{tf}: {len(ohlcv['close'])} close prices")
        if ohlcv['close']:
            print(f"  Latest close: {ohlcv['close'][-1]:.5f}")

    # Test current price
    print("\n=== Testing Current Price ===")
    current = provider.get_current_price("EUR_USD")
    if current:
        print(f"Bid: {current['bid']:.5f}")
        print(f"Ask: {current['ask']:.5f}")
        print(f"Spread: {current['spread']:.5f} ({current['spread']*10000:.1f} pips)")

    print("\n✅ All tests complete")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_multi_timeframe())
