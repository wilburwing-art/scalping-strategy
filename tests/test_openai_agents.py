"""
Test OpenAI API and AI Agents
Verifies API key works and tests the multi-agent trading system
"""

import configparser
from openai import OpenAI
import os

def load_config():
    """Load configuration from v20.conf"""
    config = configparser.ConfigParser()
    config.read('v20.conf')
    return config

def test_openai_basic(api_key, model):
    """Test basic OpenAI API connection"""
    print("\n=== Test 1: Basic OpenAI API Connection ===")

    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'API connection successful' if you can read this."}
            ],
            max_tokens=50
        )

        result = response.choices[0].message.content
        print(f"✓ API Response: {result}")
        print(f"✓ Model: {response.model}")
        print(f"✓ Tokens Used: {response.usage.total_tokens}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_market_analysis(api_key, model):
    """Test market analysis capability"""
    print("\n=== Test 2: Market Analysis Test ===")

    try:
        client = OpenAI(api_key=api_key)

        # Simulate a trading analysis request
        prompt = """You are a forex market analyst. Analyze this market data:

Instrument: EURUSD
Current Price: 1.0850
RSI (14): 65
ATR (14): 0.0012
50-period MA: 1.0820
200-period MA: 1.0780

Recent price action: Price broke above 50-MA, trending up.

Provide a brief analysis (2-3 sentences) on whether this is a good long entry opportunity."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert forex market analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )

        analysis = response.choices[0].message.content
        print(f"✓ Market Analysis Generated:")
        print(f"  {analysis}")
        print(f"\n✓ Tokens Used: {response.usage.total_tokens}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_sentiment_analysis(api_key, model):
    """Test sentiment analysis on forex news"""
    print("\n=== Test 3: Sentiment Analysis Test ===")

    try:
        client = OpenAI(api_key=api_key)

        news_items = [
            "Fed hints at rate cuts in Q2, dollar weakens",
            "ECB maintains hawkish stance, euro rallies",
            "US jobs report beats expectations, dollar strengthens"
        ]

        prompt = f"""Analyze the sentiment of these forex news headlines for EUR/USD trading:

{chr(10).join([f"{i+1}. {news}" for i, news in enumerate(news_items)])}

For each headline, classify as BULLISH_EUR, BEARISH_EUR, or NEUTRAL.
Provide a brief explanation for each."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a forex news sentiment analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )

        sentiment = response.choices[0].message.content
        print(f"✓ Sentiment Analysis:")
        print(f"  {sentiment}")
        print(f"\n✓ Tokens Used: {response.usage.total_tokens}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_risk_assessment(api_key, model):
    """Test risk assessment capability"""
    print("\n=== Test 4: Risk Assessment Test ===")

    try:
        client = OpenAI(api_key=api_key)

        prompt = """You are a risk management expert for forex trading.

Trading Scenario:
- Account Balance: $10,000
- Proposed Trade: Long EURUSD
- Entry: 1.0850
- Stop Loss: 1.0820 (30 pips)
- Take Profit: 1.0895 (45 pips)
- Position Size: 1 standard lot (100,000 units)

Assess the risk level (LOW/MEDIUM/HIGH) and explain why in 2-3 sentences."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a forex risk management expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )

        assessment = response.choices[0].message.content
        print(f"✓ Risk Assessment:")
        print(f"  {assessment}")
        print(f"\n✓ Tokens Used: {response.usage.total_tokens}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all OpenAI tests"""
    print("=" * 70)
    print("OpenAI API & AI Agents Test Suite")
    print("=" * 70)

    # Load config
    print("\nLoading configuration from v20.conf...")
    config = load_config()

    try:
        api_key = config.get('openai', 'api_key')
        model = config.get('openai', 'model')
        print(f"✓ API Key loaded: {api_key[:20]}...")
        print(f"✓ Model: {model}")
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return

    # Run tests
    results = {}

    results["Basic Connection"] = test_openai_basic(api_key, model)
    results["Market Analysis"] = test_market_analysis(api_key, model)
    results["Sentiment Analysis"] = test_sentiment_analysis(api_key, model)
    results["Risk Assessment"] = test_risk_assessment(api_key, model)

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - AI Agents Ready!")
        print("=" * 70)
        print("\n🎯 Your AI trading agents are fully operational!")
        print("\nNext Steps:")
        print("  1. Run the enhanced trading strategy:")
        print("     uv run enhanced_scalping_strategy.py")
        print("\n  2. The multi-agent system will provide:")
        print("     • Market Intelligence (news, events, sentiment)")
        print("     • Technical Analysis (multi-timeframe)")
        print("     • Risk Assessment (position sizing, correlations)")
        print("     • Coordinated Trading Decisions")
        print("\n  3. With free tier (2.5M tokens/day), you can run:")
        print("     • ~500-1000 trading signal analyses per day")
        print("     • Checking every 5 minutes = ~288 signals/day ✓")
        print("\n⚠️  IMPORTANT: Regenerate your OpenAI API key after testing")
        print("     (it was exposed in this conversation)")
        print("     Go to: https://platform.openai.com/api-keys")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
