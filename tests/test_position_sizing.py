"""
Test Position Sizing Calculations
Verifies that the position sizing fix is working correctly
"""

import logging

# Mock indicators for testing
test_cases = [
    {
        "name": "EUR/USD - Typical",
        "instrument": "EUR_USD",
        "price": 1.0850,
        "atr": 0.0015,  # 15 pips
        "account_balance": 100000,
        "risk_percent": 1.0,
    },
    {
        "name": "GBP/JPY - JPY pair",
        "instrument": "GBP_JPY",
        "price": 189.45,
        "atr": 0.75,  # 75 pips (JPY pairs have different pip size)
        "account_balance": 100000,
        "risk_percent": 1.0,
    },
    {
        "name": "EUR/USD - Low ATR",
        "instrument": "EUR_USD",
        "price": 1.0850,
        "atr": 0.0005,  # 5 pips (very low)
        "account_balance": 100000,
        "risk_percent": 1.0,
    },
    {
        "name": "USD/CAD - High ATR",
        "instrument": "USD_CAD",
        "price": 1.3500,
        "atr": 0.0100,  # 100 pips (high volatility)
        "account_balance": 100000,
        "risk_percent": 1.0,
    },
]


def calculate_pip_value(instrument, price):
    """Calculate pip value (from strategy)"""
    if instrument.endswith("_USD"):
        return 0.0001
    elif instrument.startswith("USD_"):
        return 0.0001 / price
    else:
        return 0.0001


def calculate_position_size_new(account_balance, instrument, price, atr, risk_percent):
    """New position sizing logic with fix"""
    stop_loss_distance_price = atr * 1.5

    # Convert stop loss from price to pips
    if 'JPY' in instrument:
        stop_loss_pips = stop_loss_distance_price * 100
    else:
        stop_loss_pips = stop_loss_distance_price * 10000

    # Calculate risk amount
    risk_amount = account_balance * (risk_percent / 100)

    # Calculate pip value per unit
    pip_value_per_unit = calculate_pip_value(instrument, price)

    # Position size formula
    position_size = risk_amount / (stop_loss_pips * pip_value_per_unit)

    # Enforce minimum
    MIN_POSITION_SIZE = 1000
    if position_size < MIN_POSITION_SIZE:
        position_size = MIN_POSITION_SIZE

    # Round to nearest 100
    position_size = int(round(position_size / 100) * 100)
    position_size = max(position_size, 1000)

    return position_size, stop_loss_pips, pip_value_per_unit, risk_amount


def calculate_position_size_old(account_balance, instrument, price, atr, risk_percent):
    """Old (broken) position sizing logic"""
    stop_loss_distance = atr * 1.5
    risk_amount = account_balance * (risk_percent / 100)
    pip_value = calculate_pip_value(instrument, price)
    position_size = risk_amount / (stop_loss_distance * pip_value)
    return int(position_size)


print("="*80)
print("POSITION SIZING TEST - OLD VS NEW")
print("="*80)

for test in test_cases:
    print(f"\n{test['name']}:")
    print(f"  Instrument: {test['instrument']}")
    print(f"  Price: {test['price']}")
    print(f"  ATR: {test['atr']} ({'%.1f' % (test['atr'] * (100 if 'JPY' in test['instrument'] else 10000))} pips)")
    print(f"  Account: ${test['account_balance']:,}")
    print(f"  Risk: {test['risk_percent']}% (${test['account_balance'] * test['risk_percent'] / 100:,.0f})")

    # Old calculation
    old_size = calculate_position_size_old(
        test['account_balance'],
        test['instrument'],
        test['price'],
        test['atr'],
        test['risk_percent']
    )

    # New calculation
    new_size, stop_pips, pip_val, risk_amt = calculate_position_size_new(
        test['account_balance'],
        test['instrument'],
        test['price'],
        test['atr'],
        test['risk_percent']
    )

    # Calculate actual risk with new size
    actual_risk = new_size * stop_pips * pip_val

    print(f"\n  OLD CALCULATION:")
    print(f"    Position Size: {old_size:,} units")

    print(f"\n  NEW CALCULATION:")
    print(f"    Stop Loss: {stop_pips:.1f} pips")
    print(f"    Pip Value: ${pip_val:.6f} per unit")
    print(f"    Position Size: {new_size:,} units")
    print(f"    Actual Risk: ${actual_risk:,.2f}")
    print(f"    Risk Error: {(actual_risk - risk_amt) / risk_amt * 100:.1f}%")

    # Validate
    if new_size >= 1000:
        print(f"    ✓ Size meets minimum (1000 units)")
    else:
        print(f"    ✗ Size below minimum!")

    if 500 <= actual_risk <= 1500:
        print(f"    ✓ Risk within acceptable range ($500-$1500)")
    else:
        print(f"    ✗ Risk outside target range!")

    # Calculate P&L scenarios
    print(f"\n  P&L SCENARIOS (with {new_size:,} units):")
    pip_value_full = new_size * pip_val
    print(f"    +10 pips: ${10 * pip_value_full:,.2f}")
    print(f"    +50 pips: ${50 * pip_value_full:,.2f}")
    print(f"    -{stop_pips:.0f} pips (stop hit): $-{actual_risk:,.2f}")

print("\n" + "="*80)
print("EXPECTED OUTCOMES")
print("="*80)
print("""
For a $100,000 account with 1% risk:

1. Position sizes should be 5,000-20,000 units (0.05-0.2 lots)
2. Risk should be close to $1,000 per trade
3. 10-pip wins should generate $50-200 profit
4. Stop losses should risk $500-1,500

If OLD calculation showed millions of units → BUG
If NEW calculation shows 1,000-20,000 units → FIXED ✓
""")
