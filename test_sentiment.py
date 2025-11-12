"""
Test script for Sentiment Analysis

Tests sentiment analyzer with real APIs or mock data.

Usage:
    # With real APIs (requires keys)
    export OPENAI_API_KEY="sk-..."
    export TWITTER_BEARER_TOKEN="..."  # Optional
    export REDDIT_CLIENT_ID="..."      # Optional
    export REDDIT_CLIENT_SECRET="..."  # Optional
    uv run test_sentiment.py

    # With mock data (no APIs needed)
    uv run test_sentiment.py --mock
"""

import asyncio
import logging
import os
import sys
import argparse
from datetime import datetime

from sentiment_analyzer import SentimentAnalyzer, SentimentData

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


async def test_sentiment_fetch(analyzer: SentimentAnalyzer, instruments: list):
    """Test fetching sentiment for multiple instruments"""
    print("\n" + "="*60)
    print("TEST 1: Sentiment Fetching")
    print("="*60)

    results = []

    for instrument in instruments:
        print(f"\nAnalyzing {instrument}...")
        try:
            sentiment = await analyzer.get_sentiment(instrument, lookback_hours=6)

            results.append((instrument, sentiment, True))

            print(f"  ✓ Sentiment: {sentiment.sentiment_score:+.2f}")
            print(f"  Mentions: {sentiment.total_mentions}")
            print(f"  Volume Percentile: {sentiment.mention_volume_percentile:.0f}th")

            if sentiment.twitter_mentions > 0:
                print(f"  Twitter: {sentiment.twitter_sentiment:+.2f} ({sentiment.twitter_mentions} tweets)")
            if sentiment.reddit_mentions > 0:
                print(f"  Reddit: {sentiment.reddit_sentiment:+.2f} ({sentiment.reddit_mentions} posts)")
            if sentiment.stocktwits_mentions > 0:
                print(f"  StockTwits: {sentiment.stocktwits_sentiment:+.2f} ({sentiment.stocktwits_mentions} messages)")

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            results.append((instrument, None, False))

    # Summary
    successes = sum(1 for _, _, success in results if success)
    print(f"\n✓ {successes}/{len(instruments)} instruments analyzed successfully")

    return results


async def test_caching(analyzer: SentimentAnalyzer):
    """Test sentiment caching"""
    print("\n" + "="*60)
    print("TEST 2: Caching Mechanism")
    print("="*60)

    instrument = "EUR_USD"
    import time

    # First fetch
    print(f"\nFirst fetch for {instrument}...")
    start = time.time()
    sentiment1 = await analyzer.get_sentiment(instrument, use_cache=False)
    time1 = time.time() - start
    print(f"  Took {time1:.2f}s")

    # Second fetch (should use cache)
    print(f"\nSecond fetch for {instrument} (should use cache)...")
    start = time.time()
    sentiment2 = await analyzer.get_sentiment(instrument, use_cache=True)
    time2 = time.time() - start
    print(f"  Took {time2:.2f}s")

    # Check if cache worked
    if time2 < time1 * 0.1:  # Cache should be 10x+ faster
        print(f"\n✓ Cache working! Second fetch was {time1/time2:.1f}x faster")
    else:
        print(f"\n⚠️  Cache may not be working (expected much faster)")

    # Verify data is the same
    if sentiment1.total_mentions == sentiment2.total_mentions:
        print("✓ Cached data matches original")
    else:
        print("⚠️  Cached data differs from original")


async def test_signal_detection(analyzer: SentimentAnalyzer):
    """Test signal detection logic"""
    print("\n" + "="*60)
    print("TEST 3: Signal Detection")
    print("="*60)

    instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]

    for instrument in instruments:
        sentiment = await analyzer.get_sentiment(instrument, lookback_hours=6)

        print(f"\n{instrument}:")
        print(f"  Sentiment Score: {sentiment.sentiment_score:+.2f}")
        print(f"  Net Sentiment: {sentiment.net_sentiment.name}")
        print(f"  High Conviction: {'YES' if sentiment.is_high_conviction else 'NO'}")
        print(f"  Contrarian Signal: {'YES' if sentiment.is_contrarian_signal else 'NO'}")

        # Trading recommendations
        if sentiment.is_high_conviction:
            direction = "BUY" if sentiment.sentiment_score > 0 else "SELL"
            print(f"  📈 RECOMMENDATION: {direction} (high conviction)")
        elif sentiment.is_contrarian_signal:
            direction = "SELL" if sentiment.sentiment_score > 0 else "BUY"
            print(f"  📉 CONTRARIAN: {direction} (fade the crowd)")
        else:
            print(f"  ⏸️  No strong signal")


async def test_with_mock_data():
    """Test with mock data (no API calls)"""
    print("\n" + "="*60)
    print("MOCK TEST: Sentiment Analysis (No API calls)")
    print("="*60)

    # Create mock sentiment data
    mock_sentiment = SentimentData(
        instrument="EUR_USD",
        timestamp=datetime.utcnow(),
        total_mentions=45,
        positive_count=30,
        negative_count=10,
        neutral_count=5,
        sentiment_score=0.44,  # (30-10)/45
        sentiment_strength=0.44,
        mention_volume_percentile=75.0,
        twitter_sentiment=0.5,
        reddit_sentiment=0.35,
        stocktwits_sentiment=0.42,
        twitter_mentions=25,
        reddit_mentions=12,
        stocktwits_mentions=8,
    )

    print(f"\nMock Sentiment Data:")
    print(f"  {mock_sentiment}")
    print(f"  Net Sentiment: {mock_sentiment.net_sentiment.name}")
    print(f"  High Conviction: {mock_sentiment.is_high_conviction}")
    print(f"  Contrarian Signal: {mock_sentiment.is_contrarian_signal}")

    print("\n✓ Mock data test successful")


async def run_all_tests(mock: bool = False):
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 SENTIMENT ANALYSIS TEST SUITE")
    print("="*60)

    if mock:
        await test_with_mock_data()
        return

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
    reddit_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not openai_key:
        logger.error("\n❌ OPENAI_API_KEY not set")
        logger.info("Set it with: export OPENAI_API_KEY='sk-...'")
        logger.info("Or run with --mock flag for testing without APIs")
        return

    # Initialize analyzer
    analyzer = SentimentAnalyzer(
        openai_key=openai_key,
        twitter_bearer_token=twitter_bearer,
        reddit_client_id=reddit_id,
        reddit_client_secret=reddit_secret,
    )

    # Run tests
    instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]

    try:
        # Test 1: Fetch sentiment
        results = await test_sentiment_fetch(analyzer, instruments)

        # Test 2: Caching (only if we got results)
        if any(success for _, _, success in results):
            await test_caching(analyzer)

        # Test 3: Signal detection
        await test_signal_detection(analyzer)

        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)

        # Summary
        successes = sum(1 for _, _, success in results if success)
        if successes == len(instruments):
            print(f"\n🎉 Perfect! All {successes} instruments analyzed successfully")
        elif successes > 0:
            print(f"\n⚠️  {successes}/{len(instruments)} instruments analyzed (some failed)")
        else:
            print(f"\n❌ No instruments analyzed successfully")
            print("Check API credentials and internet connection")

    finally:
        await analyzer.close()


def main():
    parser = argparse.ArgumentParser(description="Test Sentiment Analysis")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock data (no API calls)")

    args = parser.parse_args()

    asyncio.run(run_all_tests(mock=args.mock))


if __name__ == "__main__":
    main()
