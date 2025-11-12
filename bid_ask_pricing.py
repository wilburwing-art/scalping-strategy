"""
Bid/Ask Pricing Module

Provides realistic pricing using bid/ask instead of midpoint prices.

Why This Matters:
- Midpoint backtests overstate profitability by 2-5 pips per trade
- Real trades execute at:
  - BID price for SELL orders
  - ASK price for BUY orders
- Spread is built into bid/ask (typically 0.5-3 pips for majors)

Example Impact:
- Midpoint backtest: +7 pips profit
- Bid/ask backtest: +4 pips profit (after 1.5 pip spread each way)
- Reality: Strategy appears profitable but loses money

Usage:
    from bid_ask_pricing import BidAskPricer

    pricer = BidAskPricer()

    # Get execution price
    price = pricer.get_execution_price(candle, direction="BUY")

    # Calculate P&L with realistic prices
    pnl = pricer.calculate_pnl(
        direction="BUY",
        entry_candle=entry,
        exit_candle=exit,
        units=10000
    )
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BidAskPricer:
    """
    Handles bid/ask pricing for realistic trade simulation.

    Provides methods to:
    - Get execution prices (bid for sell, ask for buy)
    - Calculate P&L with realistic pricing
    - Extract bid/ask data from candles
    - Convert bid/ask to midpoint for indicators
    """

    def __init__(self):
        """Initialize bid/ask pricer"""
        pass

    def get_execution_price(self, candle, direction: str, price_type: str = "close") -> float:
        """
        Get execution price from candle based on direction.

        Args:
            candle: OANDA candle object with bid/ask data
            direction: "BUY" or "SELL"
            price_type: "open", "high", "low", or "close"

        Returns:
            Execution price (ask for buy, bid for sell)
        """
        direction = direction.upper()

        if not hasattr(candle, 'bid') or not hasattr(candle, 'ask'):
            logger.warning("Candle missing bid/ask data, falling back to midpoint")
            return self._get_midpoint_price(candle, price_type)

        # Get price field
        price_field = price_type[0].lower()  # 'o', 'h', 'l', 'c'

        try:
            if direction == "BUY":
                # Buy at ask price (higher)
                return float(getattr(candle.ask, price_field))
            elif direction == "SELL":
                # Sell at bid price (lower)
                return float(getattr(candle.bid, price_field))
            else:
                raise ValueError(f"Invalid direction: {direction}")
        except AttributeError as e:
            logger.error(f"Error getting {price_type} price: {e}")
            return self._get_midpoint_price(candle, price_type)

    def _get_midpoint_price(self, candle, price_type: str) -> float:
        """
        Get midpoint price as fallback.

        Args:
            candle: OANDA candle object
            price_type: "open", "high", "low", or "close"

        Returns:
            Midpoint price
        """
        price_field = price_type[0].lower()

        if hasattr(candle, 'mid'):
            return float(getattr(candle.mid, price_field))

        # Last resort: try to calculate from bid/ask
        if hasattr(candle, 'bid') and hasattr(candle, 'ask'):
            bid_price = float(getattr(candle.bid, price_field))
            ask_price = float(getattr(candle.ask, price_field))
            return (bid_price + ask_price) / 2

        raise ValueError("Cannot extract price from candle")

    def get_spread(self, candle, price_type: str = "close") -> float:
        """
        Get spread from candle.

        Args:
            candle: OANDA candle object with bid/ask data
            price_type: "open", "high", "low", or "close"

        Returns:
            Spread (ask - bid)
        """
        if not hasattr(candle, 'bid') or not hasattr(candle, 'ask'):
            logger.warning("Candle missing bid/ask data")
            return 0.0

        price_field = price_type[0].lower()

        try:
            bid = float(getattr(candle.bid, price_field))
            ask = float(getattr(candle.ask, price_field))
            return ask - bid
        except AttributeError:
            return 0.0

    def calculate_pnl(
        self,
        direction: str,
        entry_candle,
        exit_candle,
        units: int,
        pip_location: float = 0.0001,
    ) -> Dict:
        """
        Calculate P&L with realistic bid/ask pricing.

        Args:
            direction: "BUY" or "SELL"
            entry_candle: Entry candle with bid/ask
            exit_candle: Exit candle with bid/ask
            units: Position size
            pip_location: Pip size (0.0001 for most, 0.01 for JPY)

        Returns:
            Dictionary with P&L details:
            {
                "entry_price": 1.0852,
                "exit_price": 1.0857,
                "pips": 5.0,
                "pnl_points": 0.0005,
                "entry_spread": 0.0002,
                "exit_spread": 0.0002,
            }
        """
        direction = direction.upper()

        # Get entry price
        if direction == "BUY":
            # Buy at ask
            entry_price = self.get_execution_price(entry_candle, "BUY", "close")
            # Exit buy (sell) at bid
            exit_price = self.get_execution_price(exit_candle, "SELL", "close")
        else:
            # Sell at bid
            entry_price = self.get_execution_price(entry_candle, "SELL", "close")
            # Exit sell (buy) at ask
            exit_price = self.get_execution_price(exit_candle, "BUY", "close")

        # Calculate P&L
        if direction == "BUY":
            pnl_points = exit_price - entry_price
        else:
            pnl_points = entry_price - exit_price

        pips = pnl_points / pip_location

        # Get spreads
        entry_spread = self.get_spread(entry_candle, "close")
        exit_spread = self.get_spread(exit_candle, "close")

        return {
            "direction": direction,
            "units": units,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pips": pips,
            "pnl_points": pnl_points,
            "entry_spread": entry_spread,
            "exit_spread": exit_spread,
            "entry_spread_pips": entry_spread / pip_location,
            "exit_spread_pips": exit_spread / pip_location,
        }

    def extract_ohlc_bid_ask(self, candles: List, use_average: bool = False) -> Dict:
        """
        Extract OHLC data from bid/ask candles.

        Args:
            candles: List of OANDA candles with bid/ask
            use_average: Use average of bid/ask (True) or just midpoint (False)

        Returns:
            Dictionary with OHLC arrays:
            {
                "open": [...],
                "high": [...],
                "low": [...],
                "close": [...],
                "volume": [...],
                "time": [...],
            }
        """
        ohlc = {
            "time": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
        }

        for candle in candles:
            ohlc["time"].append(candle.time)
            ohlc["volume"].append(int(candle.volume))

            # Get prices
            if use_average and hasattr(candle, 'bid') and hasattr(candle, 'ask'):
                # Average of bid/ask
                o = (float(candle.bid.o) + float(candle.ask.o)) / 2
                h = (float(candle.bid.h) + float(candle.ask.h)) / 2
                l = (float(candle.bid.l) + float(candle.ask.l)) / 2
                c = (float(candle.bid.c) + float(candle.ask.c)) / 2
            elif hasattr(candle, 'mid'):
                # Midpoint
                o = float(candle.mid.o)
                h = float(candle.mid.h)
                l = float(candle.mid.l)
                c = float(candle.mid.c)
            else:
                logger.warning("Cannot extract OHLC from candle")
                continue

            ohlc["open"].append(o)
            ohlc["high"].append(h)
            ohlc["low"].append(l)
            ohlc["close"].append(c)

        return ohlc

    def compare_midpoint_vs_bidask(
        self,
        direction: str,
        entry_candle,
        exit_candle,
        units: int,
        pip_location: float = 0.0001,
    ) -> Dict:
        """
        Compare P&L using midpoint vs bid/ask pricing.

        Demonstrates impact of using realistic pricing.

        Args:
            direction: "BUY" or "SELL"
            entry_candle: Entry candle
            exit_candle: Exit candle
            units: Position size
            pip_location: Pip size

        Returns:
            Dictionary comparing midpoint vs bid/ask:
            {
                "midpoint_pips": 7.0,
                "bidask_pips": 4.0,
                "difference_pips": 3.0,
                "overstatement_percent": 75.0,
            }
        """
        # Calculate with bid/ask
        bidask_result = self.calculate_pnl(
            direction=direction,
            entry_candle=entry_candle,
            exit_candle=exit_candle,
            units=units,
            pip_location=pip_location,
        )

        # Calculate with midpoint
        entry_mid = self._get_midpoint_price(entry_candle, "close")
        exit_mid = self._get_midpoint_price(exit_candle, "close")

        if direction.upper() == "BUY":
            mid_pnl_points = exit_mid - entry_mid
        else:
            mid_pnl_points = entry_mid - exit_mid

        mid_pips = mid_pnl_points / pip_location

        # Calculate difference
        diff_pips = mid_pips - bidask_result["pips"]
        overstatement = (diff_pips / mid_pips * 100) if mid_pips != 0 else 0

        return {
            "direction": direction,
            "midpoint_pips": mid_pips,
            "bidask_pips": bidask_result["pips"],
            "difference_pips": diff_pips,
            "overstatement_percent": overstatement,
            "entry_spread_pips": bidask_result["entry_spread_pips"],
            "exit_spread_pips": bidask_result["exit_spread_pips"],
            "total_spread_cost_pips": bidask_result["entry_spread_pips"] + bidask_result["exit_spread_pips"],
        }


# Example usage
def example_usage():
    """Example demonstrating bid/ask pricing impact"""
    print("\n" + "="*60)
    print("BID/ASK PRICING MODULE")
    print("="*60)

    print("""
