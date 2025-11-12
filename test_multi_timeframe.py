"""
Test Suite for Multi-Timeframe Data Provider

Tests the parallel fetching, caching, and formatting of multi-timeframe data.
"""

import asyncio
import configparser
from datetime import datetime
from v20 import Context
from multi_timeframe_data import MultiTimeframeDataProvider


def test_basic_fetching():
    """Test basic multi-timeframe data fetching"""
    print("\n=== Test 1: Basic Multi-Timeframe Fetching ===")

    # Load config
    config = configparser.ConfigParser()
    config.read("v20.conf")

    if not config.has_section("practice"):
        print("⚠️  No v20.conf found - skipping API tests")
        return False

    ctx = Context(
        config["practice"]["hostname"],
        config["practice"]["token"],
        application="MultiTimeframeTest"
    )
    account_id = config["practice"]["account_id"]

    # Create provider
    provider = MultiTimeframeDataProvider(ctx, account_id, enable_caching=False)

    async def fetch_data():
        # Fetch all timeframes
        data = await provider.get_multi_timeframe_data("EUR_USD")

        print("\n📊 Fetched timeframes:")
        for tf, candles in data.items():
            print(f"  {tf}: {len(candles)} candles")
            if len(candles) == 0:
                print(f"    ⚠️  No candles returned for {tf}")
                return False

        # Verify all timeframes present
        expected_tfs = ["1m", "5m", "15m", "1H", "4H"]
        for tf in expected_tfs:
            if tf not in data:
                print(f"    ❌ Missing timeframe: {tf}")
                return False

        print("✅ All timeframes fetched successfully")
        return True

    result = asyncio.run(fetch_data())
    return result


def test_agent_formatting():
    """Test formatting for agent consumption"""
    print("\n=== Test 2: Agent Data Formatting ===")

    config = configparser.ConfigParser()
    config.read("v20.conf")

    if not config.has_section("practice"):
        print("⚠️  No v20.conf found - skipping API tests")
        return False

    ctx = Context(
        config["practice"]["hostname"],
        config["practice"]["token"],
        application="MultiTimeframeTest"
    )
    account_id = config["practice"]["account_id"]

    provider = MultiTimeframeDataProvider(ctx, account_id)

    async def fetch_and_format():
        # Fetch data
        data = await provider.get_multi_timeframe_data("EUR_USD")

        # Format for agents
        formatted = provider.format_for_agents(data)

        print("\n📊 Formatted data structure:")
        for tf, ohlcv in formatted.items():
            print(f"  {tf}:")
            print(f"    Keys: {list(ohlcv.keys())}")
            print(f"    Data points: {len(ohlcv['close'])}")

            if ohlcv['close']:
                print(f"    Latest close: {ohlcv['close'][-1]:.5f}")
            else:
                print(f"    ⚠️  No close prices")
                return False

            # Verify structure
            required_keys = ["time", "open", "high", "low", "close", "volume"]
            for key in required_keys:
                if key not in ohlcv:
                    print(f"    ❌ Missing key: {key}")
                    return False
                if len(ohlcv[key]) != len(ohlcv['close']):
                    print(f"    ❌ Length mismatch for {key}")
                    return False

        print("✅ Agent formatting successful")
        return True

    result = asyncio.run(fetch_and_format())
    return result


