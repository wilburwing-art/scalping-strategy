# Phase 3 Implementation Plan: Advanced Intelligence & Optimization
## Enhanced Market Analysis & System Hardening

**Status**: Ready for implementation
**Estimated Effort**: 30-40 hours
**Priority**: HIGH - Production readiness and competitive edge
**Dependencies**: Phase 1 (Agents) ✅ COMPLETE, Phase 2 (Base fixes) ⚠️ IN PROGRESS

---

## Executive Summary

Phase 1 built the multi-agent AI system. Phase 2 fixed the base strategy fundamentals. Phase 3 adds **advanced intelligence features** that give the system a genuine edge over basic technical strategies:

**Core Goals**:
1. **Economic Calendar Integration** - Avoid high-impact news events that cause unpredictable volatility
2. **Social Sentiment Analysis** - Gauge market sentiment from Twitter, Reddit, StockTwits
3. **Trade Journaling** - Track performance, identify patterns, continuous improvement
4. **Parameter Optimization** - Systematically find optimal strategy parameters
5. **Advanced Risk Features** - Session filtering and correlation analysis (if not in Phase 2)
6. **Production Hardening** - Monitoring, alerts, failsafes

---

## Critical Path Analysis

### Dependency Graph

```
Economic Calendar ──┐
                    ├──> News-Aware Trading ──> Higher Win Rate
Sentiment Analysis ─┘

Trade Journal ──────> Performance Analytics ──> Parameter Insights
                                               │
Parameter Optimizer ───────────────────────────┘

Session Filters ────┐
Correlation Matrix ─┼──> Risk Management ──> Lower Drawdown
Production Alerts ──┘
```

**Critical Path**: Economic Calendar → Sentiment Analysis → Integration (15-18 hours)
**Parallel Track**: Trade Journaling → Parameter Optimization (12-15 hours)
**Quick Wins**: Production monitoring, alerts (4-6 hours)

---

## Component 1: Economic Calendar Integration

### Why This Matters

**Problem**: Trading during high-impact news events leads to:
- Extreme volatility (100+ pip moves in seconds)
- Wide spreads (5-10x normal)
- Slippage (3-10 pips vs normal 0.5-1 pip)
- Stop loss hunting (market makers widen spreads, trigger stops, then reverse)

**Impact**: Avoiding just 2-3 bad news trades per month can improve monthly return by 3-5%

### Solution Architecture

#### Data Source: Trading Economics API

**Why Trading Economics**:
- Comprehensive economic calendar (10,000+ events/year)
- Real-time updates and revisions
- Historical impact ratings (low/medium/high)
- Free tier: 1000 requests/month (sufficient for forex)

**Alternative**: Forex Factory scraping (free but legally gray, unreliable)

#### Implementation

