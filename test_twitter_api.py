"""
Test Twitter API Connection
Verifies that Twitter API credentials are working correctly
"""

import configparser
import requests
import json

def load_config():
    """Load configuration from v20.conf"""
    config = configparser.ConfigParser()
    config.read('v20.conf')
    return config

def test_twitter_api():
    """Test Twitter API connection with bearer token"""
    print("Loading Twitter API credentials from v20.conf...")
    config = load_config()

    bearer_token = config.get('twitter', 'bearer_token')
    api_key = config.get('twitter', 'api_key')

    print(f"✓ API Key: {api_key[:10]}...")
    print(f"✓ Bearer Token: {bearer_token[:20]}...")

    # Test 1: Recent Search (requires Basic or higher tier)
    print("\n=== Test 1: Recent Tweet Search ===")
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }

    # Search for forex-related tweets
    search_url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": "EURUSD OR forex OR currency trading",
        "max_results": 10,
        "tweet.fields": "created_at,lang,public_metrics"
    }

    try:
        response = requests.get(search_url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Successfully retrieved {len(data.get('data', []))} tweets")

            # Display first tweet
            if data.get('data'):
                tweet = data['data'][0]
                print(f"\nSample Tweet:")
                print(f"  Text: {tweet.get('text', '')[:100]}...")
                print(f"  Created: {tweet.get('created_at')}")
                print(f"  Likes: {tweet.get('public_metrics', {}).get('like_count', 0)}")

        elif response.status_code == 403:
            print("✗ Error 403: Access Forbidden")
            print("This usually means:")
            print("  1. Free tier doesn't have access to recent search")
            print("  2. You need to upgrade to Basic tier ($100/month)")
            print("  3. Or use the legacy v1.1 standard search endpoint")

        elif response.status_code == 401:
            print("✗ Error 401: Unauthorized")
            print("Bearer token is invalid or expired")
            print("Regenerate your keys at: https://developer.twitter.com/")

        else:
            print(f"✗ Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"✗ Connection Error: {e}")

    # Test 2: User Lookup (free tier)
    print("\n=== Test 2: User Lookup (Free Tier Endpoint) ===")
    user_url = "https://api.twitter.com/2/users/by/username/elonmusk"

    try:
        response = requests.get(user_url, headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Successfully retrieved user data")
            print(f"  Username: @{data['data']['username']}")
            print(f"  Name: {data['data']['name']}")
            print(f"  ID: {data['data']['id']}")

        elif response.status_code == 401:
            print("✗ Error 401: Unauthorized - Invalid bearer token")

        else:
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"✗ Connection Error: {e}")

    # Test 3: Check Rate Limits
    print("\n=== Test 3: Rate Limit Status ===")
    try:
        if 'x-rate-limit-limit' in response.headers:
            print(f"Rate Limit: {response.headers.get('x-rate-limit-limit')}")
            print(f"Remaining: {response.headers.get('x-rate-limit-remaining')}")
            print(f"Reset: {response.headers.get('x-rate-limit-reset')}")
        else:
            print("No rate limit headers in response")
    except:
        print("Could not check rate limits")

    print("\n=== Summary ===")
    print("✓ Twitter API credentials are configured in v20.conf")
    print("\nNote: Free tier has limited access to endpoints.")
    print("For forex sentiment analysis, you may need:")
    print("  - Basic tier ($100/month) for recent search")
    print("  - OR use Twitter v1.1 standard search (7-day history)")
    print("  - OR use alternative sources (Reddit, StockTwits)")

if __name__ == "__main__":
    test_twitter_api()
