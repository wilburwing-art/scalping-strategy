"""
Economic Calendar Integration for Forex Trading Strategy

Integrates with Trading Economics API to fetch economic events and
prevent trading during high-impact news periods.

Usage:
    calendar = EconomicCalendar(api_key="your_key")
    await calendar.fetch_upcoming_events(hours_ahead=24)
    is_safe, event = calendar.is_safe_to_trade("EUR_USD", datetime.now())
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class NewsImpact(Enum):
    """Economic event impact level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # NFP, FOMC, GDP, CPI


@dataclass
class EconomicEvent:
    """Single economic calendar event"""
    event_id: str
    country: str
    event_name: str
    timestamp: datetime
    impact: NewsImpact
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    currency: str = "USD"

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

    def __str__(self) -> str:
        time_str = self.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        return f"{self.event_name} ({self.country}) - {self.impact.value.upper()} @ {time_str}"


class EconomicCalendar:
    """
    Integration with Trading Economics API for economic events.

    Features:
    - Fetch upcoming economic events
    - Classify event impact (low/medium/high/critical)
    - Determine if safe to trade based on upcoming news
    - Cache results to reduce API calls

    Usage:
        calendar = EconomicCalendar(api_key="your_key")
        events = await calendar.fetch_upcoming_events(hours_ahead=24)
        is_safe = calendar.is_safe_to_trade("EUR_USD", datetime.now())
    """

    BASE_URL = "https://api.tradingeconomics.com"

    # Critical events that always cause volatility
    CRITICAL_EVENTS = {
        "Non-Farm Payrolls",
        "Nonfarm Payrolls",
        "NFP",
        "FOMC Statement",
        "Federal Funds Rate",
        "Interest Rate Decision",
        "ECB Interest Rate",
        "GDP Growth Rate",
        "GDP",
        "CPI",
        "Consumer Price Index",
        "Retail Sales",
        "Unemployment Rate",
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

    async def fetch_upcoming_events(
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
            logger.info("Using cached economic events")
            return self._filter_events(
                self._cache.get("events", []),
                hours_ahead,
                min_impact,
                countries
            )

        # Fetch from API
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours_ahead)

        try:
            url = f"{self.BASE_URL}/calendar"
            params = {
                "c": self.api_key,
                "d1": now.strftime("%Y-%m-%d"),
                "d2": end_time.strftime("%Y-%m-%d"),
                "f": "json",
            }

            logger.info(f"Fetching economic calendar from {params['d1']} to {params['d2']}")
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

            logger.info(f"Fetched {len(events)} economic events")

            return self._filter_events(events, hours_ahead, min_impact, countries)

        except httpx.HTTPStatusError as e:
            logger.error(f"API error fetching economic calendar: {e.response.status_code} - {e.response.text}")
            # Return cached data if available
            return self._cache.get("events", [])
        except Exception as e:
            logger.error(f"Failed to fetch economic calendar: {e}")
            # Return cached data if available
            return self._cache.get("events", [])

    def _parse_event(self, data: Dict) -> Optional[EconomicEvent]:
        """Parse API response into EconomicEvent"""
        try:
            event_name = data.get("Event", "Unknown Event")

            # Determine impact level
            impact_str = data.get("Importance", "").lower()

            # Check if critical event
            if any(critical.lower() in event_name.lower() for critical in self.CRITICAL_EVENTS):
                impact = NewsImpact.CRITICAL
            elif impact_str == "3" or impact_str == "high":
                impact = NewsImpact.HIGH
            elif impact_str == "2" or impact_str == "medium":
                impact = NewsImpact.MEDIUM
            else:
                impact = NewsImpact.LOW

            # Parse timestamp
            date_str = data.get("Date", "")
            if not date_str:
                return None

            # Handle various date formats
            try:
                timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                # Try alternate format
                timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

            event = EconomicEvent(
                event_id=data.get("CalendarId", str(hash(event_name + date_str))),
                country=data.get("Country", "Unknown"),
                event_name=event_name,
                timestamp=timestamp,
                impact=impact,
                actual=self._parse_float(data.get("Actual")),
                forecast=self._parse_float(data.get("Forecast")),
                previous=self._parse_float(data.get("Previous")),
                currency=data.get("Currency", "USD"),
            )

            return event

        except Exception as e:
            logger.warning(f"Failed to parse event data: {e}")
            return None

    def _parse_float(self, value) -> Optional[float]:
        """Safely parse float value"""
        if value is None or value == "":
            return None
        try:
            # Remove % signs and other characters
            if isinstance(value, str):
                value = value.replace("%", "").replace(",", "").strip()
            return float(value)
        except (ValueError, TypeError):
            return None

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still fresh"""
        if not self._cache_timestamp:
            return False
        return datetime.utcnow() - self._cache_timestamp < self.cache_duration

    def _filter_events(
        self,
        events: List[EconomicEvent],
        hours_ahead: int,
        min_impact: NewsImpact,
        countries: Optional[List[str]],
    ) -> List[EconomicEvent]:
        """Filter events by criteria"""
        now = datetime.utcnow()
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
        current_time: Optional[datetime] = None,
        buffer_minutes_before: int = 30,
        buffer_minutes_after: int = 60,
    ) -> Tuple[bool, Optional[EconomicEvent]]:
        """
        Check if it's safe to trade given upcoming news.

        Args:
            instrument: e.g., "EUR_USD"
            current_time: Current time (UTC), defaults to now
            buffer_minutes_before: Don't trade X minutes before event
            buffer_minutes_after: Don't trade X minutes after event

        Returns:
            (is_safe, blocking_event)
                is_safe: True if safe to trade, False if news event nearby
                blocking_event: The event causing the block, or None if safe
        """
        if current_time is None:
            current_time = datetime.utcnow()

        # Extract currencies from instrument
        try:
            base_currency, quote_currency = instrument.split("_")
        except ValueError:
            logger.error(f"Invalid instrument format: {instrument}")
            return True, None  # Allow trading if can't parse

        # Get relevant countries
        countries = set()
        countries.update(self.CURRENCY_COUNTRIES.get(base_currency, []))
        countries.update(self.CURRENCY_COUNTRIES.get(quote_currency, []))

        # Get cached events (should be pre-fetched)
        all_events = self._cache.get("events", [])

        if not all_events:
            logger.warning("No events in cache - calendar may not have been fetched yet")
            # Conservative: allow trading but warn
            return True, None

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
                minutes_until = (event.timestamp - current_time).total_seconds() / 60
                logger.warning(
                    f"News event detected: {event.event_name} ({event.country}) "
                    f"at {event.timestamp.strftime('%H:%M UTC')} - Impact: {event.impact.value} "
                    f"({minutes_until:.0f} minutes away)"
                )
                return False, event

        return True, None

    def get_upcoming_critical_events(self, hours_ahead: int = 24) -> List[EconomicEvent]:
        """
        Get list of upcoming critical events for logging/monitoring.

        Args:
            hours_ahead: How far ahead to look

        Returns:
            List of critical events
        """
        all_events = self._cache.get("events", [])
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)

        critical = [
            e for e in all_events
            if e.impact == NewsImpact.CRITICAL and now <= e.timestamp <= cutoff
        ]

        return sorted(critical, key=lambda e: e.timestamp)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Example usage
async def main():
    """Example usage of EconomicCalendar"""
    import os

    api_key = os.getenv("TRADING_ECONOMICS_API_KEY")
    if not api_key:
        print("Set TRADING_ECONOMICS_API_KEY environment variable")
        return

    calendar = EconomicCalendar(api_key=api_key)

    # Fetch upcoming events
    events = await calendar.fetch_upcoming_events(
        hours_ahead=24,
        min_impact=NewsImpact.MEDIUM,
    )

    print(f"\nFound {len(events)} upcoming economic events:\n")
    for event in events[:10]:  # Show first 10
        print(f"  {event}")

    # Check if safe to trade
    instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
    print("\n\nTrading Safety Check:")
    for instrument in instruments:
        is_safe, blocking_event = calendar.is_safe_to_trade(instrument)
        if is_safe:
            print(f"  {instrument}: ✓ SAFE TO TRADE")
        else:
            print(f"  {instrument}: ✗ AVOID - {blocking_event.event_name}")

    # Show critical events
    critical = calendar.get_upcoming_critical_events(hours_ahead=48)
    if critical:
        print(f"\n\n⚠️  {len(critical)} CRITICAL events in next 48 hours:")
        for event in critical:
            print(f"  {event}")

    await calendar.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