This module demonstrates why using bid/ask pricing is critical
for realistic backtesting.

Midpoint pricing OVERSTATES profitability because:
1. Real BUY orders execute at ASK (higher price)
2. Real SELL orders execute at BID (lower price)
3. Spread is built into every entry and exit

For a typical EUR/USD trade with 1.5 pip spread:
- Midpoint shows: +7 pips profit
- Bid/ask shows: +4 pips profit (3 pips lost to spread)
- Reality matches bid/ask, not midpoint

Without bid/ask pricing, backtests can show profitable strategies
that lose money in live trading.

To use this module:
1. Fetch candles with price="BA" (not price="M")
2. Use BidAskPricer.get_execution_price() for entries/exits
3. Use BidAskPricer.calculate_pnl() for P&L calculations
4. Use average of bid/ask for technical indicators

Example:
    from bid_ask_pricing import BidAskPricer

    pricer = BidAskPricer()

    # Get entry price for BUY order
    entry_price = pricer.get_execution_price(candle, "BUY")  # Uses ASK

    # Get exit price for closing BUY order
    exit_price = pricer.get_execution_price(candle, "SELL")  # Uses BID

    # Calculate realistic P&L
    pnl = pricer.calculate_pnl("BUY", entry_candle, exit_candle, 10000)

The multi_timeframe_data.py module already supports bid/ask fetching
with use_bid_ask=True parameter.
""")

    print("="*60)
    print("✅ Module ready for use")
    print("="*60)


if __name__ == "__main__":
    example_usage()