```python
from datetime import datetime, timedelta
import httpx
from typing import List, Dict, Optional
from enum import Enum

class NewsImpact(Enum):
    """Economic event impact level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # NFP, FOMC, etc.

class EconomicEvent:
    """Single economic calendar event"""
    def __init__(
        self,
        event_id: str,
        country: str,
        event_name: str,
        timestamp: datetime,
        impact: NewsImpact,
        actual: Optional[float] = None,
        forecast: Optional[float] = None,
        previous: Optional[float] = None,
        currency: str = "USD",
    ):
        self.event_id = event_id
        self.country = country
        self.event_name = event_name
        self.timestamp = timestamp
        self.impact = impact
        self.actual = actual
        self.forecast = forecast
        self.previous = previous
        self.currency = currency

    @property
    def is_surprise(self) -> bool:
        """Check if actual differs significantly from forecast"""
        if not self.actual or not self.forecast:
            return False

        deviation = abs(self.actual - self.forecast) / abs(self.forecast) if self.forecast != 0 else 0
        return deviation > 0.2  # 20% deviation = surprise

    @property
    def surprise_magnitude(self) -> float:
        """How much did actual deviate from forecast (%)"""
        if not self.actual or not self.forecast or self.forecast == 0:
            return 0.0
        return abs(self.actual - self.forecast) / abs(self.forecast)

class EconomicCalendar:
    """
    Integration with Trading Economics API for economic events.

    Usage:
        calendar = EconomicCalendar(api_key="your_key")
        events = await calendar.get_upcoming_events(hours_ahead=24)
        is_safe = calendar.is_safe_to_trade("EUR_USD", datetime.now())
    """

    BASE_URL = "https://api.tradingeconomics.com"

    # Critical events that always cause volatility
    CRITICAL_EVENTS = {
        "Non-Farm Payrolls",
        "FOMC Statement",
        "Federal Funds Rate",
        "ECB Interest Rate Decision",
        "GDP Growth Rate",
        "CPI",
        "Retail Sales",
    }

    # Currency to country mapping
    CURRENCY_COUNTRIES = {
        "USD": ["United States"],
        "EUR": ["Euro Area", "Germany", "France", "Italy", "Spain"],
        "GBP": ["United Kingdom"],
        "JPY": ["Japan"],
        "CHF": ["Switzerland"],
        "CAD": ["Canada"],
        "AUD": ["Australia"],
        "NZD": ["New Zealand"],
    }

    def __init__(self, api_key: str, cache_duration_minutes: int = 60):
        """
        Args:
            api_key: Trading Economics API key (free at tradingeconomics.com)
            cache_duration_minutes: How long to cache calendar data
        """
        self.api_key = api_key
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self._cache: Dict[str, List[EconomicEvent]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        min_impact: NewsImpact = NewsImpact.MEDIUM,
        countries: Optional[List[str]] = None,
    ) -> List[EconomicEvent]:
        """
        Fetch upcoming economic events.

        Args:
            hours_ahead: How far ahead to look
            min_impact: Minimum impact level to include
            countries: Filter by countries (None = all major economies)

        Returns:
            List of upcoming events sorted by time
        """
        # Check cache
        if self._is_cache_valid():
            return self._filter_events(
                self._cache.get("events", []),
                hours_ahead,
                min_impact,
                countries
            )

        # Fetch from API
        now = datetime.now()
        end_time = now + timedelta(hours=hours_ahead)

        try:
            url = f"{self.BASE_URL}/calendar"
            params = {
                "c": self.api_key,
                "d1": now.strftime("%Y-%m-%d"),
                "d2": end_time.strftime("%Y-%m-%d"),
                "f": "json",
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse events
            events = []
            for item in data:
                try:
                    event = self._parse_event(item)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse event: {e}")
                    continue

            # Update cache
            self._cache["events"] = events
            self._cache_timestamp = now

            return self._filter_events(events, hours_ahead, min_impact, countries)

        except Exception as e:
            logger.error(f"Failed to fetch economic calendar: {e}")
            # Return cached data if available
            return self._cache.get("events", [])

    def _parse_event(self, data: Dict) -> Optional[EconomicEvent]:
        """Parse API response into EconomicEvent"""
        try:
            # Determine impact level
            impact_str = data.get("Importance", "").lower()
            if any(critical in data.get("Event", "") for critical in self.CRITICAL_EVENTS):
                impact = NewsImpact.CRITICAL
            elif impact_str == "high" or data.get("Importance") == "3":
                impact = NewsImpact.HIGH
            elif impact_str == "medium" or data.get("Importance") == "2":
                impact = NewsImpact.MEDIUM
            else:
                impact = NewsImpact.LOW

            # Parse timestamp
            timestamp = datetime.fromisoformat(data["Date"].replace("Z", "+00:00"))

            event = EconomicEvent(
                event_id=data.get("CalendarId", str(hash(data["Event"] + data["Date"]))),
                country=data.get("Country", "Unknown"),
                event_name=data.get("Event", "Unknown Event"),
                timestamp=timestamp,
                impact=impact,
                actual=self._parse_float(data.get("Actual")),
                forecast=self._parse_float(data.get("Forecast")),
                previous=self._parse_float(data.get("Previous")),
                currency=data.get("Currency", "USD"),
            )

            return event

        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            return None

    def _parse_float(self, value) -> Optional[float]:
        """Safely parse float value"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still fresh"""
        if not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < self.cache_duration

    def _filter_events(
        self,
        events: List[EconomicEvent],
        hours_ahead: int,
        min_impact: NewsImpact,
        countries: Optional[List[str]],
    ) -> List[EconomicEvent]:
        """Filter events by criteria"""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours_ahead)

        # Impact level ordering
        impact_order = {
            NewsImpact.LOW: 0,
            NewsImpact.MEDIUM: 1,
            NewsImpact.HIGH: 2,
            NewsImpact.CRITICAL: 3,
        }
        min_impact_value = impact_order[min_impact]

        filtered = [
            e for e in events
            if (now <= e.timestamp <= cutoff and
                impact_order[e.impact] >= min_impact_value and
                (countries is None or e.country in countries))
        ]

        return sorted(filtered, key=lambda e: e.timestamp)

    def is_safe_to_trade(
        self,
        instrument: str,
        current_time: datetime,
        buffer_minutes_before: int = 30,
        buffer_minutes_after: int = 60,
    ) -> tuple[bool, Optional[EconomicEvent]]:
        """
        Check if it's safe to trade given upcoming news.

        Args:
            instrument: e.g., "EUR_USD"
            current_time: Current time
            buffer_minutes_before: Don't trade X minutes before event
            buffer_minutes_after: Don't trade X minutes after event

        Returns:
            (is_safe, blocking_event)
        """
        # Extract currencies from instrument
        base_currency, quote_currency = instrument.split("_")

        # Get relevant countries
        countries = set()
        countries.update(self.CURRENCY_COUNTRIES.get(base_currency, []))
        countries.update(self.CURRENCY_COUNTRIES.get(quote_currency, []))

        # Get cached events (should be pre-fetched)
        all_events = self._cache.get("events", [])

        # Check for events in danger window
        danger_start = current_time - timedelta(minutes=buffer_minutes_after)
        danger_end = current_time + timedelta(minutes=buffer_minutes_before)

        for event in all_events:
            # Only check high/critical impact events
            if event.impact not in [NewsImpact.HIGH, NewsImpact.CRITICAL]:
                continue

            # Check if event affects this instrument
            if event.country not in countries:
                continue

            # Check if event is in danger window
            if danger_start <= event.timestamp <= danger_end:
                logger.warning(
                    f"News event detected: {event.event_name} ({event.country}) "
                    f"at {event.timestamp} - Impact: {event.impact.value}"
                )
                return False, event

        return True, None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

#### Integration with Trading Strategy

```python
class NewsAwareStrategy(EnhancedScalpingStrategy):
    """Trading strategy with economic calendar integration"""

    def __init__(self, config_file, environment="practice"):
        super().__init__(config_file, environment)

        # Initialize economic calendar
        trading_economics_key = os.getenv("TRADING_ECONOMICS_API_KEY")
        if not trading_economics_key:
            logger.warning("TRADING_ECONOMICS_API_KEY not set - news filtering disabled")
            self.economic_calendar = None
        else:
            self.economic_calendar = EconomicCalendar(api_key=trading_economics_key)

    async def pre_fetch_news_calendar(self):
        """
        Pre-fetch upcoming events (call this once at start, then hourly).
        """
        if not self.economic_calendar:
            return

        events = await self.economic_calendar.get_upcoming_events(
            hours_ahead=24,
            min_impact=NewsImpact.MEDIUM,
        )

        logger.info(f"Fetched {len(events)} upcoming economic events")

        # Log critical events
        critical = [e for e in events if e.impact == NewsImpact.CRITICAL]
        for event in critical:
            logger.warning(
                f"CRITICAL EVENT: {event.event_name} ({event.country}) "
                f"at {event.timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
            )

    async def analyze_opportunity(self, instrument: str) -> Optional[TradingRecommendation]:
        """
        Enhanced analysis with news filtering.
        """
        # 1. Check if safe to trade (news filter)
        if self.economic_calendar:
            is_safe, blocking_event = self.economic_calendar.is_safe_to_trade(
                instrument,
                datetime.now(),
                buffer_minutes_before=30,
                buffer_minutes_after=60,
            )

            if not is_safe:
                logger.info(
                    f"Skipping {instrument} - {blocking_event.event_name} "
                    f"({blocking_event.impact.value}) in {(blocking_event.timestamp - datetime.now()).total_seconds() / 60:.0f} minutes"
                )
                return None

        # 2. Continue with normal analysis
        return await super().analyze_opportunity(instrument)

    async def run(self):
        """Main trading loop with news pre-fetching"""
        # Pre-fetch news calendar
        await self.pre_fetch_news_calendar()

        # Set up hourly news refresh
        last_news_refresh = datetime.now()

        while True:
            try:
                # Refresh news calendar every hour
                if (datetime.now() - last_news_refresh).total_seconds() > 3600:
                    await self.pre_fetch_news_calendar()
                    last_news_refresh = datetime.now()

                # Normal trading logic
                await self.scan_and_trade()

                await asyncio.sleep(self.scan_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)

        # Cleanup
        if self.economic_calendar:
            await self.economic_calendar.close()
