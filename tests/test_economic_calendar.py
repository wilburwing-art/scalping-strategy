"""
Test script for Economic Calendar integration

Usage:
    export TRADING_ECONOMICS_API_KEY="your_key"
    uv run test_economic_calendar.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from economic_calendar import EconomicCalendar, NewsImpact

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def test_fetch_events():
    """Test fetching economic events"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Fetch Upcoming Economic Events")
    logger.info("="*60)

    api_key = os.getenv("TRADING_ECONOMICS_API_KEY")
    if not api_key:
        logger.error("❌ TRADING_ECONOMICS_API_KEY not set")
        logger.info("Get free API key at: https://tradingeconomics.com/analytics/api/")
        return False

    calendar = EconomicCalendar(api_key=api_key)

    try:
        # Fetch next 24 hours
        events = await calendar.fetch_upcoming_events(
            hours_ahead=24,
            min_impact=NewsImpact.MEDIUM,
        )

        logger.info(f"\n✓ Fetched {len(events)} upcoming economic events\n")

        if events:
            logger.info("Sample events:")
            for event in events[:5]:
                logger.info(f"  - {event}")
        else:
            logger.warning("⚠️  No upcoming events in next 24 hours")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to fetch events: {e}")
        return False

    finally:
        await calendar.close()


async def test_critical_events():
    """Test fetching critical events"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Identify Critical Events")
    logger.info("="*60)

    api_key = os.getenv("TRADING_ECONOMICS_API_KEY")
    if not api_key:
        return False

    calendar = EconomicCalendar(api_key=api_key)

    try:
        # First fetch all events
        await calendar.fetch_upcoming_events(hours_ahead=48)

        # Get critical events
        critical = calendar.get_upcoming_critical_events(hours_ahead=48)

        if critical:
            logger.info(f"\n⚠️  Found {len(critical)} CRITICAL events in next 48 hours:\n")
            for event in critical:
                time_str = event.timestamp.strftime("%Y-%m-%d %H:%M UTC")
                logger.warning(f"  {event.event_name} ({event.country}) @ {time_str}")
            logger.info("")
        else:
            logger.info("\n✓ No critical events in next 48 hours")

        return True

    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

    finally:
        await calendar.close()


async def test_safety_check():
    """Test is_safe_to_trade logic"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Trading Safety Check")
    logger.info("="*60)

    api_key = os.getenv("TRADING_ECONOMICS_API_KEY")
    if not api_key:
        return False

    calendar = EconomicCalendar(api_key=api_key)

    try:
        # Fetch events first
        await calendar.fetch_upcoming_events(hours_ahead=24)

        # Test major instruments
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"]

        logger.info(f"\nChecking safety for major instruments:\n")

        safe_count = 0
        blocked_count = 0

        for instrument in instruments:
            is_safe, blocking_event = calendar.is_safe_to_trade(
                instrument,
                buffer_minutes_before=30,
                buffer_minutes_after=60,
            )

            if is_safe:
                logger.info(f"  ✓ {instrument}: SAFE TO TRADE")
                safe_count += 1
            else:
                if blocking_event:
                    minutes_until = (blocking_event.timestamp - datetime.utcnow()).total_seconds() / 60
                    logger.warning(
                        f"  ✗ {instrument}: BLOCKED - {blocking_event.event_name} "
                        f"({blocking_event.impact.value}) in {minutes_until:.0f} min"
                    )
                blocked_count += 1

        logger.info(f"\n📊 Results: {safe_count} safe, {blocked_count} blocked")

        return True

    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

    finally:
        await calendar.close()


async def test_cache():
    """Test caching mechanism"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Caching Mechanism")
    logger.info("="*60)

    api_key = os.getenv("TRADING_ECONOMICS_API_KEY")
    if not api_key:
        return False

    calendar = EconomicCalendar(api_key=api_key, cache_duration_minutes=60)

    try:
        import time

        # First fetch
        logger.info("First fetch (should call API)...")
        start = time.time()
        events1 = await calendar.fetch_upcoming_events(hours_ahead=24)
        time1 = time.time() - start
        logger.info(f"  Took {time1:.2f}s, fetched {len(events1)} events")

        # Second fetch (should use cache)
        logger.info("\nSecond fetch (should use cache)...")
        start = time.time()
        events2 = await calendar.fetch_upcoming_events(hours_ahead=24)
        time2 = time.time() - start
        logger.info(f"  Took {time2:.2f}s, fetched {len(events2)} events")

        if time2 < time1 * 0.1:  # Cache should be 10x+ faster
            logger.info(f"\n✓ Cache working! Second fetch was {time1/time2:.1f}x faster")
        else:
            logger.warning("\n⚠️  Cache may not be working properly")

        return True

    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

    finally:
        await calendar.close()


async def run_all_tests():
    """Run all tests"""
    logger.info("\n" + "="*60)
    logger.info("🧪 ECONOMIC CALENDAR INTEGRATION TESTS")
    logger.info("="*60 + "\n")

    if not os.getenv("TRADING_ECONOMICS_API_KEY"):
        logger.error("❌ TRADING_ECONOMICS_API_KEY environment variable not set\n")
        logger.info("To run tests:")
        logger.info("1. Get free API key at: https://tradingeconomics.com/analytics/api/")
        logger.info("2. Run: export TRADING_ECONOMICS_API_KEY='your_key'")
        logger.info("3. Run: uv run test_economic_calendar.py\n")
        return

    results = []

    # Run tests
    results.append(("Fetch Events", await test_fetch_events()))
    results.append(("Critical Events", await test_critical_events()))
    results.append(("Safety Check", await test_safety_check()))
    results.append(("Cache", await test_cache()))

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60 + "\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {status}: {name}")

    logger.info(f"\n{passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All tests passed! Economic calendar integration working correctly.\n")
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed. Check logs above.\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