def test_caching():
    """Test caching mechanism"""
    print("\n=== Test 3: Caching ===")

    config = configparser.ConfigParser()
    config.read("v20.conf")

    if not config.has_section("practice"):
        print("⚠️  No v20.conf found - skipping API tests")
        return False

    ctx = Context(
        config["practice"]["hostname"],
        config["practice"]["token"],
        application="MultiTimeframeTest"
    )
    account_id = config["practice"]["account_id"]

    provider = MultiTimeframeDataProvider(
        ctx,
        account_id,
        enable_caching=True,
        cache_duration_seconds=60
    )

    async def test_cache():
        import time

        # First fetch (should hit API)
        print("\n🔄 First fetch (should hit API)...")
        start = time.time()
        data1 = await provider.get_multi_timeframe_data("EUR_USD")
        elapsed1 = time.time() - start
        print(f"  Time: {elapsed1:.2f}s")

        # Second fetch (should use cache)
        print("\n🔄 Second fetch (should use cache)...")
        start = time.time()
        data2 = await provider.get_multi_timeframe_data("EUR_USD")
        elapsed2 = time.time() - start
        print(f"  Time: {elapsed2:.2f}s")

        # Cache should be significantly faster
        if elapsed2 < elapsed1 * 0.1:  # At least 10x faster
            print(f"✅ Cache working (speedup: {elapsed1/elapsed2:.1f}x)")
            return True
        else:
            print(f"⚠️  Cache may not be working (speedup: {elapsed1/elapsed2:.1f}x)")
            return False

    result = asyncio.run(test_cache())
    return result


def test_current_price():
    """Test current price fetching"""
    print("\n=== Test 4: Current Price Fetching ===")

    config = configparser.ConfigParser()
    config.read("v20.conf")

    if not config.has_section("practice"):
        print("⚠️  No v20.conf found - skipping API tests")
        return False

    ctx = Context(
        config["practice"]["hostname"],
        config["practice"]["token"],
        application="MultiTimeframeTest"
    )
    account_id = config["practice"]["account_id"]

    provider = MultiTimeframeDataProvider(ctx, account_id)

    # Fetch current price
    price = provider.get_current_price("EUR_USD")

    if price is None:
        print("❌ Failed to fetch current price")
        return False

    print("\n💰 Current price:")
    print(f"  Bid: {price['bid']:.5f}")
    print(f"  Ask: {price['ask']:.5f}")
    print(f"  Spread: {price['spread']:.5f} ({price['spread']*10000:.1f} pips)")
    print(f"  Midpoint: {price['midpoint']:.5f}")
    print(f"  Time: {price['time']}")

    # Validate structure
    required_keys = ["instrument", "bid", "ask", "spread", "midpoint", "time"]
    for key in required_keys:
        if key not in price:
            print(f"❌ Missing key: {key}")
            return False

    # Validate spread is positive and reasonable
    if price['spread'] <= 0:
        print("❌ Invalid spread (negative or zero)")
        return False

    if price['spread'] > 0.01:  # More than 100 pips is suspicious
        print("⚠️  Unusually large spread")
        return False

    print("✅ Current price fetching successful")
    return True


def test_single_timeframe():
    """Test synchronous single timeframe fetching"""
    print("\n=== Test 5: Single Timeframe Fetching ===")

    config = configparser.ConfigParser()
    config.read("v20.conf")

    if not config.has_section("practice"):
        print("⚠️  No v20.conf found - skipping API tests")
        return False

    ctx = Context(
        config["practice"]["hostname"],
        config["practice"]["token"],
        application="MultiTimeframeTest"
    )
    account_id = config["practice"]["account_id"]

    provider = MultiTimeframeDataProvider(ctx, account_id)

    # Fetch single timeframe
    candles = provider.get_single_timeframe("EUR_USD", "5m")

    if not candles:
        print("❌ No candles returned")
        return False

    print(f"\n📊 Fetched {len(candles)} 5m candles")

    # Check first and last candle
    if len(candles) > 0:
        first = candles[0]
        last = candles[-1]
        print(f"  First: {first.time}")
        print(f"  Last: {last.time}")

    print("✅ Single timeframe fetching successful")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("MULTI-TIMEFRAME DATA PROVIDER TEST SUITE")
    print("="*60)

    tests = [
        test_basic_fetching,
        test_agent_formatting,
        test_caching,
        test_current_price,
        test_single_timeframe,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"\n❌ {test_func.__name__} failed with exception:")
            print(f"  {e}")
            results.append((test_func.__name__, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