```

**Implementation Complexity**: ⭐⭐⭐ (Medium-Hard)
**Estimated Time**: 6-8 hours
**Critical**: ✅ YES - Avoid catastrophic losses

### Testing & Validation

- [ ] API integration works with Trading Economics
- [ ] Events fetched and parsed correctly
- [ ] Currency-to-country mapping accurate
- [ ] Safe-to-trade logic blocks trades 30 min before high-impact news
- [ ] Cache reduces API calls (< 100/day)
- [ ] Fallback graceful if API unavailable

### Cost Analysis

**Trading Economics API**:
- Free tier: 1,000 requests/month
- Paid tier: $50/month for 100,000 requests
- Expected usage: ~500 requests/month (fetch once/hour)

**Recommendation**: Start with free tier

---

## Component 2: Social Sentiment Analysis

### Why This Matters

**Research Shows**:
- Twitter sentiment predicts intraday forex moves (30-60 min ahead)
- Reddit r/forex can indicate retail positioning (fade indicator)
- StockTwits sentiment correlates with short-term volatility

**Use Cases**:
1. **Contrarian signal**: If retail heavily long → professional shorts → fade the crowd
2. **Momentum confirmation**: If sentiment + technicals align → higher confidence
3. **Risk-off detection**: Sudden fear spike → tighten stops

### Solution Architecture

#### Data Sources

**1. Twitter/X API v2** (Most Important)
- Search for currency mentions: "$EURUSD", "EUR/USD", etc.
- Analyze sentiment: positive/negative/neutral
- Track volume of mentions (unusual spike = important)
- **Cost**: Free tier (500k tweets/month), $100/month for elevated access

**2. Reddit API** (PRAW)
- Subreddits: r/forex, r/wallstreetbets (for USD), r/economics
- Track post sentiment and upvote counts
- **Cost**: Free

**3. StockTwits API**
- Forex-specific sentiment
- Retail trader positioning
- **Cost**: Free (limited), $50/month for premium

#### Sentiment Analysis Options

**Option 1: OpenAI GPT-4o-mini** (Recommended)
- Accurate sentiment classification
- Understands context (sarcasm, financial jargon)
- Cost: ~$0.15 per 1M tokens (~3,000 tweets)

**Option 2: Local Model (FinBERT)**
- Free after setup
- Finance-tuned sentiment
- Requires local GPU or CPU processing

**Option 3: VADER (Rule-based)**
- Instant, free
- Less accurate for financial text
- Good for high-volume screening

#### Implementation

```python
import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics

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

