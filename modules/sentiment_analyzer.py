"""
Social Sentiment Analysis for Forex Trading

Aggregates sentiment from Twitter, Reddit, and StockTwits to gauge
market sentiment for currency pairs.

Usage:
    analyzer = SentimentAnalyzer(
        openai_key="sk-...",
        twitter_bearer="...",
        reddit_client_id="...",
        reddit_client_secret="...",
    )

    sentiment = await analyzer.get_sentiment("EUR_USD")

    if sentiment.is_high_conviction and sentiment.sentiment_score > 0.5:
        print("Strong bullish sentiment!")
"""

import httpx
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


class SentimentScore(Enum):
    """Sentiment classification"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


@dataclass
class SentimentData:
    """Aggregated sentiment for an instrument"""
    instrument: str
    timestamp: datetime

    # Raw metrics
    total_mentions: int
    positive_count: int
    negative_count: int
    neutral_count: int

    # Derived metrics
    sentiment_score: float  # -1.0 to +1.0
    sentiment_strength: float  # 0.0 to 1.0 (confidence)
    mention_volume_percentile: float  # vs 30-day average

    # Source breakdown
    twitter_sentiment: Optional[float] = None
    reddit_sentiment: Optional[float] = None
    stocktwits_sentiment: Optional[float] = None

    # Additional metrics
    twitter_mentions: int = 0
    reddit_mentions: int = 0
    stocktwits_mentions: int = 0

    @property
    def net_sentiment(self) -> SentimentScore:
        """Classify overall sentiment"""
        if self.sentiment_score >= 0.3:
            return SentimentScore.VERY_POSITIVE if self.sentiment_score >= 0.6 else SentimentScore.POSITIVE
        elif self.sentiment_score <= -0.3:
            return SentimentScore.VERY_NEGATIVE if self.sentiment_score <= -0.6 else SentimentScore.NEGATIVE
        else:
            return SentimentScore.NEUTRAL

    @property
    def is_high_conviction(self) -> bool:
        """Strong sentiment with high volume"""
        return (
            abs(self.sentiment_score) > 0.4 and
            self.sentiment_strength > 0.6 and
            self.mention_volume_percentile > 70
        )

    @property
    def is_contrarian_signal(self) -> bool:
        """Retail heavily one-sided (fade opportunity)"""
        return (
            abs(self.sentiment_score) > 0.7 and  # Very one-sided
            self.total_mentions > 20 and  # Significant volume
            self.mention_volume_percentile > 80  # Unusually high volume
        )

    def __str__(self) -> str:
        direction = "BULLISH" if self.sentiment_score > 0 else "BEARISH" if self.sentiment_score < 0 else "NEUTRAL"
        return (
            f"{self.instrument} Sentiment: {direction} ({self.sentiment_score:+.2f}) - "
            f"{self.total_mentions} mentions ({self.mention_volume_percentile:.0f}th percentile)"
        )


class SentimentAnalyzer:
    """
    Aggregate social sentiment from multiple sources.

    Features:
    - Twitter/X API v2 integration
    - Reddit API integration
    - StockTwits API integration
    - OpenAI GPT-4o-mini sentiment classification
    - Volume percentile tracking
    - Contrarian signal detection

    Usage:
        analyzer = SentimentAnalyzer(
            openai_key="sk-...",
            twitter_bearer_token="...",
        )

        sentiment = await analyzer.get_sentiment("EUR_USD")

        if sentiment.is_high_conviction and sentiment.sentiment_score > 0.5:
            print("Strong bullish sentiment detected!")
    """

    # Instrument search terms mapping
    INSTRUMENT_SEARCH_TERMS = {
        "EUR_USD": ["$EURUSD", "EUR/USD", "EURUSD", "#EURUSD", "euro dollar", "eur usd"],
        "GBP_USD": ["$GBPUSD", "GBP/USD", "GBPUSD", "#GBPUSD", "cable", "pound dollar", "gbp usd"],
        "USD_JPY": ["$USDJPY", "USD/JPY", "USDJPY", "#USDJPY", "dollar yen", "usd jpy"],
        "GBP_JPY": ["$GBPJPY", "GBP/JPY", "GBPJPY", "#GBPJPY", "pound yen", "gbp jpy"],
        "AUD_USD": ["$AUDUSD", "AUD/USD", "AUDUSD", "#AUDUSD", "aussie dollar", "aud usd"],
        "USD_CAD": ["$USDCAD", "USD/CAD", "USDCAD", "#USDCAD", "dollar loonie", "usd cad"],
        "EUR_GBP": ["$EURGBP", "EUR/GBP", "EURGBP", "#EURGBP", "euro pound", "eur gbp"],
        "USD_CHF": ["$USDCHF", "USD/CHF", "USDCHF", "#USDCHF", "dollar franc", "usd chf"],
    }

    def __init__(
        self,
        openai_key: str,
        twitter_bearer_token: Optional[str] = None,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None,
        stocktwits_token: Optional[str] = None,
        cache_duration_minutes: int = 15,
    ):
        """
        Args:
            openai_key: OpenAI API key for sentiment classification
            twitter_bearer_token: Twitter API v2 bearer token
            reddit_client_id: Reddit API client ID
            reddit_client_secret: Reddit API client secret
            stocktwits_token: StockTwits API token (optional, has public endpoint)
            cache_duration_minutes: How long to cache sentiment data
        """
        self.openai_key = openai_key
        self.twitter_bearer = twitter_bearer_token
        self.reddit_id = reddit_client_id
        self.reddit_secret = reddit_client_secret
        self.stocktwits_token = stocktwits_token

        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.cache_duration = timedelta(minutes=cache_duration_minutes)

        # Caching
        self._sentiment_cache: Dict[str, SentimentData] = {}
        self._cache_timestamp: Dict[str, datetime] = {}

        # Historical volume tracking (for percentile calc)
        self._mention_history: Dict[str, List[Tuple[datetime, int]]] = {}

        # Track which sources are available
        self.twitter_enabled = bool(twitter_bearer_token)
        self.reddit_enabled = bool(reddit_client_id and reddit_client_secret)
        self.stocktwits_enabled = True  # Public endpoint available

        logger.info(f"Sentiment analyzer initialized:")
        logger.info(f"  Twitter: {'✓' if self.twitter_enabled else '✗'}")
        logger.info(f"  Reddit: {'✓' if self.reddit_enabled else '✗'}")
        logger.info(f"  StockTwits: {'✓' if self.stocktwits_enabled else '✗'}")

    async def get_sentiment(
        self,
        instrument: str,
        lookback_hours: int = 4,
        use_cache: bool = True,
    ) -> SentimentData:
        """
        Fetch and analyze sentiment for an instrument.

        Args:
            instrument: e.g., "EUR_USD"
            lookback_hours: How far back to search
            use_cache: Use cached data if available

        Returns:
            Aggregated sentiment data
        """
        # Check cache
        if use_cache and self._is_cache_valid(instrument):
            logger.debug(f"Using cached sentiment for {instrument}")
            return self._sentiment_cache[instrument]

        search_terms = self.INSTRUMENT_SEARCH_TERMS.get(instrument, [])
        if not search_terms:
            logger.warning(f"No search terms configured for {instrument}")
            return self._empty_sentiment(instrument)

        # Fetch from all sources in parallel
        tasks = []

        if self.twitter_enabled:
            tasks.append(("twitter", self._fetch_twitter_sentiment(search_terms, lookback_hours)))

        if self.reddit_enabled:
            tasks.append(("reddit", self._fetch_reddit_sentiment(search_terms, lookback_hours)))

        if self.stocktwits_enabled:
            tasks.append(("stocktwits", self._fetch_stocktwits_sentiment(instrument)))

        if not tasks:
            logger.warning("No sentiment sources configured")
            return self._empty_sentiment(instrument)

        # Gather results
        source_names = [name for name, _ in tasks]
        source_tasks = [task for _, task in tasks]
        results = await asyncio.gather(*source_tasks, return_exceptions=True)

        # Aggregate sentiment
        all_mentions = []
        positive = negative = neutral = 0
        source_sentiments = {}
        source_mention_counts = {}

        for i, result in enumerate(results):
            source_name = source_names[i]

            if isinstance(result, Exception):
                logger.error(f"{source_name} sentiment fetch failed: {result}")
                continue

            if result:
                all_mentions.extend(result["mentions"])
                positive += result["positive"]
                negative += result["negative"]
                neutral += result["neutral"]

                # Track source-specific sentiment
                if result["total"] > 0:
                    source_sentiments[f"{source_name}_sentiment"] = (
                        (result["positive"] - result["negative"]) / result["total"]
                    )
                    source_mention_counts[f"{source_name}_mentions"] = result["total"]

        # Calculate aggregate metrics
        total = len(all_mentions)

        if total == 0:
            logger.info(f"No sentiment data found for {instrument}")
            return self._empty_sentiment(instrument)

        sentiment_score = (positive - negative) / total if total > 0 else 0.0
        sentiment_strength = abs(sentiment_score)

        # Calculate mention volume percentile
        mention_percentile = self._calculate_volume_percentile(instrument, total)

        sentiment_data = SentimentData(
            instrument=instrument,
            timestamp=datetime.utcnow(),
            total_mentions=total,
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            sentiment_score=sentiment_score,
            sentiment_strength=sentiment_strength,
            mention_volume_percentile=mention_percentile,
            **source_sentiments,
            **source_mention_counts,
        )

        # Update cache
        self._sentiment_cache[instrument] = sentiment_data
        self._cache_timestamp[instrument] = datetime.utcnow()

        logger.info(f"Sentiment fetched: {sentiment_data}")

        return sentiment_data

    async def _fetch_twitter_sentiment(
        self,
        search_terms: List[str],
        lookback_hours: int,
    ) -> Dict:
        """Fetch tweets and classify sentiment"""
        try:
            # Build search query
            query = " OR ".join([f'"{term}"' for term in search_terms])
            query += " -is:retweet lang:en"  # Exclude RTs, English only

            # Calculate time range
            start_time = (datetime.utcnow() - timedelta(hours=lookback_hours)).isoformat() + "Z"

            # Call Twitter API v2
            url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {"Authorization": f"Bearer {self.twitter_bearer}"}
            params = {
                "query": query,
                "start_time": start_time,
                "max_results": 100,  # Max per request
                "tweet.fields": "created_at,public_metrics",
            }

            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            tweets = data.get("data", [])

            if not tweets:
                logger.debug("No tweets found")
                return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

            logger.debug(f"Found {len(tweets)} tweets")

            # Classify sentiment using OpenAI
            texts = [t["text"] for t in tweets]
            sentiments = await self._classify_sentiment_batch(texts)

            positive = sum(1 for s in sentiments if s > 0.2)
            negative = sum(1 for s in sentiments if s < -0.2)
            neutral = len(sentiments) - positive - negative

            return {
                "mentions": tweets,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "total": len(tweets),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Twitter API error: {e.response.status_code} - {e.response.text[:200]}")
            return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}
        except Exception as e:
            logger.error(f"Twitter sentiment fetch failed: {e}")
            return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

    async def _fetch_reddit_sentiment(
        self,
        search_terms: List[str],
        lookback_hours: int,
    ) -> Dict:
        """Fetch Reddit posts/comments and classify sentiment"""
        try:
            # Get OAuth token
            auth_response = await self.http_client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(self.reddit_id, self.reddit_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": "forex-sentiment-bot/1.0"},
            )
            auth_response.raise_for_status()
            access_token = auth_response.json()["access_token"]

            # Search r/forex for mentions
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "forex-sentiment-bot/1.0",
            }

            # Build query
            query = " OR ".join(search_terms)

            # Search posts
            url = "https://oauth.reddit.com/r/forex/search"
            params = {
                "q": query,
                "sort": "new",
                "limit": 100,
                "t": "day",  # Last 24 hours
                "restrict_sr": "true",
            }

            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            if not posts:
                logger.debug("No Reddit posts found")
                return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

            logger.debug(f"Found {len(posts)} Reddit posts")

            # Extract text (title + selftext)
            texts = [
                f"{p['data']['title']} {p['data'].get('selftext', '')}"
                for p in posts
            ]

            # Classify sentiment
            sentiments = await self._classify_sentiment_batch(texts)

            positive = sum(1 for s in sentiments if s > 0.2)
            negative = sum(1 for s in sentiments if s < -0.2)
            neutral = len(sentiments) - positive - negative

            return {
                "mentions": posts,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "total": len(posts),
            }

        except Exception as e:
            logger.error(f"Reddit sentiment fetch failed: {e}")
            return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

    async def _fetch_stocktwits_sentiment(self, instrument: str) -> Dict:
        """Fetch StockTwits sentiment (they provide pre-calculated sentiment)"""
        try:
            # StockTwits uses different symbols: EUR.USD instead of EUR_USD
            symbol = instrument.replace("_", ".")

            url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
            params = {}

            # Add token if available (increases rate limits)
            if self.stocktwits_token:
                params["access_token"] = self.stocktwits_token

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            messages = data.get("messages", [])

            if not messages:
                logger.debug("No StockTwits messages found")
                return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

            logger.debug(f"Found {len(messages)} StockTwits messages")

            # StockTwits provides sentiment labels
            positive = sum(
                1 for m in messages
                if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish"
            )
            negative = sum(
                1 for m in messages
                if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish"
            )
            neutral = len(messages) - positive - negative

            return {
                "mentions": messages,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "total": len(messages),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"StockTwits: Symbol {instrument} not found")
            else:
                logger.error(f"StockTwits API error: {e.response.status_code}")
            return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}
        except Exception as e:
            logger.error(f"StockTwits sentiment fetch failed: {e}")
            return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

    async def _classify_sentiment_batch(self, texts: List[str]) -> List[float]:
        """
        Classify sentiment using OpenAI GPT-4o-mini.

        Returns:
            List of sentiment scores (-1.0 to +1.0) for each text
        """
        if not texts:
            return []

        try:
            # Batch texts for efficiency (max 20 at a time)
            batch_size = 20
            all_scores = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]

                # Create prompt
                prompt = (
                    "Classify the sentiment of these forex/trading social media posts. "
                    "Return ONLY a JSON array of numbers from -1.0 (very bearish) to +1.0 (very bullish). "
                    "No explanations, just the array.\n\n"
                )
                for j, text in enumerate(batch):
                    # Truncate long texts
                    truncated = text[:300] if len(text) > 300 else text
                    prompt += f"{j+1}. {truncated}\n"

                # Call OpenAI
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a sentiment analysis expert for financial markets. Return only a JSON array of numbers between -1.0 and 1.0."
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200,
                }

                response = await self.http_client.post(url, headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Parse JSON array
                # Clean up content (remove markdown code blocks if present)
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()

                scores = json.loads(content)

                # Validate scores
                validated_scores = []
                for score in scores:
                    if isinstance(score, (int, float)):
                        # Clamp to -1.0 to 1.0
                        validated_scores.append(max(-1.0, min(1.0, float(score))))
                    else:
                        validated_scores.append(0.0)  # Neutral fallback

                all_scores.extend(validated_scores)

                # Rate limiting (be nice to OpenAI API)
                await asyncio.sleep(0.5)

            return all_scores

        except Exception as e:
            logger.error(f"Sentiment classification failed: {e}")
            # Fallback: neutral sentiment
            return [0.0] * len(texts)

    def _calculate_volume_percentile(self, instrument: str, current_volume: int) -> float:
        """Calculate mention volume percentile vs 30-day history"""
        # Get historical volumes
        if instrument not in self._mention_history:
            self._mention_history[instrument] = []

        history = self._mention_history[instrument]

        # Add current volume
        history.append((datetime.utcnow(), current_volume))

        # Keep only last 30 days
        cutoff = datetime.utcnow() - timedelta(days=30)
        history = [(ts, vol) for ts, vol in history if ts > cutoff]
        self._mention_history[instrument] = history

        if len(history) < 10:
            return 50.0  # Not enough data

        # Calculate percentile
        volumes = [vol for _, vol in history]
        volumes.sort()

        percentile = (sum(1 for v in volumes if v <= current_volume) / len(volumes)) * 100

        return percentile

    def _is_cache_valid(self, instrument: str) -> bool:
        """Check if cached sentiment is still fresh"""
        if instrument not in self._cache_timestamp:
            return False

        age = datetime.utcnow() - self._cache_timestamp[instrument]
        return age < self.cache_duration

    def _empty_sentiment(self, instrument: str) -> SentimentData:
        """Return neutral sentiment when no data available"""
        return SentimentData(
            instrument=instrument,
            timestamp=datetime.utcnow(),
            total_mentions=0,
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            sentiment_score=0.0,
            sentiment_strength=0.0,
            mention_volume_percentile=50.0,
        )

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


# Example usage
async def main():
    """Example usage of SentimentAnalyzer"""
    import os

    openai_key = os.getenv("OPENAI_API_KEY")
    twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
    reddit_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not openai_key:
        print("Set OPENAI_API_KEY environment variable")
        return

    analyzer = SentimentAnalyzer(
        openai_key=openai_key,
        twitter_bearer_token=twitter_bearer,
        reddit_client_id=reddit_id,
        reddit_client_secret=reddit_secret,
    )

    # Test sentiment analysis
    instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]

    print("\n" + "="*60)
    print("SOCIAL SENTIMENT ANALYSIS")
    print("="*60 + "\n")

    for instrument in instruments:
        print(f"Analyzing {instrument}...")
        sentiment = await analyzer.get_sentiment(instrument, lookback_hours=6)

        print(f"\n{sentiment}")
        print(f"  Net Sentiment: {sentiment.net_sentiment.name}")
        print(f"  High Conviction: {sentiment.is_high_conviction}")
        print(f"  Contrarian Signal: {sentiment.is_contrarian_signal}")

        if sentiment.twitter_sentiment is not None:
            print(f"  Twitter: {sentiment.twitter_sentiment:+.2f} ({sentiment.twitter_mentions} mentions)")
        if sentiment.reddit_sentiment is not None:
            print(f"  Reddit: {sentiment.reddit_sentiment:+.2f} ({sentiment.reddit_mentions} mentions)")
        if sentiment.stocktwits_sentiment is not None:
            print(f"  StockTwits: {sentiment.stocktwits_sentiment:+.2f} ({sentiment.stocktwits_mentions} mentions)")

        print()

    await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())
