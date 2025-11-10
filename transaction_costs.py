"""
Transaction Cost Modeling Module

Models all trading costs to accurately calculate net profitability.
This is CRITICAL for scalping - costs can be 60%+ of gross profits.

Cost Components:
1. Spread: 0.5-3.0 pips depending on instrument and market conditions
2. Slippage: 0.5-2.0 pips for market orders
3. Swap/Rollover: -$0.50 to $0.50 per lot per day for overnight positions
4. Commission: Usually $0 for forex retail (included in spread)

Why This Matters:
- EUR/USD scalping with 5 pip targets and 3 pip costs = 60% cost ratio
- Without cost modeling, strategy appears profitable but loses money
- Costs vary by time of day, volatility, and broker

Usage:
    from transaction_costs import CostCalculator

    calc = CostCalculator()

    # Calculate costs for a trade
    costs = calc.calculate_trade_costs(
        instrument="EUR_USD",
        units=10000,
        entry_price=1.0850,
        exit_price=1.0855,
        hold_days=0,
        market_condition="normal"
    )

    print(f"Total cost: ${costs['total_cost_usd']:.2f}")
    print(f"Net P&L: ${costs['net_pnl_usd']:.2f}")
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MarketCondition(Enum):
    """Market volatility conditions affecting spread and slippage"""
    QUIET = "quiet"           # Asian session, low volatility
    NORMAL = "normal"         # London/NY session, normal volatility
    VOLATILE = "volatile"     # High impact news, high volatility
    EXTREME = "extreme"       # Major events, flash crash, etc.


@dataclass
class InstrumentCostProfile:
    """
    Cost profile for a trading instrument.

    All spreads and slippage are in pips (0.0001 for most pairs, 0.01 for JPY).
    """
    instrument: str
    base_spread: float        # Typical spread in pips
    min_spread: float         # Best possible spread
    max_spread: float         # Worst normal spread
    slippage_avg: float       # Average slippage in pips
    slippage_std: float       # Slippage standard deviation
    swap_long: float          # Swap for long positions (USD per 10k units per day)
    swap_short: float         # Swap for short positions (USD per 10k units per day)
    pip_value: float          # Value of 1 pip in USD for 10k units
    pip_location: float       # 0.0001 for most pairs, 0.01 for JPY pairs


# Realistic cost profiles for major forex pairs
COST_PROFILES = {
    "EUR_USD": InstrumentCostProfile(
        instrument="EUR_USD",
        base_spread=0.8,
        min_spread=0.5,
        max_spread=2.0,
        slippage_avg=0.5,
        slippage_std=0.3,
        swap_long=-0.50,
        swap_short=0.20,
        pip_value=1.0,
        pip_location=0.0001,
    ),
    "GBP_USD": InstrumentCostProfile(
        instrument="GBP_USD",
        base_spread=1.2,
        min_spread=0.8,
        max_spread=3.0,
        slippage_avg=0.7,
        slippage_std=0.4,
        swap_long=-0.60,
        swap_short=0.25,
        pip_value=1.0,
        pip_location=0.0001,
    ),
    "USD_JPY": InstrumentCostProfile(
        instrument="USD_JPY",
        base_spread=0.7,
        min_spread=0.4,
        max_spread=2.0,
        slippage_avg=0.5,
        slippage_std=0.3,
        swap_long=-0.30,
        swap_short=-0.10,
        pip_value=0.91,  # Varies with JPY rate, ~$9.1 per 10k units
        pip_location=0.01,
    ),
    "AUD_USD": InstrumentCostProfile(
        instrument="AUD_USD",
        base_spread=1.0,
        min_spread=0.6,
        max_spread=2.5,
        slippage_avg=0.6,
        slippage_std=0.4,
        swap_long=-0.40,
        swap_short=0.15,
        pip_value=1.0,
        pip_location=0.0001,
    ),
    "USD_CAD": InstrumentCostProfile(
        instrument="USD_CAD",
        base_spread=1.2,
        min_spread=0.7,
        max_spread=3.0,
        slippage_avg=0.6,
        slippage_std=0.4,
        swap_long=-0.45,
        swap_short=0.18,
        pip_value=0.74,  # ~$7.4 per 10k units
        pip_location=0.0001,
    ),
    "EUR_GBP": InstrumentCostProfile(
        instrument="EUR_GBP",
        base_spread=1.5,
        min_spread=1.0,
        max_spread=3.5,
        slippage_avg=0.8,
        slippage_std=0.5,
        swap_long=-0.55,
        swap_short=0.22,
        pip_value=1.27,  # ~$12.7 per 10k units
        pip_location=0.0001,
    ),
}


class CostCalculator:
    """
    Calculates comprehensive transaction costs for forex trades.

    Includes spread, slippage, and swap costs with adjustments
    for market conditions and time of day.
    """

    def __init__(self, cost_profiles: Optional[Dict[str, InstrumentCostProfile]] = None):
        """
        Initialize cost calculator.

        Args:
            cost_profiles: Optional custom cost profiles
        """
        self.cost_profiles = cost_profiles or COST_PROFILES

    def calculate_trade_costs(
        self,
        instrument: str,
        units: int,
        entry_price: float,
        exit_price: Optional[float] = None,
        hold_days: float = 0.0,
        market_condition: str = "normal",
        include_slippage: bool = True,
    ) -> Dict:
        """
        Calculate all costs for a trade.

        Args:
            instrument: e.g., "EUR_USD"
            units: Position size (positive = long, negative = short)
            entry_price: Entry price
            exit_price: Exit price (None = calculate break-even)
            hold_days: Days position held (for swap calculation)
            market_condition: "quiet", "normal", "volatile", or "extreme"
            include_slippage: Include slippage costs

        Returns:
            Dictionary with comprehensive cost breakdown:
            {
                "spread_cost_pips": 1.5,
                "spread_cost_usd": 15.00,
                "slippage_cost_pips": 1.0,
                "slippage_cost_usd": 10.00,
                "swap_cost_usd": -2.50,
                "total_cost_pips": 2.5,
                "total_cost_usd": 22.50,
                "gross_pnl_usd": 50.00,
                "net_pnl_usd": 27.50,
                "cost_ratio": 0.45,  # costs / gross profit
                "break_even_pips": 2.5,
            }
        """
        # Get cost profile
        profile = self.cost_profiles.get(instrument)
        if not profile:
            logger.warning(f"No cost profile for {instrument}, using EUR_USD defaults")
            profile = self.cost_profiles["EUR_USD"]

        # Parse market condition
        try:
            condition = MarketCondition(market_condition.lower())
        except ValueError:
            condition = MarketCondition.NORMAL

        # Calculate spread cost
        spread_pips = self._get_spread(profile, condition)
        spread_cost_pips = spread_pips * 2  # Entry + exit

        # Calculate slippage cost
        slippage_cost_pips = 0.0
        if include_slippage:
            slippage_cost_pips = self._get_slippage(profile, condition) * 2  # Entry + exit

        # Calculate swap cost
        swap_cost_usd = self._get_swap_cost(profile, units, hold_days)

        # Total cost in pips and USD
        total_cost_pips = spread_cost_pips + slippage_cost_pips

        # Convert to USD (scale by position size)
        lots = abs(units) / 10000  # 1 lot = 10k units
        spread_cost_usd = spread_cost_pips * profile.pip_value * lots
        slippage_cost_usd = slippage_cost_pips * profile.pip_value * lots
        total_cost_usd = spread_cost_usd + slippage_cost_usd + swap_cost_usd

        # Calculate gross P&L if exit price provided
        gross_pnl_usd = 0.0
        net_pnl_usd = 0.0
        cost_ratio = 0.0

        if exit_price is not None:
            # Calculate P&L
            price_diff = exit_price - entry_price
            if units < 0:  # Short position
                price_diff = -price_diff

            pips = price_diff / profile.pip_location
            gross_pnl_usd = pips * profile.pip_value * lots

            net_pnl_usd = gross_pnl_usd - total_cost_usd

            # Cost ratio (what % of profit goes to costs)
            if gross_pnl_usd > 0:
                cost_ratio = total_cost_usd / gross_pnl_usd

        return {
            "instrument": instrument,
            "units": units,
            "lots": lots,
            "spread_cost_pips": spread_cost_pips,
            "spread_cost_usd": spread_cost_usd,
            "slippage_cost_pips": slippage_cost_pips,
            "slippage_cost_usd": slippage_cost_usd,
            "swap_cost_usd": swap_cost_usd,
            "total_cost_pips": total_cost_pips,
            "total_cost_usd": total_cost_usd,
            "gross_pnl_usd": gross_pnl_usd,
            "net_pnl_usd": net_pnl_usd,
            "cost_ratio": cost_ratio,
            "break_even_pips": total_cost_pips,
            "pip_value": profile.pip_value,
            "market_condition": market_condition,
        }

    def _get_spread(self, profile: InstrumentCostProfile, condition: MarketCondition) -> float:
        """
        Get spread for current market conditions.

        Args:
            profile: Instrument cost profile
            condition: Current market condition

        Returns:
            Spread in pips
        """
        if condition == MarketCondition.QUIET:
            return profile.min_spread
        elif condition == MarketCondition.NORMAL:
            return profile.base_spread
        elif condition == MarketCondition.VOLATILE:
            return profile.base_spread * 1.5
        else:  # EXTREME
            return profile.max_spread

    def _get_slippage(self, profile: InstrumentCostProfile, condition: MarketCondition) -> float:
        """
        Get expected slippage for current market conditions.

        Args:
            profile: Instrument cost profile
            condition: Current market condition

        Returns:
            Slippage in pips
        """
        base_slippage = profile.slippage_avg

        if condition == MarketCondition.QUIET:
            return base_slippage * 0.7
        elif condition == MarketCondition.NORMAL:
            return base_slippage
        elif condition == MarketCondition.VOLATILE:
            return base_slippage * 2.0
        else:  # EXTREME
            return base_slippage * 3.0

    def _get_swap_cost(self, profile: InstrumentCostProfile, units: int, hold_days: float) -> float:
        """
        Calculate swap cost for overnight positions.

        Args:
            profile: Instrument cost profile
            units: Position size
            hold_days: Days held

        Returns:
            Swap cost in USD
        """
        if hold_days == 0:
            return 0.0

        # Determine if long or short
        swap_rate = profile.swap_long if units > 0 else profile.swap_short

        # Scale by position size
        lots = abs(units) / 10000
        swap_cost = swap_rate * lots * hold_days

        return swap_cost

    def calculate_required_win_rate(
        self,
        instrument: str,
        target_pips: float,
        stop_loss_pips: float,
        market_condition: str = "normal",
    ) -> Dict:
        """
        Calculate required win rate to be profitable given costs.

        Args:
            instrument: e.g., "EUR_USD"
            target_pips: Take profit in pips
            stop_loss_pips: Stop loss in pips
            market_condition: Market condition

        Returns:
            Dictionary with required win rate and profitability analysis
        """
        profile = self.cost_profiles.get(instrument, self.cost_profiles["EUR_USD"])

        # Calculate costs
        condition = MarketCondition(market_condition.lower())
        spread = self._get_spread(profile, condition) * 2
        slippage = self._get_slippage(profile, condition) * 2
        total_cost_pips = spread + slippage

        # Adjust target and stop for costs
        net_target_pips = target_pips - total_cost_pips
        net_stop_pips = stop_loss_pips + total_cost_pips

        # Calculate required win rate
        # Break-even: (win_rate * net_target) + (loss_rate * -net_stop) = 0
        # win_rate * net_target = (1 - win_rate) * net_stop
        # win_rate * (net_target + net_stop) = net_stop
        # win_rate = net_stop / (net_target + net_stop)

        if net_target_pips <= 0:
            return {
                "viable": False,
                "reason": "Target too small to overcome costs",
                "total_cost_pips": total_cost_pips,
                "net_target_pips": net_target_pips,
            }

        required_win_rate = net_stop_pips / (net_target_pips + net_stop_pips)

        return {
            "viable": required_win_rate < 0.70,  # Arbitrary threshold
            "instrument": instrument,
            "target_pips": target_pips,
            "stop_loss_pips": stop_loss_pips,
            "total_cost_pips": total_cost_pips,
            "net_target_pips": net_target_pips,
            "net_stop_pips": net_stop_pips,
            "required_win_rate": required_win_rate,
            "cost_ratio_on_win": total_cost_pips / target_pips,
            "market_condition": market_condition,
        }


# Example usage and testing
def example_usage():
    """Example of using the cost calculator"""
    print("\n" + "="*60)
    print("TRANSACTION COST CALCULATOR EXAMPLES")
    print("="*60)

    calc = CostCalculator()

    # Example 1: EUR/USD scalping trade
    print("\n=== Example 1: EUR/USD Scalping (5 pip target) ===")
    costs = calc.calculate_trade_costs(
        instrument="EUR_USD",
        units=10000,  # 1 mini lot
        entry_price=1.0850,
        exit_price=1.0855,  # +5 pips
        hold_days=0,
        market_condition="normal",
    )

    print(f"Position: {costs['lots']} lots ({costs['units']} units)")
    print(f"Gross P&L: ${costs['gross_pnl_usd']:.2f}")
    print(f"Spread cost: {costs['spread_cost_pips']:.1f} pips (${costs['spread_cost_usd']:.2f})")
    print(f"Slippage cost: {costs['slippage_cost_pips']:.1f} pips (${costs['slippage_cost_usd']:.2f})")
    print(f"Total costs: {costs['total_cost_pips']:.1f} pips (${costs['total_cost_usd']:.2f})")
    print(f"Net P&L: ${costs['net_pnl_usd']:.2f}")
    print(f"Cost ratio: {costs['cost_ratio']*100:.1f}%")

    # Example 2: Required win rate
    print("\n=== Example 2: Required Win Rate Analysis ===")
    analysis = calc.calculate_required_win_rate(
        instrument="EUR_USD",
        target_pips=5.0,
        stop_loss_pips=5.0,
        market_condition="normal",
    )

    print(f"Strategy: 5 pip target, 5 pip stop (1:1 R:R)")
    print(f"Total costs: {analysis['total_cost_pips']:.1f} pips")
    print(f"Net target: {analysis['net_target_pips']:.1f} pips")
    print(f"Net stop: {analysis['net_stop_pips']:.1f} pips")
    print(f"Required win rate: {analysis['required_win_rate']*100:.1f}%")
    print(f"Cost ratio: {analysis['cost_ratio_on_win']*100:.1f}%")
    print(f"Viable: {analysis['viable']}")

    # Example 3: Different market conditions
    print("\n=== Example 3: Cost Variation by Market Condition ===")
    for condition in ["quiet", "normal", "volatile", "extreme"]:
        costs = calc.calculate_trade_costs(
            instrument="EUR_USD",
            units=10000,
            entry_price=1.0850,
            exit_price=1.0855,
            market_condition=condition,
        )
        print(f"{condition.capitalize():12s}: {costs['total_cost_pips']:.1f} pips (${costs['total_cost_usd']:.2f})")

    # Example 4: Overnight position with swap
    print("\n=== Example 4: Overnight Position (3 days) ===")
    costs = calc.calculate_trade_costs(
        instrument="EUR_USD",
        units=10000,
        entry_price=1.0850,
        exit_price=1.0870,  # +20 pips
        hold_days=3.0,
        market_condition="normal",
    )

    print(f"Gross P&L: ${costs['gross_pnl_usd']:.2f}")
    print(f"Spread + slippage: ${costs['spread_cost_usd'] + costs['slippage_cost_usd']:.2f}")
    print(f"Swap cost: ${costs['swap_cost_usd']:.2f}")
    print(f"Total costs: ${costs['total_cost_usd']:.2f}")
    print(f"Net P&L: ${costs['net_pnl_usd']:.2f}")

    print("\n" + "="*60)
    print("✅ Examples complete")
    print("="*60)


if __name__ == "__main__":
    example_usage()