class SentimentAnalyzer:
    """
    Aggregate social sentiment from multiple sources.

    Usage:
        analyzer = SentimentAnalyzer(
            openai_key="sk-...",
            twitter_bearer_token="...",
        )

        sentiment = await analyzer.get_sentiment("EUR_USD")

        if sentiment.is_high_conviction and sentiment.sentiment_score > 0.5:
            print("Strong bullish sentiment detected!")
    """

    INSTRUMENT_SEARCH_TERMS = {
        "EUR_USD": ["$EURUSD", "EUR/USD", "#EURUSD", "euro dollar"],
        "GBP_USD": ["$GBPUSD", "GBP/USD", "#GBPUSD", "cable", "pound dollar"],
        "USD_JPY": ["$USDJPY", "USD/JPY", "#USDJPY", "dollar yen"],
        "GBP_JPY": ["$GBPJPY", "GBP/JPY", "#GBPJPY", "pound yen"],
        "AUD_USD": ["$AUDUSD", "AUD/USD", "#AUDUSD", "aussie dollar"],
    }

    def __init__(
        self,
        openai_key: str,
        twitter_bearer_token: Optional[str] = None,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None,
        stocktwits_token: Optional[str] = None,
    ):
        """
        Args:
            openai_key: OpenAI API key for sentiment classification
            twitter_bearer_token: Twitter API v2 bearer token
            reddit_client_id: Reddit API client ID
            reddit_client_secret: Reddit API client secret
            stocktwits_token: StockTwits API token
        """
        self.openai_key = openai_key
        self.twitter_bearer = twitter_bearer_token
        self.reddit_id = reddit_client_id
        self.reddit_secret = reddit_client_secret
        self.stocktwits_token = stocktwits_token

        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Historical volume tracking (for percentile calc)
        self._mention_history: Dict[str, List[tuple[datetime, int]]] = {}

    async def get_sentiment(
        self,
        instrument: str,
        lookback_hours: int = 4,
    ) -> SentimentData:
        """
        Fetch and analyze sentiment for an instrument.

        Args:
            instrument: e.g., "EUR_USD"
            lookback_hours: How far back to search

        Returns:
            Aggregated sentiment data
        """
        search_terms = self.INSTRUMENT_SEARCH_TERMS.get(instrument, [])
        if not search_terms:
            logger.warning(f"No search terms configured for {instrument}")
            return self._empty_sentiment(instrument)

        # Fetch from all sources in parallel
        tasks = []

        if self.twitter_bearer:
            tasks.append(self._fetch_twitter_sentiment(search_terms, lookback_hours))

        if self.reddit_id and self.reddit_secret:
            tasks.append(self._fetch_reddit_sentiment(search_terms, lookback_hours))

        if self.stocktwits_token:
            tasks.append(self._fetch_stocktwits_sentiment(instrument))

        if not tasks:
            logger.warning("No sentiment sources configured")
            return self._empty_sentiment(instrument)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate sentiment
        all_mentions = []
        positive = negative = neutral = 0
        source_sentiments = {}

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Sentiment fetch failed: {result}")
                continue

            if result:
                all_mentions.extend(result["mentions"])
                positive += result["positive"]
                negative += result["negative"]
                neutral += result["neutral"]

                # Track source-specific sentiment
                source_name = ["twitter", "reddit", "stocktwits"][i]
                if result["total"] > 0:
                    source_sentiments[f"{source_name}_sentiment"] = (
                        (result["positive"] - result["negative"]) / result["total"]
                    )

        # Calculate aggregate metrics
        total = len(all_mentions)

        if total == 0:
            return self._empty_sentiment(instrument)

        sentiment_score = (positive - negative) / total if total > 0 else 0.0
        sentiment_strength = abs(sentiment_score)

        # Calculate mention volume percentile
        mention_percentile = self._calculate_volume_percentile(instrument, total)

        return SentimentData(
            instrument=instrument,
            timestamp=datetime.now(),
            total_mentions=total,
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            sentiment_score=sentiment_score,
            sentiment_strength=sentiment_strength,
            mention_volume_percentile=mention_percentile,
            **source_sentiments,
        )

    async def _fetch_twitter_sentiment(
        self,
        search_terms: List[str],
        lookback_hours: int,
    ) -> Dict:
        """Fetch tweets and classify sentiment"""
        try:
            # Build search query
            query = " OR ".join(search_terms)
            query += " -is:retweet lang:en"  # Exclude RTs, English only

            # Calculate time range
            start_time = (datetime.now() - timedelta(hours=lookback_hours)).isoformat() + "Z"

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
                return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

            # Classify sentiment using OpenAI
            sentiments = await self._classify_sentiment_batch([t["text"] for t in tweets])

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
            # Use Reddit API (PRAW would be better, but httpx for consistency)
            # Search r/forex for mentions

            url = "https://oauth.reddit.com/r/forex/search"

            # Get OAuth token first
            auth_response = await self.http_client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(self.reddit_id, self.reddit_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": "forex-sentiment-bot/1.0"},
            )
            auth_response.raise_for_status()
            access_token = auth_response.json()["access_token"]

            # Search posts
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "forex-sentiment-bot/1.0",
            }

            query = " OR ".join(search_terms)
            params = {
                "q": query,
                "sort": "new",
                "limit": 100,
                "t": "day",  # Last 24 hours
            }

            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            if not posts:
                return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

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
            params = {"access_token": self.stocktwits_token} if self.stocktwits_token else {}

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            messages = data.get("messages", [])

            if not messages:
                return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

            # StockTwits provides sentiment labels
            positive = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish")
            negative = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish")
            neutral = len(messages) - positive - negative

            return {
                "mentions": messages,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "total": len(messages),
            }

        except Exception as e:
            logger.error(f"StockTwits sentiment fetch failed: {e}")
            return {"mentions": [], "positive": 0, "negative": 0, "neutral": 0, "total": 0}

    async def _classify_sentiment_batch(self, texts: List[str]) -> List[float]:
        """
        Classify sentiment using OpenAI GPT-4o-mini.

        Returns:
            List of sentiment scores (-1.0 to +1.0) for each text
        """
        try:
            # Batch texts for efficiency (max 20 at a time)
            batch_size = 20
            all_scores = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]

                # Create prompt
                prompt = "Classify the sentiment of these forex-related social media posts. Return a JSON array of scores from -1.0 (very bearish) to +1.0 (very bullish):\n\n"
                for j, text in enumerate(batch):
                    prompt += f"{j+1}. {text[:200]}\n"  # Truncate long texts

                # Call OpenAI
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a sentiment analysis expert for financial markets. Output only a JSON array of numbers."},
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
                import json
                scores = json.loads(content)
                all_scores.extend(scores)

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
        history.append((datetime.now(), current_volume))

        # Keep only last 30 days
        cutoff = datetime.now() - timedelta(days=30)
        history = [(ts, vol) for ts, vol in history if ts > cutoff]
        self._mention_history[instrument] = history

        if len(history) < 10:
            return 50.0  # Not enough data

        # Calculate percentile
        volumes = [vol for _, vol in history]
        volumes.sort()

        percentile = (sum(1 for v in volumes if v <= current_volume) / len(volumes)) * 100

        return percentile

    def _empty_sentiment(self, instrument: str) -> SentimentData:
        """Return neutral sentiment when no data available"""
        return SentimentData(
            instrument=instrument,
            timestamp=datetime.now(),
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
```

#### Integration with Agents

```python
# Modify MarketIntelligenceAgent to include sentiment data
async def run_market_intelligence(
    instrument: str,
    sentiment_data: Optional[SentimentData] = None,
    ...
) -> MarketIntelligence:
    """
    Enhanced with social sentiment.
    """
    deps = {
        "instrument": instrument,
        "sentiment_data": sentiment_data,
        ...
    }

    result = await market_intel_agent.run(
        f"""Analyze market sentiment and news for {instrument}.

        Social Sentiment Data:
        - Total Mentions: {sentiment_data.total_mentions if sentiment_data else 'N/A'}
        - Sentiment Score: {sentiment_data.sentiment_score if sentiment_data else 'N/A'} (-1 bearish, +1 bullish)
        - Mention Volume: {sentiment_data.mention_volume_percentile if sentiment_data else 'N/A'}th percentile
        - High Conviction: {sentiment_data.is_high_conviction if sentiment_data else False}

        Consider:
        1. Does social sentiment align with news/fundamentals?
        2. Is this a contrarian indicator (retail wrong)?
        3. Volume spike = breaking news or just noise?

        Provide sentiment score 0-100 and reasoning.
        """,
        deps=deps,
    )

    return result.data
```

**Implementation Complexity**: ⭐⭐⭐⭐ (Hard)
**Estimated Time**: 8-10 hours
**Critical**: ⚠️ MEDIUM - Edge, not essential

### Testing & Validation

- [ ] Twitter API integration working
- [ ] Reddit API fetching posts correctly
- [ ] StockTwits data parsed correctly
- [ ] OpenAI sentiment classification accurate (spot check 50 examples)
- [ ] Volume percentile calculation correct
- [ ] Sentiment improves agent confidence by 5-10%

### Cost Analysis

**Monthly Costs**:
- Twitter API: Free tier ($0) or Elevated ($100)
- Reddit API: Free ($0)
- StockTwits API: Free tier ($0) or Premium ($50)
- OpenAI sentiment classification: ~$5-10/month (100 classifications/day)

**Total**: $5-160/month depending on tier

**Recommendation**: Start with free tiers, upgrade if proves valuable

---

## Component 3: Trade Journaling & Performance Tracking

### Why This Matters

**Problem**: Without tracking, you can't:
- Identify which setups work vs don't work
- Spot patterns in losses (e.g., "I always lose on Fridays")
- Improve systematically

**Solution**: Comprehensive trade journal with analytics

### Implementation

```python
import sqlite3
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import json

@dataclass
class TradeJournalEntry:
    """Complete record of a trade"""

    # Identifiers
    trade_id: str
    timestamp: datetime

    # Instrument details
    instrument: str
    direction: str  # "BUY" or "SELL"
    units: int

    # Entry
    entry_price: float
    entry_time: datetime

    # Exit
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None  # "STOP_LOSS", "TAKE_PROFIT", "MANUAL", "TIME"

    # P/L
    gross_pips: Optional[float] = None
    costs_pips: float = 0.0
    net_pips: Optional[float] = None
    profit_usd: Optional[float] = None

    # Market context
    session: Optional[str] = None  # "asian", "london", "ny", "overlap"
    rsi: Optional[float] = None
    atr: Optional[float] = None
    ma_short: Optional[float] = None
    ma_long: Optional[float] = None

    # Agent analysis
    market_intel_score: Optional[float] = None
    technical_score: Optional[float] = None
    risk_score: Optional[float] = None
    overall_confidence: Optional[float] = None
    agent_reasoning: Optional[str] = None

    # News/sentiment context
    news_events_nearby: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_volume: Optional[int] = None

    # Risk management
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward_ratio: Optional[float] = None
    position_size_pct: Optional[float] = None  # % of account

    # Performance
    hold_time_minutes: Optional[int] = None
    max_adverse_excursion_pips: Optional[float] = None
    max_favorable_excursion_pips: Optional[float] = None

    # Metadata
    strategy_version: str = "3.0"
    environment: str = "practice"  # "practice" or "live"
    notes: Optional[str] = None

class TradeJournal:
    """
    SQLite-based trade journal with analytics.

    Usage:
        journal = TradeJournal("trades.db")

        # Log entry
        journal.log_entry(trade_id="123", instrument="EUR_USD", ...)

        # Log exit
        journal.log_exit(trade_id="123", exit_price=1.0850, ...)

        # Analytics
        stats = journal.get_statistics(days=30)
        print(f"Win rate: {stats['win_rate']:.1%}")
    """

    def __init__(self, db_path: str = "trade_journal.db"):
        """
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            instrument TEXT NOT NULL,
            direction TEXT NOT NULL,
            units INTEGER NOT NULL,

            entry_price REAL NOT NULL,
            entry_time TEXT NOT NULL,

            exit_price REAL,
            exit_time TEXT,
            exit_reason TEXT,

            gross_pips REAL,
            costs_pips REAL DEFAULT 0,
            net_pips REAL,
            profit_usd REAL,

            session TEXT,
            rsi REAL,
            atr REAL,
            ma_short REAL,
            ma_long REAL,

            market_intel_score REAL,
            technical_score REAL,
            risk_score REAL,
            overall_confidence REAL,
            agent_reasoning TEXT,

            news_events_nearby TEXT,
            sentiment_score REAL,
            sentiment_volume INTEGER,

            stop_loss REAL DEFAULT 0,
            take_profit REAL DEFAULT 0,
            risk_reward_ratio REAL,
            position_size_pct REAL,

            hold_time_minutes INTEGER,
            max_adverse_excursion_pips REAL,
            max_favorable_excursion_pips REAL,

            strategy_version TEXT DEFAULT '3.0',
            environment TEXT DEFAULT 'practice',
            notes TEXT
        )
        """)

        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_instrument ON trades(instrument)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exit_time ON trades(exit_time)")

        self.conn.commit()

    def log_entry(self, entry: TradeJournalEntry):
        """Log trade entry"""
        cursor = self.conn.cursor()

        # Convert dataclass to dict
        data = asdict(entry)

        # Convert datetime to ISO string
        data["timestamp"] = data["timestamp"].isoformat()
        data["entry_time"] = data["entry_time"].isoformat()
        if data["exit_time"]:
            data["exit_time"] = data["exit_time"].isoformat()

        # Insert
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])

        cursor.execute(
            f"INSERT OR REPLACE INTO trades ({columns}) VALUES ({placeholders})",
            list(data.values())
        )

        self.conn.commit()
        logger.info(f"Trade {entry.trade_id} logged to journal")

    def log_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
        gross_pips: float,
        net_pips: float,
        profit_usd: float,
        hold_time_minutes: int,
        max_adverse_pips: float,
        max_favorable_pips: float,
    ):
        """Update trade with exit information"""
        cursor = self.conn.cursor()

        cursor.execute("""
        UPDATE trades SET
            exit_price = ?,
            exit_time = ?,
            exit_reason = ?,
            gross_pips = ?,
            net_pips = ?,
            profit_usd = ?,
            hold_time_minutes = ?,
            max_adverse_excursion_pips = ?,
            max_favorable_excursion_pips = ?
        WHERE trade_id = ?
        """, (
            exit_price,
            exit_time.isoformat(),
            exit_reason,
            gross_pips,
            net_pips,
            profit_usd,
            hold_time_minutes,
            max_adverse_pips,
            max_favorable_pips,
            trade_id,
        ))

        self.conn.commit()
        logger.info(f"Trade {trade_id} exit logged: {net_pips:+.1f} pips, ${profit_usd:+.2f}")

    def get_statistics(
        self,
        days: Optional[int] = None,
        instrument: Optional[str] = None,
        environment: str = "practice",
    ) -> Dict:
        """
        Calculate comprehensive performance statistics.

        Args:
            days: Last N days (None = all time)
            instrument: Filter by instrument (None = all)
            environment: "practice" or "live"

        Returns:
            Dictionary of statistics
        """
        # Build query
        query = "SELECT * FROM trades WHERE environment = ? AND exit_time IS NOT NULL"
        params = [environment]

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND exit_time >= ?"
            params.append(cutoff)

        if instrument:
            query += " AND instrument = ?"
            params.append(instrument)

        # Fetch data
        df = pd.read_sql_query(query, self.conn, params=params)

        if len(df) == 0:
            return {"total_trades": 0, "message": "No trades found"}

        # Basic stats
        total_trades = len(df)
        winners = df[df["net_pips"] > 0]
        losers = df[df["net_pips"] < 0]

        win_rate = len(winners) / total_trades if total_trades > 0 else 0

        # P/L stats
        total_profit_usd = df["profit_usd"].sum()
        avg_win_pips = winners["net_pips"].mean() if len(winners) > 0 else 0
        avg_loss_pips = losers["net_pips"].mean() if len(losers) > 0 else 0

        # Profit factor
        gross_profit = winners["profit_usd"].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers["profit_usd"].sum()) if len(losers) > 0 else 0.01
        profit_factor = gross_profit / gross_loss

        # Sharpe ratio (simplified)
        returns = df["profit_usd"]
        sharpe = (returns.mean() / returns.std()) if returns.std() > 0 else 0

        # Drawdown
        cumulative_pl = df["profit_usd"].cumsum()
        running_max = cumulative_pl.cummax()
        drawdown = cumulative_pl - running_max
        max_drawdown = drawdown.min()

        # By exit reason
        exit_reasons = df["exit_reason"].value_counts().to_dict()

        # By session
        session_stats = df.groupby("session")["net_pips"].agg(["count", "mean", "sum"]).to_dict()

        # By instrument
        instrument_stats = df.groupby("instrument")["net_pips"].agg(["count", "mean", "sum"]).to_dict()

        # Agent confidence correlation
        if "overall_confidence" in df.columns and df["overall_confidence"].notna().any():
            high_confidence = df[df["overall_confidence"] > 0.7]
            low_confidence = df[df["overall_confidence"] < 0.5]

            high_conf_win_rate = (high_confidence["net_pips"] > 0).mean() if len(high_confidence) > 0 else 0
            low_conf_win_rate = (low_confidence["net_pips"] > 0).mean() if len(low_confidence) > 0 else 0
        else:
            high_conf_win_rate = low_conf_win_rate = None

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_profit_usd": total_profit_usd,
            "avg_win_pips": avg_win_pips,
            "avg_loss_pips": avg_loss_pips,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown_usd": max_drawdown,
            "exit_reasons": exit_reasons,
            "session_performance": session_stats,
            "instrument_performance": instrument_stats,
            "high_confidence_win_rate": high_conf_win_rate,
            "low_confidence_win_rate": low_conf_win_rate,
        }

    def export_to_csv(self, filepath: str, days: Optional[int] = None):
        """Export journal to CSV"""
        query = "SELECT * FROM trades WHERE exit_time IS NOT NULL"
        params = []

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND exit_time >= ?"
            params.append(cutoff)

        df = pd.read_sql_query(query, self.conn, params=params)
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df)} trades to {filepath}")

    def close(self):
        """Close database connection"""
        self.conn.close()
