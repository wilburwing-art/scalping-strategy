"""
AI Cost Tracking and Optimization Module

Tracks token usage, estimates costs, and provides caching for AI agent calls.
"""

import logging
import tiktoken
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("AICostTracker")


@dataclass
class UsageStats:
    """Token usage statistics"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    api_calls: int = 0
    cached_calls: int = 0
    estimated_cost: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)

    def add_usage(self, prompt_tokens: int, completion_tokens: int, cost: float = 0.0):
        """Add usage from an API call"""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.api_calls += 1
        self.estimated_cost += cost

    def add_cached(self):
        """Increment cached call counter"""
        self.cached_calls += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        runtime = (datetime.now() - self.start_time).total_seconds()
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "api_calls": self.api_calls,
            "cached_calls": self.cached_calls,
            "cache_hit_rate": self.cached_calls / max(1, self.api_calls + self.cached_calls),
            "estimated_cost": round(self.estimated_cost, 4),
            "runtime_seconds": round(runtime, 1),
            "tokens_per_hour": round((self.total_tokens / runtime * 3600) if runtime > 0 else 0, 0),
            "cost_per_hour": round((self.estimated_cost / runtime * 3600) if runtime > 0 else 0, 4),
        }


class CostTracker:
    """Track and estimate AI costs"""

    # OpenAI pricing (as of Jan 2025)
    PRICING = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},  # per 1K tokens
        "gpt-4o-mini": {"input": 0.000150, "output": 0.000600},  # per 1K tokens
        "gpt-4o-2024-11-20": {"input": 0.0025, "output": 0.01},
    }

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model.replace("openai:", "").split(":")[0])

        # Per-agent stats
        self.agent_stats: Dict[str, UsageStats] = defaultdict(UsageStats)

        # Overall stats
        self.total_stats = UsageStats()

        logger.info(f"CostTracker initialized for {model}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for token usage"""
        pricing = self.PRICING.get(self.model, self.PRICING["gpt-4o-mini"])

        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def track_call(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        cached: bool = False
    ):
        """Track an API call"""
        if cached:
            self.agent_stats[agent_name].add_cached()
            self.total_stats.add_cached()
            logger.debug(f"{agent_name}: cache hit")
            return

        prompt_tokens = self.count_tokens(prompt)
        completion_tokens = self.count_tokens(response)
        cost = self.estimate_cost(prompt_tokens, completion_tokens)

        self.agent_stats[agent_name].add_usage(prompt_tokens, completion_tokens, cost)
        self.total_stats.add_usage(prompt_tokens, completion_tokens, cost)

        logger.info(
            f"{agent_name}: {prompt_tokens} + {completion_tokens} = {prompt_tokens + completion_tokens} tokens "
            f"(${cost:.4f})"
        )

    def get_stats(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics"""
        if agent_name:
            return self.agent_stats[agent_name].to_dict()

        return {
            "total": self.total_stats.to_dict(),
            "by_agent": {
                name: stats.to_dict()
                for name, stats in self.agent_stats.items()
            },
            "model": self.model,
            "pricing": self.PRICING.get(self.model, self.PRICING["gpt-4o-mini"]),
        }

    def estimate_monthly_cost(self, checks_per_day: int = 288) -> Dict[str, Any]:
        """
        Estimate monthly costs based on current usage.

        Args:
            checks_per_day: Number of market scans per day (default: 288 = every 5 min)
        """
        total = self.total_stats
        runtime_hours = (datetime.now() - total.start_time).total_seconds() / 3600

        if runtime_hours == 0:
            return {
                "error": "No data yet - run some analyses first"
            }

        # Average cost per check
        checks_completed = total.api_calls + total.cached_calls
        cost_per_check = total.estimated_cost / max(1, checks_completed)

        # Daily estimate
        daily_cost = cost_per_check * checks_per_day

        # Monthly estimate (30 days)
        monthly_cost = daily_cost * 30

        # Token usage
        tokens_per_check = total.total_tokens / max(1, checks_completed)
        daily_tokens = tokens_per_check * checks_per_day
        monthly_tokens = daily_tokens * 30

        # Free tier limit (gpt-4o-mini: 2.5M tokens/day)
        free_tier_limit = 2_500_000
        within_free_tier = daily_tokens < free_tier_limit

        return {
            "cost_per_check": round(cost_per_check, 6),
            "checks_per_day": checks_per_day,
            "daily_cost": round(daily_cost, 4),
            "monthly_cost": round(monthly_cost, 2),
            "tokens_per_check": round(tokens_per_check, 0),
            "daily_tokens": round(daily_tokens, 0),
            "monthly_tokens": round(monthly_tokens, 0),
            "within_free_tier": within_free_tier,
            "free_tier_limit": free_tier_limit,
            "free_tier_usage_pct": round((daily_tokens / free_tier_limit) * 100, 1) if within_free_tier else 100,
        }

    def reset(self):
        """Reset all statistics"""
        self.agent_stats.clear()
        self.total_stats = UsageStats()
        logger.info("Cost tracker reset")


class ResponseCache:
    """Simple time-based cache for AI responses"""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time to live for cached responses (default: 5 minutes)
        """
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        logger.info(f"ResponseCache initialized with {ttl_seconds}s TTL")

    def get(self, key: str) -> Optional[Any]:
        """Get cached response if valid"""
        if key in self.cache:
            response, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return response
            else:
                # Expired
                del self.cache[key]
        return None

    def set(self, key: str, response: Any):
        """Cache a response"""
        self.cache[key] = (response, datetime.now())

    def clear(self):
        """Clear all cached responses"""
        self.cache.clear()
        logger.info("Cache cleared")

    def clean_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        expired = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp >= self.ttl
        ]
        for key in expired:
            del self.cache[key]
        if expired:
            logger.debug(f"Cleaned {len(expired)} expired cache entries")

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "ttl_seconds": self.ttl.total_seconds(),
        }
