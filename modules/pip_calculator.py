"""
Pip Value Calculator Module

Accurately calculates pip values for forex pairs, accounting for:
- Different quote currencies (USD, EUR, GBP, JPY, etc.)
- Position sizes (standard lot, mini lot, micro lot)
- Current exchange rates for cross pairs
- Special handling for JPY pairs (0.01 pip location vs 0.0001)

Why This Matters:
- Incorrect pip values lead to wrong position sizing
- Can risk too much (blow account) or too little (missed opportunity)
- Critical for accurate P&L calculation

Pip Value Formula:
    For XXX_YYY pair:
    - If account currency = YYY: pip_value = (pip_location / 1) * position_size
    - If account currency = XXX: pip_value = (pip_location / rate) * position_size
    - If account currency != XXX or YYY: need conversion via XXX_ACC or YYY_ACC rate

Usage:
    from pip_calculator import PipCalculator

    calc = PipCalculator()

    # Calculate pip value for EUR/USD
    pip_value = calc.calculate_pip_value(
        instrument="EUR_USD",
        account_currency="USD",
        current_rate=1.0850,
        units=10000  # 1 mini lot
    )

    print(f"1 pip = ${pip_value:.2f}")
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class PipCalculator:
    """
    Calculates accurate pip values for forex trading.

    Handles all major currency pairs and crosses, accounting for
    quote currency, account currency, and current exchange rates.
    """

    # Pip locations for different currency types
    PIP_LOCATIONS = {
        "JPY": 0.01,      # Japanese Yen
        "HUF": 0.01,      # Hungarian Forint
        "default": 0.0001  # Most currencies
    }

    def __init__(self):
        """Initialize pip calculator"""
        pass

    def calculate_pip_value(
        self,
        instrument: str,
        account_currency: str = "USD",
        current_rate: Optional[float] = None,
        units: int = 10000,
        conversion_rates: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculate pip value in account currency.

        Args:
            instrument: e.g., "EUR_USD", "USD_JPY"
            account_currency: Account denomination (usually "USD")
            current_rate: Current exchange rate for the pair
            units: Position size in base currency units (10000 = 1 mini lot)
            conversion_rates: Optional dict of exchange rates for cross conversions

        Returns:
            Pip value in account currency (e.g., $1.00 for EUR/USD mini lot)

        Raises:
            ValueError: If instrument format is invalid
        """
        # Parse instrument
        parts = instrument.split("_")
        if len(parts) != 2:
            raise ValueError(f"Invalid instrument format: {instrument}")

        base_currency, quote_currency = parts

        # Get pip location
        pip_location = self._get_pip_location(quote_currency)

        # Case 1: Account currency = quote currency (e.g., EUR/USD with USD account)
        if account_currency == quote_currency:
            return (pip_location * units)

        # Case 2: Account currency = base currency (e.g., USD/JPY with USD account)
        if account_currency == base_currency:
            if current_rate is None:
                raise ValueError("current_rate required when account currency = base currency")
            return (pip_location / current_rate) * units

        # Case 3: Cross pair (e.g., EUR/GBP with USD account)
        # Need to convert quote currency to account currency
        if conversion_rates is None:
            logger.warning(
                f"No conversion rates provided for {quote_currency} to {account_currency}. "
                f"Using estimated value."
            )
            return pip_location * units  # Fallback estimate

        # Try to find conversion rate
        conversion_rate = self._find_conversion_rate(
            quote_currency,
            account_currency,
            conversion_rates
        )

        if conversion_rate is None:
            logger.warning(
                f"Could not find conversion rate for {quote_currency} to {account_currency}"
            )
            return pip_location * units  # Fallback

        # Calculate pip value with conversion
        pip_value_in_quote = pip_location * units
        pip_value_in_account = pip_value_in_quote * conversion_rate

        return pip_value_in_account

    def _get_pip_location(self, currency: str) -> float:
        """
        Get pip location for a currency.

        Args:
            currency: Currency code (e.g., "USD", "JPY")

        Returns:
            Pip location (0.0001 or 0.01)
        """
        return self.PIP_LOCATIONS.get(currency, self.PIP_LOCATIONS["default"])

    def _find_conversion_rate(
        self,
        from_currency: str,
        to_currency: str,
        rates: Dict[str, float]
    ) -> Optional[float]:
        """
        Find conversion rate between two currencies.

        Tries direct rate (FROM_TO) and inverse rate (TO_FROM).

        Args:
            from_currency: Source currency
            to_currency: Target currency
            rates: Dictionary of exchange rates

        Returns:
            Conversion rate or None if not found
        """
        # Try direct rate
        direct_pair = f"{from_currency}_{to_currency}"
        if direct_pair in rates:
            return rates[direct_pair]

        # Try inverse rate
        inverse_pair = f"{to_currency}_{from_currency}"
        if inverse_pair in rates:
            return 1.0 / rates[inverse_pair]

        return None

    def calculate_pip_value_from_price_diff(
        self,
        instrument: str,
        entry_price: float,
        exit_price: float,
        units: int,
        account_currency: str = "USD",
        conversion_rates: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Calculate P&L from price difference.

        Args:
            instrument: e.g., "EUR_USD"
            entry_price: Entry price
            exit_price: Exit price
            units: Position size (positive = long, negative = short)
            account_currency: Account currency
            conversion_rates: Optional conversion rates

        Returns:
            Dictionary with P&L details:
            {
                "pips": 15.0,
                "pip_value": 1.0,
                "pnl": 15.0,
                "direction": "long",
            }
        """
        # Parse instrument
        parts = instrument.split("_")
        if len(parts) != 2:
            raise ValueError(f"Invalid instrument format: {instrument}")

        base_currency, quote_currency = parts

        # Calculate pip location
        pip_location = self._get_pip_location(quote_currency)

        # Calculate price difference
        price_diff = exit_price - entry_price

        # Adjust for direction
        direction = "long" if units > 0 else "short"
        if units < 0:
            price_diff = -price_diff

        # Calculate pips
        pips = price_diff / pip_location

        # Calculate pip value
        avg_rate = (entry_price + exit_price) / 2
        pip_value = self.calculate_pip_value(
            instrument=instrument,
            account_currency=account_currency,
            current_rate=avg_rate,
            units=abs(units),
            conversion_rates=conversion_rates,
        )

        # Calculate P&L
        pnl = pips * pip_value

        return {
            "instrument": instrument,
            "direction": direction,
            "units": units,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "price_diff": price_diff if units > 0 else -price_diff,
            "pips": pips,
            "pip_value": pip_value,
            "pip_location": pip_location,
            "pnl": pnl,
            "account_currency": account_currency,
        }

    def calculate_position_size_from_risk(
        self,
        instrument: str,
        account_balance: float,
        risk_percent: float,
        stop_loss_pips: float,
        account_currency: str = "USD",
        current_rate: Optional[float] = None,
        conversion_rates: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Calculate position size based on risk parameters.

        Formula:
            position_size = risk_amount / (stop_loss_pips * pip_value)

        Args:
            instrument: e.g., "EUR_USD"
            account_balance: Account balance in account currency
            risk_percent: Risk per trade (e.g., 1.0 for 1%)
            stop_loss_pips: Stop loss distance in pips
            account_currency: Account currency
            current_rate: Current exchange rate
            conversion_rates: Optional conversion rates

        Returns:
            Dictionary with position sizing details:
            {
                "units": 10000,
                "lots": 1.0,
                "risk_amount": 100.0,
                "pip_value": 1.0,
                "max_loss": 100.0,
            }
        """
        # Calculate risk amount
        risk_amount = account_balance * (risk_percent / 100)

        # Calculate pip value for standard sizing (10k units)
        pip_value = self.calculate_pip_value(
            instrument=instrument,
            account_currency=account_currency,
            current_rate=current_rate,
            units=10000,  # Calculate per mini lot
            conversion_rates=conversion_rates,
        )

        if pip_value <= 0:
            raise ValueError("Invalid pip value calculated")

        # Calculate position size
        # risk_amount = units * stop_loss_pips * pip_value_per_10k / 10000
        # units = risk_amount * 10000 / (stop_loss_pips * pip_value_per_10k)
        units = (risk_amount * 10000) / (stop_loss_pips * pip_value)

        # Round to appropriate precision
        units = int(units)

        # Calculate actual values
        lots = units / 10000
        actual_pip_value = pip_value * lots
        max_loss = stop_loss_pips * actual_pip_value

        return {
            "instrument": instrument,
            "account_balance": account_balance,
            "risk_percent": risk_percent,
            "risk_amount": risk_amount,
            "stop_loss_pips": stop_loss_pips,
            "units": units,
            "lots": lots,
            "pip_value_per_lot": pip_value,
            "actual_pip_value": actual_pip_value,
            "max_loss": max_loss,
            "risk_utilization": (max_loss / risk_amount) * 100,  # Should be ~100%
        }


# Example usage and testing
def example_usage():
    """Example of using the pip calculator"""
    print("\n" + "="*60)
    print("PIP VALUE CALCULATOR EXAMPLES")
    print("="*60)

    calc = PipCalculator()

    # Example 1: EUR/USD (account currency = quote currency)
    print("\n=== Example 1: EUR/USD with USD Account ===")
    pip_value = calc.calculate_pip_value(
        instrument="EUR_USD",
        account_currency="USD",
        current_rate=1.0850,
        units=10000,
    )
    print(f"Pip value: ${pip_value:.2f} per mini lot")
    print(f"Expected: $1.00 (quote currency = account currency)")

    # Example 2: USD/JPY (account currency = base currency)
    print("\n=== Example 2: USD/JPY with USD Account ===")
    pip_value = calc.calculate_pip_value(
        instrument="USD_JPY",
        account_currency="USD",
        current_rate=150.00,
        units=10000,
    )
    print(f"Pip value: ${pip_value:.2f} per mini lot")
    print(f"Expected: ~$0.67 (0.01 / 150.00 * 10000)")

    # Example 3: GBP/USD (different pip value due to larger quote)
    print("\n=== Example 3: GBP/USD with USD Account ===")
    pip_value = calc.calculate_pip_value(
        instrument="GBP_USD",
        account_currency="USD",
        current_rate=1.2500,
        units=10000,
    )
    print(f"Pip value: ${pip_value:.2f} per mini lot")
    print(f"Expected: $1.00 (quote currency = account currency)")

    # Example 4: P&L calculation
    print("\n=== Example 4: P&L Calculation (EUR/USD +15 pips) ===")
    pnl = calc.calculate_pip_value_from_price_diff(
        instrument="EUR_USD",
        entry_price=1.0850,
        exit_price=1.0865,  # +15 pips
        units=10000,
        account_currency="USD",
    )
    print(f"Entry: {pnl['entry_price']:.4f}")
    print(f"Exit: {pnl['exit_price']:.4f}")
    print(f"Pips: {pnl['pips']:.1f}")
    print(f"Pip value: ${pnl['pip_value']:.2f}")
    print(f"P&L: ${pnl['pnl']:.2f}")

    # Example 5: Position sizing
    print("\n=== Example 5: Position Sizing (1% risk, 10 pip stop) ===")
    sizing = calc.calculate_position_size_from_risk(
        instrument="EUR_USD",
        account_balance=10000,
        risk_percent=1.0,
        stop_loss_pips=10.0,
        account_currency="USD",
        current_rate=1.0850,
    )
    print(f"Account balance: ${sizing['account_balance']:.2f}")
    print(f"Risk: {sizing['risk_percent']}% = ${sizing['risk_amount']:.2f}")
    print(f"Stop loss: {sizing['stop_loss_pips']} pips")
    print(f"Position size: {sizing['units']} units ({sizing['lots']:.2f} lots)")
    print(f"Max loss: ${sizing['max_loss']:.2f}")
    print(f"Risk utilization: {sizing['risk_utilization']:.1f}%")

    # Example 6: Different instruments comparison
    print("\n=== Example 6: Pip Values Across Instruments ===")
    instruments = [
        ("EUR_USD", 1.0850),
        ("GBP_USD", 1.2500),
        ("USD_JPY", 150.00),
        ("AUD_USD", 0.6500),
        ("USD_CAD", 1.3500),
    ]

    for instrument, rate in instruments:
        pip_value = calc.calculate_pip_value(
            instrument=instrument,
            account_currency="USD",
            current_rate=rate,
            units=10000,
        )
        print(f"{instrument:12s} @ {rate:8.4f}: ${pip_value:.2f} per pip (mini lot)")

    print("\n" + "="*60)
    print("✅ Examples complete")
    print("="*60)


if __name__ == "__main__":
    example_usage()