```

**Implementation Complexity**: ⭐⭐ (Medium)
**Estimated Time**: 4-5 hours
**Critical**: ✅ YES - Required for optimization

### Testing & Validation

- [ ] Trades logged correctly with all fields
- [ ] Statistics calculated accurately
- [ ] CSV export works
- [ ] Performance analysis useful for identifying patterns

---

## Component 4: Parameter Optimization Framework

### Why This Matters

**Problem**: Default parameters (RSI 30/70, ATR 14, etc.) may not be optimal
**Solution**: Systematic optimization with walk-forward validation

### Implementation

```python
import itertools
from typing import List, Dict, Tuple
import numpy as np
from dataclasses import dataclass

@dataclass
class ParameterSet:
    """Set of strategy parameters"""
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    rsi_period: int = 14
    atr_period: int = 14
    ma_short_period: int = 20
    ma_long_period: int = 50
    risk_percent: float = 1.0
    reward_risk_ratio: float = 1.5
    min_confidence: float = 0.6

class ParameterOptimizer:
    """
    Grid search parameter optimization with walk-forward validation.

    Usage:
        optimizer = ParameterOptimizer(backtest_engine)
        best_params = await optimizer.optimize(
            instrument="EUR_USD",
            start_date="2023-01-01",
            end_date="2024-12-31",
        )
    """

    def __init__(self, backtest_engine):
        self.backtest_engine = backtest_engine

    async def optimize(
        self,
        instrument: str,
        start_date: str,
        end_date: str,
        param_grid: Optional[Dict] = None,
        optimization_metric: str = "sharpe_ratio",
        walk_forward_periods: int = 4,
    ) -> Tuple[ParameterSet, Dict]:
        """
        Find optimal parameters using walk-forward validation.

        Args:
            instrument: Instrument to optimize
            start_date: Start of data range
            end_date: End of data range
            param_grid: Parameter ranges to test
            optimization_metric: "sharpe_ratio", "total_return", "profit_factor"
            walk_forward_periods: Number of walk-forward windows

        Returns:
            (best_parameters, performance_metrics)
        """
        if param_grid is None:
            param_grid = self._default_param_grid()

        # Split data into walk-forward windows
        windows = self._create_walk_forward_windows(
            start_date,
            end_date,
            walk_forward_periods
        )

        # For each window, optimize on in-sample, validate on out-of-sample
        results = []

        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            logger.info(f"\nWalk-forward period {i+1}/{walk_forward_periods}")
            logger.info(f"Train: {train_start} to {train_end}")
            logger.info(f"Test: {test_start} to {test_end}")

            # Grid search on training data
            best_params, best_score = await self._grid_search(
                instrument,
                train_start,
                train_end,
                param_grid,
                optimization_metric,
            )

            # Validate on test data
            test_performance = await self._backtest_with_params(
                instrument,
                test_start,
                test_end,
                best_params,
            )

            results.append({
                "period": i+1,
                "best_params": best_params,
                "train_score": best_score,
                "test_performance": test_performance,
            })

            logger.info(f"Train {optimization_metric}: {best_score:.3f}")
            logger.info(f"Test {optimization_metric}: {test_performance[optimization_metric]:.3f}")

        # Aggregate results
        final_params = self._aggregate_parameters(results)
        final_performance = self._aggregate_performance(results)

        return final_params, final_performance

    def _default_param_grid(self) -> Dict:
        """Default parameter grid for optimization"""
        return {
            "rsi_oversold": [25, 30, 35],
            "rsi_overbought": [65, 70, 75],
            "rsi_period": [10, 14, 20],
            "atr_period": [10, 14, 20],
            "ma_short_period": [10, 20, 30],
            "ma_long_period": [40, 50, 60],
            "reward_risk_ratio": [1.2, 1.5, 2.0],
            "min_confidence": [0.5, 0.6, 0.7],
        }

    async def _grid_search(
        self,
        instrument: str,
        start_date: str,
        end_date: str,
        param_grid: Dict,
        metric: str,
    ) -> Tuple[ParameterSet, float]:
        """Run grid search over parameter space"""

        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        combinations = list(itertools.product(*param_values))

        logger.info(f"Testing {len(combinations)} parameter combinations...")

        best_score = -np.inf
        best_params = None

        for combo in combinations:
            # Create parameter set
            params = ParameterSet()
            for name, value in zip(param_names, combo):
                setattr(params, name, value)

            # Backtest with these parameters
            performance = await self._backtest_with_params(
                instrument,
                start_date,
                end_date,
                params,
            )

            score = performance[metric]

            if score > best_score:
                best_score = score
                best_params = params

        return best_params, best_score

    async def _backtest_with_params(
        self,
        instrument: str,
        start_date: str,
        end_date: str,
        params: ParameterSet,
    ) -> Dict:
        """Run backtest with specific parameters"""

        # Configure backtest engine with parameters
        self.backtest_engine.configure(params)

        # Run backtest
        results = await self.backtest_engine.run(
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
        )

        return results

    def _create_walk_forward_windows(
        self,
        start_date: str,
        end_date: str,
        num_periods: int,
    ) -> List[Tuple[str, str, str, str]]:
        """Create walk-forward train/test windows"""

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        total_days = (end - start).days
        period_days = total_days // num_periods
        train_days = int(period_days * 0.7)  # 70% train, 30% test
        test_days = period_days - train_days

        windows = []

        for i in range(num_periods):
            train_start = start + pd.Timedelta(days=i * period_days)
            train_end = train_start + pd.Timedelta(days=train_days)
            test_start = train_end
            test_end = test_start + pd.Timedelta(days=test_days)

            windows.append((
                train_start.strftime("%Y-%m-%d"),
                train_end.strftime("%Y-%m-%d"),
                test_start.strftime("%Y-%m-%d"),
                test_end.strftime("%Y-%m-%d"),
            ))

        return windows

    def _aggregate_parameters(self, results: List[Dict]) -> ParameterSet:
        """Choose final parameters (use most recent period's best)"""
        return results[-1]["best_params"]

    def _aggregate_performance(self, results: List[Dict]) -> Dict:
        """Aggregate performance across all out-of-sample periods"""

        test_performances = [r["test_performance"] for r in results]

        return {
            "avg_sharpe_ratio": np.mean([p["sharpe_ratio"] for p in test_performances]),
            "avg_total_return": np.mean([p["total_return_pct"] for p in test_performances]),
            "avg_win_rate": np.mean([p["win_rate"] for p in test_performances]),
            "avg_max_drawdown": np.mean([p["max_drawdown_pct"] for p in test_performances]),
            "consistency": np.std([p["total_return_pct"] for p in test_performances]),
        }
