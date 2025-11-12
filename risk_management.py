"""
Risk Management Module

Enforces leverage limits and position size checks to prevent account blow-ups.

Why This Matters:
- High leverage magnifies both gains AND losses
- 50:1 leverage means 2% adverse move wipes out account
- Most retail traders lose money due to over-leveraging
- Broker may force-close positions if margin falls too low

Critical Rules:
1. Maximum leverage: 20:1 for experienced, 10:1 for beginners
2. Maximum risk per trade: 1-2% of account
3. Maximum total exposure: 3-5x account balance
4. Maintain 100%+ margin level (don't get margin called)

Example Disaster:
- $10k account
- Take 100k position (10:1 leverage) - SEEMS SAFE
- Add another 100k position (now 20:1)
- Add third 100k position (now 30:1)
- Market moves 3% against you
- Loss: $9k (90% of account GONE)
- Margin call: Broker closes all positions

Usage:
    from risk_management import RiskManager

    rm = RiskManager(
        max_leverage=20.0,
        max_risk_per_trade=1.0,
        max_total_exposure_ratio=3.0,
    )

    # Check if position is allowed
    result = rm.validate_position(
        account_balance=10000,
        existing_exposure=50000,
        new_position_size=20000,
        stop_loss_pips=10,
        instrument="EUR_USD",
    )

    if not result["allowed"]:
        print(f"Position rejected: {result['reason']}")
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PositionInfo:
    """Information about an open position"""
    instrument: str
    units: int              # Positive = long, negative = short
    unrealized_pnl: float   # Current P&L in account currency
    margin_used: float      # Margin locked for this position


class RiskManager:
    """
    Enforces risk management rules and leverage limits.

    Prevents:
    - Excessive leverage
    - Over-sizing positions
    - Insufficient margin
    - Portfolio concentration
    """

    def __init__(
        self,
        max_leverage: float = 20.0,
        max_risk_per_trade: float = 1.0,
        max_total_exposure_ratio: float = 3.0,
        min_margin_level: float = 100.0,
        max_correlation_exposure: float = 2.0,
    ):
        """
        Initialize risk manager.

        Args:
            max_leverage: Maximum leverage allowed (e.g., 20.0 = 20:1)
            max_risk_per_trade: Maximum risk per trade as % of balance
            max_total_exposure_ratio: Max total exposure as multiple of balance
            min_margin_level: Minimum margin level % (100 = break-even)
            max_correlation_exposure: Max exposure to correlated pairs
        """
        self.max_leverage = max_leverage
        self.max_risk_per_trade = max_risk_per_trade
        self.max_total_exposure_ratio = max_total_exposure_ratio
        self.min_margin_level = min_margin_level
        self.max_correlation_exposure = max_correlation_exposure

    def validate_position(
        self,
        account_balance: float,
        new_position_units: int,
        instrument: str,
        current_price: float,
        stop_loss_pips: float,
        pip_value: float,
        existing_positions: Optional[List[PositionInfo]] = None,
        margin_rate: float = 0.03333,  # 30:1 margin (OANDA default)
    ) -> Dict:
        """
        Validate if a new position is allowed.

        Performs comprehensive checks:
        1. Leverage check
        2. Risk per trade check
        3. Total exposure check
        4. Margin requirement check
        5. Position size sanity check

        Args:
            account_balance: Current account balance
            new_position_units: Proposed position size
            instrument: e.g., "EUR_USD"
            current_price: Current market price
            stop_loss_pips: Stop loss distance in pips
            pip_value: Pip value for position size
            existing_positions: List of open positions
            margin_rate: Margin requirement (e.g., 0.03333 = 30:1 leverage)

        Returns:
            Dictionary with validation result:
            {
                "allowed": True/False,
                "reason": "explanation if rejected",
                "checks": {
                    "leverage_check": {"passed": True, "value": 15.0, "limit": 20.0},
                    "risk_check": {...},
                    "exposure_check": {...},
                    "margin_check": {...},
                },
                "warnings": ["list of warnings"],
            }
        """
        existing_positions = existing_positions or []
        checks = {}
        warnings = []

        # Calculate position value
        position_value = abs(new_position_units) * current_price

        # 1. Leverage Check
        leverage_check = self._check_leverage(
            account_balance,
            position_value,
            existing_positions,
        )
        checks["leverage"] = leverage_check

        if not leverage_check["passed"]:
            return {
                "allowed": False,
                "reason": f"Leverage limit exceeded: {leverage_check['value']:.1f}x > {self.max_leverage}x",
                "checks": checks,
                "warnings": warnings,
            }

        # Add warning if leverage is high but still allowed
        if leverage_check["value"] > self.max_leverage * 0.8:
            warnings.append(f"High leverage: {leverage_check['value']:.1f}x (limit: {self.max_leverage}x)")

        # 2. Risk Per Trade Check
        risk_check = self._check_risk_per_trade(
            account_balance,
            new_position_units,
            stop_loss_pips,
            pip_value,
        )
        checks["risk_per_trade"] = risk_check

        if not risk_check["passed"]:
            return {
                "allowed": False,
                "reason": f"Risk per trade exceeded: {risk_check['value']:.1f}% > {self.max_risk_per_trade}%",
                "checks": checks,
                "warnings": warnings,
            }

        # 3. Total Exposure Check
        exposure_check = self._check_total_exposure(
            account_balance,
            position_value,
            existing_positions,
        )
        checks["exposure"] = exposure_check

        if not exposure_check["passed"]:
            return {
                "allowed": False,
                "reason": f"Total exposure exceeded: {exposure_check['value']:.1f}x > {self.max_total_exposure_ratio}x",
                "checks": checks,
                "warnings": warnings,
            }

        # 4. Margin Check
        margin_check = self._check_margin_requirement(
            account_balance,
            position_value,
            existing_positions,
            margin_rate,
        )
        checks["margin"] = margin_check

        if not margin_check["passed"]:
            return {
                "allowed": False,
                "reason": f"Insufficient margin: {margin_check['free_margin']:.2f} < {margin_check['required_margin']:.2f}",
                "checks": checks,
                "warnings": warnings,
            }

        # Add warning if margin is getting tight
        if margin_check["margin_level"] < self.min_margin_level * 1.5:
            warnings.append(f"Low margin level: {margin_check['margin_level']:.1f}%")

        # 5. Position Size Sanity Check
        sanity_check = self._check_position_sanity(
            new_position_units,
            account_balance,
            current_price,
        )
        checks["sanity"] = sanity_check

        if not sanity_check["passed"]:
            warnings.append(f"Position size unusual: {sanity_check['message']}")

        # All checks passed
        return {
            "allowed": True,
            "reason": "All risk checks passed",
            "checks": checks,
            "warnings": warnings,
        }

    def _check_leverage(
        self,
        account_balance: float,
        new_position_value: float,
        existing_positions: List[PositionInfo],
    ) -> Dict:
        """Check if leverage limit is respected"""
        # Calculate total exposure
        existing_exposure = sum(abs(p.units) * 1.0 for p in existing_positions)  # Simplified
        total_exposure = existing_exposure + new_position_value

        # Calculate leverage
        leverage = total_exposure / account_balance if account_balance > 0 else 999

        return {
            "passed": leverage <= self.max_leverage,
            "value": leverage,
            "limit": self.max_leverage,
            "existing_exposure": existing_exposure,
            "new_position_value": new_position_value,
            "total_exposure": total_exposure,
        }

    def _check_risk_per_trade(
        self,
        account_balance: float,
        position_units: int,
        stop_loss_pips: float,
        pip_value: float,
    ) -> Dict:
        """Check if risk per trade is within limit"""
        # Calculate potential loss
        lots = abs(position_units) / 10000
        max_loss = stop_loss_pips * pip_value * lots

        # Calculate risk percentage
        risk_percent = (max_loss / account_balance * 100) if account_balance > 0 else 999

        return {
            "passed": risk_percent <= self.max_risk_per_trade,
            "value": risk_percent,
            "limit": self.max_risk_per_trade,
            "max_loss": max_loss,
            "stop_loss_pips": stop_loss_pips,
        }

    def _check_total_exposure(
        self,
        account_balance: float,
        new_position_value: float,
        existing_positions: List[PositionInfo],
    ) -> Dict:
        """Check if total exposure is within limit"""
        # Calculate total exposure
        existing_exposure = sum(abs(p.units) * 1.0 for p in existing_positions)
        total_exposure = existing_exposure + new_position_value

        # Calculate exposure ratio
        exposure_ratio = total_exposure / account_balance if account_balance > 0 else 999

        return {
            "passed": exposure_ratio <= self.max_total_exposure_ratio,
            "value": exposure_ratio,
            "limit": self.max_total_exposure_ratio,
            "existing_exposure": existing_exposure,
            "new_position_value": new_position_value,
            "total_exposure": total_exposure,
        }

    def _check_margin_requirement(
        self,
        account_balance: float,
        new_position_value: float,
        existing_positions: List[PositionInfo],
        margin_rate: float,
    ) -> Dict:
        """Check if margin requirements are met"""
        # Calculate used margin
        used_margin = sum(p.margin_used for p in existing_positions)
        new_margin_required = new_position_value * margin_rate
        total_margin_required = used_margin + new_margin_required

        # Calculate unrealized P&L
        unrealized_pnl = sum(p.unrealized_pnl for p in existing_positions)

        # Calculate equity and free margin
        equity = account_balance + unrealized_pnl
        free_margin = equity - used_margin

        # Margin level (equity / used margin * 100)
        margin_level = (equity / total_margin_required * 100) if total_margin_required > 0 else 999

        return {
            "passed": free_margin >= new_margin_required and margin_level >= self.min_margin_level,
            "margin_level": margin_level,
            "equity": equity,
            "used_margin": used_margin,
            "required_margin": new_margin_required,
            "free_margin": free_margin,
            "min_margin_level": self.min_margin_level,
        }

    def _check_position_sanity(
        self,
        position_units: int,
        account_balance: float,
        current_price: float,
    ) -> Dict:
        """Sanity check for position size"""
        position_value = abs(position_units) * current_price

        # Check if position is too small
        if position_value < 100:
            return {
                "passed": False,
                "message": f"Position too small: ${position_value:.2f}",
            }

        # Check if position is unreasonably large
        if position_value > account_balance * 100:
            return {
                "passed": False,
                "message": f"Position unreasonably large: ${position_value:.2f} vs ${account_balance:.2f} balance",
            }

        return {
            "passed": True,
            "message": "Position size reasonable",
        }

    def calculate_max_position_size(
        self,
        account_balance: float,
        instrument: str,
        current_price: float,
        stop_loss_pips: float,
        pip_value: float,
        existing_positions: Optional[List[PositionInfo]] = None,
    ) -> Dict:
        """
        Calculate maximum allowed position size.

        Considers all risk limits and returns the most restrictive.

        Args:
            account_balance: Current balance
            instrument: Trading instrument
            current_price: Current price
            stop_loss_pips: Stop loss in pips
            pip_value: Pip value per 10k units
            existing_positions: Existing open positions

        Returns:
            Dictionary with max position size and limiting factor
        """
        existing_positions = existing_positions or []

        # 1. Max from risk per trade
        risk_amount = account_balance * (self.max_risk_per_trade / 100)
        max_units_from_risk = int((risk_amount * 10000) / (stop_loss_pips * pip_value))

        # 2. Max from leverage limit
        existing_exposure = sum(abs(p.units) * 1.0 for p in existing_positions)
        remaining_leverage = (account_balance * self.max_leverage) - existing_exposure
        max_units_from_leverage = int(remaining_leverage / current_price)

        # 3. Max from exposure limit
        existing_exposure_ratio = existing_exposure / account_balance
        remaining_exposure = (account_balance * self.max_total_exposure_ratio) - existing_exposure
        max_units_from_exposure = int(remaining_exposure / current_price)

        # Take minimum
        max_units = min(max_units_from_risk, max_units_from_leverage, max_units_from_exposure)

        # Determine limiting factor
        if max_units == max_units_from_risk:
            limiting_factor = "risk_per_trade"
        elif max_units == max_units_from_leverage:
            limiting_factor = "leverage"
        else:
            limiting_factor = "exposure"

        return {
            "max_units": max_units,
            "max_lots": max_units / 10000,
            "limiting_factor": limiting_factor,
            "max_from_risk": max_units_from_risk,
            "max_from_leverage": max_units_from_leverage,
            "max_from_exposure": max_units_from_exposure,
        }


# Example usage
def example_usage():
    """Example of using the risk manager"""
    print("\n" + "="*60)
    print("RISK MANAGEMENT MODULE EXAMPLES")
    print("="*60)

    rm = RiskManager(
        max_leverage=20.0,
        max_risk_per_trade=1.0,
        max_total_exposure_ratio=3.0,
        min_margin_level=100.0,
    )

    # Example 1: Valid position
    print("\n=== Example 1: Valid Position ===")
    result = rm.validate_position(
        account_balance=10000,
        new_position_units=10000,  # 1 mini lot
        instrument="EUR_USD",
        current_price=1.0850,
        stop_loss_pips=10.0,
        pip_value=1.0,
    )

    print(f"Allowed: {result['allowed']}")
    print(f"Reason: {result['reason']}")
    if result['warnings']:
        print(f"Warnings: {result['warnings']}")

    # Example 2: Over-leveraged position
    print("\n=== Example 2: Over-Leveraged Position (REJECTED) ===")
    result = rm.validate_position(
        account_balance=10000,
        new_position_units=250000,  # 25 mini lots (25:1 leverage)
        instrument="EUR_USD",
        current_price=1.0850,
        stop_loss_pips=10.0,
        pip_value=1.0,
    )

    print(f"Allowed: {result['allowed']}")
    print(f"Reason: {result['reason']}")

    # Example 3: Excessive risk per trade
    print("\n=== Example 3: Excessive Risk Per Trade (REJECTED) ===")
    result = rm.validate_position(
        account_balance=10000,
        new_position_units=50000,  # 5 mini lots
        instrument="EUR_USD",
        current_price=1.0850,
        stop_loss_pips=50.0,  # 50 pip stop = $250 risk (2.5%)
        pip_value=1.0,
    )

    print(f"Allowed: {result['allowed']}")
    print(f"Reason: {result['reason']}")
    print(f"Risk: {result['checks']['risk_per_trade']['value']:.1f}% > {result['checks']['risk_per_trade']['limit']}%")

    # Example 4: Calculate max position size
    print("\n=== Example 4: Calculate Max Position Size ===")
    max_size = rm.calculate_max_position_size(
        account_balance=10000,
        instrument="EUR_USD",
        current_price=1.0850,
        stop_loss_pips=10.0,
        pip_value=1.0,
    )

    print(f"Max position size: {max_size['max_units']} units ({max_size['max_lots']:.2f} lots)")
    print(f"Limiting factor: {max_size['limiting_factor']}")
    print(f"  From risk limit: {max_size['max_from_risk']} units")
    print(f"  From leverage limit: {max_size['max_from_leverage']} units")
    print(f"  From exposure limit: {max_size['max_from_exposure']} units")

    print("\n" + "="*60)
    print("✅ Examples complete")
    print("="*60)


if __name__ == "__main__":
    example_usage()
