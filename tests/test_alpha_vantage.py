"""
Test Alpha Vantage API Connection
Verifies API key and demonstrates economic calendar + news sentiment endpoints
"""

import configparser
import requests
import json
from datetime import datetime

def load_config():
    """Load configuration from v20.conf"""
    config = configparser.ConfigParser()
    config.read('v20.conf')
    return config

def test_news_sentiment(api_key):
    """Test News & Sentiment API - shows market sentiment for forex"""
    print("\n=== Test 1: News Sentiment API ===")
    print("Getting latest forex news with sentiment scores...")

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": "FOREX:EUR,FOREX:USD,FOREX:GBP",
        "apikey": api_key,
        "limit": 5
    }

    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if "feed" in data:
                print(f"✓ Retrieved {len(data['feed'])} news articles")

                # Show first article
                if data['feed']:
                    article = data['feed'][0]
                    print(f"\nSample Article:")
                    print(f"  Title: {article['title'][:80]}...")
                    print(f"  Source: {article.get('source', 'Unknown')}")
                    print(f"  Published: {article.get('time_published', 'Unknown')}")
                    print(f"  Overall Sentiment: {article.get('overall_sentiment_label', 'N/A')}")
                    print(f"  Sentiment Score: {article.get('overall_sentiment_score', 'N/A')}")

                    # Show ticker-specific sentiment
                    if 'ticker_sentiment' in article:
                        print(f"\n  Ticker Sentiments:")
                        for ticker in article['ticker_sentiment'][:3]:
                            print(f"    {ticker['ticker']}: {ticker['ticker_sentiment_label']} ({ticker['ticker_sentiment_score']})")

                return True
            else:
                print(f"✗ Unexpected response format: {data}")
                return False

        else:
            print(f"✗ Error: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Connection Error: {e}")
        return False

def test_forex_data(api_key):
    """Test Forex Exchange Rate API"""
    print("\n=== Test 2: Forex Exchange Rate API ===")
    print("Getting current EURUSD exchange rate...")

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": "EUR",
        "to_currency": "USD",
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if "Realtime Currency Exchange Rate" in data:
                rate_data = data["Realtime Currency Exchange Rate"]
                print(f"✓ Current EURUSD Rate")
                print(f"  Rate: {rate_data['5. Exchange Rate']}")
                print(f"  Bid: {rate_data['8. Bid Price']}")
                print(f"  Ask: {rate_data['9. Ask Price']}")
                print(f"  Last Updated: {rate_data['6. Last Refreshed']}")
                return True
            else:
                print(f"✗ Unexpected response: {data}")
                return False

        else:
            print(f"✗ Error: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Connection Error: {e}")
        return False

def test_economic_calendar(api_key):
    """Test Economic Calendar via Market News API"""
    print("\n=== Test 3: Economic Events (via Market News) ===")
    print("Getting economic calendar events...")

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "topics": "economy_macro,economy_monetary",
        "apikey": api_key,
        "limit": 5
    }

    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if "feed" in data:
                print(f"✓ Retrieved {len(data['feed'])} economic news items")

                if data['feed']:
                    print(f"\nRecent Economic Events:")
                    for i, item in enumerate(data['feed'][:3], 1):
                        print(f"\n  {i}. {item['title'][:70]}...")
                        print(f"     Time: {item.get('time_published', 'Unknown')}")
                        print(f"     Sentiment: {item.get('overall_sentiment_label', 'N/A')}")

                return True
            else:
                print(f"✗ No feed data found")
                return False

        else:
            print(f"✗ Error: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Connection Error: {e}")
        return False

def test_rate_limit(api_key):
    """Check rate limit status"""
    print("\n=== Test 4: Rate Limit Check ===")

    # Make a simple API call to check headers
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": "EURUSD",
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params)

        # Alpha Vantage doesn't return rate limit headers, but we can infer from response
        if "Note" in response.text:
            print("⚠️  Rate Limit Warning:")
            print("  Alpha Vantage has a limit of 500 calls/day (25 calls/min)")
            print("  If you see this message, you've hit the rate limit")
            print(f"  Response: {response.text[:200]}")
        else:
            print("✓ Rate limit OK")
            print("  Free tier: 500 calls/day, 25 calls/minute")
            print("  Current usage: Unknown (Alpha Vantage doesn't expose this)")

    except Exception as e:
        print(f"✗ Error checking rate limit: {e}")

def main():
    """Run all API tests"""
    print("=" * 60)
    print("Alpha Vantage API Test Suite")
    print("=" * 60)

    # Load config
    print("\nLoading configuration from v20.conf...")
    config = load_config()

    try:
        api_key = config.get('alpha_vantage', 'api_key')
        print(f"✓ API Key loaded: {api_key[:8]}...")
    except Exception as e:
        print(f"✗ Error loading API key: {e}")
        return

    # Run tests
    results = {
        "News Sentiment": test_news_sentiment(api_key),
        "Forex Data": test_forex_data(api_key),
        "Economic Calendar": test_economic_calendar(api_key),
    }

    test_rate_limit(api_key)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")

    print("\n=== Usage Recommendations ===")
    print("✓ News Sentiment: Use for market-moving news confirmation")
    print("✓ Forex Data: Backup data source (OANDA is primary)")
    print("✓ Economic Calendar: Check before major events (NFP, Fed, etc.)")
    print("\n⚠️  Rate Limits:")
    print("  - 500 API calls per day (free tier)")
    print("  - 25 calls per minute")
    print("  - Cache results to avoid hitting limits")
    print("\n💡 Integration Tips:")
    print("  1. Call News Sentiment every 30 minutes for latest news")
    print("  2. Cache economic calendar daily (doesn't change often)")
    print("  3. Use sentiment as confirmation signal, not primary")
    print("  4. Avoid trading 30 min before/after high-impact news")

if __name__ == "__main__":
    main()