```

**Implementation Complexity**: ⭐⭐⭐⭐ (Hard)
**Estimated Time**: 6-8 hours
**Critical**: ⚠️ MEDIUM - Improves performance

---

## Component 5: Production Monitoring & Alerts

### Implementation

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertManager:
    """Send alerts for critical events"""

    def __init__(self, email: str, smtp_config: Dict):
        self.email = email
        self.smtp_config = smtp_config

    async def send_alert(self, subject: str, message: str, priority: str = "MEDIUM"):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["from_email"]
            msg["To"] = self.email
            msg["Subject"] = f"[{priority}] {subject}"

            msg.attach(MIMEText(message, "plain"))

            with smtplib.SMTP(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"]) as server:
                server.starttls()
                server.login(self.smtp_config["username"], self.smtp_config["password"])
                server.send_message(msg)

            logger.info(f"Alert sent: {subject}")

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
```

**Implementation Complexity**: ⭐ (Easy)
**Estimated Time**: 2 hours

---

## Implementation Timeline

### Week 1: Economic Calendar & Sentiment (14-18 hours)
- Day 1-2: Economic calendar integration (6-8h)
- Day 3-4: Social sentiment analysis (8-10h)

### Week 2: Journaling & Optimization (10-13 hours)
- Day 5-6: Trade journaling system (4-5h)
- Day 7-8: Parameter optimization (6-8h)

### Week 3: Integration & Testing (6-9 hours)
- Day 9: Production monitoring (2h)
- Day 10-11: Integration testing (4-6h)
- Day 12: Documentation (2-3h)

**Total Effort**: 30-40 hours

---

## Success Criteria

Phase 3 complete when:
- [ ] Economic calendar blocks trades 30min before high-impact news
- [ ] Sentiment analysis integrated with agents
- [ ] Trade journal tracks all trades with full context
- [ ] Parameter optimizer finds better parameters than defaults
- [ ] Production alerts working
- [ ] System runs 30 days without crashes
- [ ] Performance improves by 5-10% vs Phase 2

---

## Next Steps

1. ✅ Review this plan
2. ⏭️ Implement Component 1 (Economic Calendar)
3. ⏭️ Implement Component 2 (Sentiment Analysis)
4. ⏭️ Continue through remaining components
5. ⏭️ Validation testing
6. ⏭️ Production deployment

**This plan builds a production-grade trading system with genuine competitive advantages.**
