"""
Multi-Agent AI Trading System

This module implements a sophisticated multi-agent system for forex trading decisions
using pydantic-ai and OpenAI GPT models. The system consists of four specialized agents:

1. MarketIntelligenceAgent: Analyzes news, sentiment, economic events
2. TechnicalAnalysisAgent: Multi-timeframe technical analysis
3. RiskAssessmentAgent: Position sizing and risk management
4. CoordinatorAgent: Orchestrates agents and makes final decisions

Optimizations:
- Token usage tracking and cost estimation
- Response caching for market intelligence
- Optimized prompts for reduced token consumption
"""

import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from ai_cost_tracker import CostTracker, ResponseCache

logger = logging.getLogger("TradingAgents")


# Data Models for Agent Communication
class MarketIntelligence(BaseModel):
    """Market intelligence analysis from news and sentiment"""
    sentiment_score: float = Field(ge=-1.0, le=1.0, description="Overall market sentiment (-1 to 1)")
    news_impact: str = Field(description="HIGH, MEDIUM, LOW, or NONE")
    economic_events: list[str] = Field(default_factory=list, description="Upcoming economic events")
    geopolitical_risk: str = Field(description="Assessment of geopolitical risks")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in analysis")
    reasoning: str = Field(description="Explanation of the analysis")


class TechnicalAnalysis(BaseModel):
    """Technical analysis from multiple timeframes"""
    signal: str = Field(description="BUY, SELL, or HOLD")
    entry_price: Optional[float] = Field(None, description="Recommended entry price")
    stop_loss: Optional[float] = Field(None, description="Recommended stop loss")
    take_profit: Optional[float] = Field(None, description="Recommended take profit")
    trend_strength: float = Field(ge=0.0, le=1.0, description="Trend strength (0 to 1)")
    indicator_confluence: int = Field(ge=0, le=5, description="Number of confirming indicators")
    timeframe_alignment: bool = Field(description="Multiple timeframes aligned")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in analysis")
    reasoning: str = Field(description="Explanation of the analysis")


class RiskAssessment(BaseModel):
    """Risk management analysis"""
    position_size: int = Field(description="Recommended position size in units")
    risk_reward_ratio: float = Field(description="Risk to reward ratio")
    risk_level: str = Field(description="LOW, MEDIUM, or HIGH")
    correlation_warning: bool = Field(description="Warning if correlated positions exist")
    max_drawdown_ok: bool = Field(description="Position within max drawdown limits")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in assessment")
    reasoning: str = Field(description="Explanation of the assessment")


class TradingRecommendation(BaseModel):
    """Final coordinated trading recommendation"""
    action: str = Field(description="BUY, SELL, or HOLD")
    instrument: str = Field(description="Trading instrument")
    entry_price: Optional[float] = Field(None, description="Entry price")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    position_size: Optional[int] = Field(None, description="Position size in units")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence score")
    market_intel_weight: float = Field(description="Weight given to market intelligence")
    technical_weight: float = Field(description="Weight given to technical analysis")
    risk_weight: float = Field(description="Weight given to risk assessment")
    reasoning: str = Field(description="Comprehensive reasoning for the decision")


class TradingAgentSystem:
    """
    Multi-agent trading system that coordinates specialized AI agents
    to make informed trading decisions.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        market_intel_weight: float = 0.3,
        technical_weight: float = 0.4,
        risk_weight: float = 0.3,
        min_confidence: float = 0.6
    ):
        """
        Initialize the multi-agent trading system.

        Args:
            api_key: OpenAI API key
            model: OpenAI model to use (gpt-4o, gpt-4o-mini)
            market_intel_weight: Weight for market intelligence (default: 0.3)
            technical_weight: Weight for technical analysis (default: 0.4)
            risk_weight: Weight for risk assessment (default: 0.3)
            min_confidence: Minimum confidence threshold for trades (default: 0.6)
        """
        self.api_key = api_key
        self.model = model
        self.market_intel_weight = market_intel_weight
        self.technical_weight = technical_weight
        self.risk_weight = risk_weight
        self.min_confidence = min_confidence

        # Initialize cost tracking and caching
        self.cost_tracker = CostTracker(model=model)
        self.market_intel_cache = ResponseCache(ttl_seconds=300)  # 5 min TTL

        # Initialize specialized agents
        self.market_intel_agent = self._create_market_intel_agent()
        self.technical_agent = self._create_technical_agent()
        self.risk_agent = self._create_risk_agent()
        self.coordinator_agent = self._create_coordinator_agent()

        logger.info(
            f"TradingAgentSystem initialized with {model} "
            f"(weights: MI={market_intel_weight}, TA={technical_weight}, "
            f"RA={risk_weight}, min_conf={min_confidence})"
        )

    def _create_market_intel_agent(self) -> Agent:
        """Create the Market Intelligence Agent"""
        system_prompt = """Forex market intelligence expert. Analyze sentiment, news, events, geopolitical risks.

Factors: news impact on pairs, economic events (NFP, Fed, GDP), central bank policy, geopolitical tensions.
Output: sentiment (-1 to +1), news impact (HIGH/MEDIUM/LOW/NONE), confidence (0-1).
Be realistic - avoid overconfidence."""

        # Set OpenAI API key as environment variable for pydantic-ai
        import os
        os.environ['OPENAI_API_KEY'] = self.api_key

        return Agent(
            model=f"openai:{self.model}",
            output_type=MarketIntelligence,
            system_prompt=system_prompt
        )

    def _create_technical_agent(self) -> Agent:
        """Create the Technical Analysis Agent"""
        system_prompt = """Forex technical analysis expert. Analyze price action, indicators, patterns across M5/M15/H1/H4 timeframes.

Indicators: RSI, ATR, MAs, MACD, Bollinger Bands, support/resistance, fibonacci, patterns.
Output: BUY/SELL/HOLD, entry/SL/TP levels, trend strength (0-1), indicator confluence (0-5), confidence (0-1).
Conservative - clear setups only."""

        return Agent(
            model=f"openai:{self.model}",
            output_type=TechnicalAnalysis,
            system_prompt=system_prompt
        )

    def _create_risk_agent(self) -> Agent:
        """Create the Risk Assessment Agent"""
        system_prompt = """Forex risk management expert. Ensure strict risk principles to protect capital.

Factors: position sizing (account balance, risk %), R:R ratio (min 1.5:1), correlation, max drawdown, SL placement.
Output: position size, R:R ratio, risk level (LOW/MEDIUM/HIGH), correlation warning, confidence (0-1).
Strict - preserve capital."""

        return Agent(
            model=f"openai:{self.model}",
            output_type=RiskAssessment,
            system_prompt=system_prompt
        )

    def _create_coordinator_agent(self) -> Agent:
        """Create the Coordinator Agent"""
        system_prompt = """Trading coordinator. Synthesize market intel, technical analysis, risk assessment into final decision.

Weight inputs appropriately, resolve conflicts, calculate overall confidence.
Output: BUY/SELL/HOLD, entry/SL/TP, position size, confidence, reasoning.
Recommend trades only when: confidence >= threshold, clear setup, acceptable risk, no conflicts.
When uncertain, HOLD - capital preservation paramount."""

        return Agent(
            model=f"openai:{self.model}",
            output_type=TradingRecommendation,
            system_prompt=system_prompt
        )

    async def analyze_opportunity(
        self,
        instrument: str,
        current_price: float,
        indicators: Dict[str, Any],
        account_balance: float,
        active_trades: int = 0,
        news_context: Optional[str] = None
    ) -> TradingRecommendation:
        """
        Analyze a trading opportunity using all agents.

        Args:
            instrument: Trading instrument (e.g., "EUR_USD")
            current_price: Current market price
            indicators: Dict with technical indicators (rsi, atr, ma_50, ma_200, etc.)
            account_balance: Current account balance
            active_trades: Number of active trades
            news_context: Optional recent news/events context

        Returns:
            TradingRecommendation with action and parameters
        """
        logger.info(f"Analyzing {instrument} at {current_price}")

        try:
            # Run all agents in parallel using asyncio.gather
            import asyncio
            results = await asyncio.gather(
                self._run_market_intel(instrument, current_price, news_context),
                self._run_technical_analysis(instrument, current_price, indicators),
                self._run_risk_assessment(instrument, current_price, indicators, account_balance, active_trades)
            )

            market_intel = results[0]
            technical_analysis = results[1]
            risk_assessment = results[2]

            # Coordinate final decision
            recommendation = await self._coordinate_decision(
                instrument,
                market_intel,
                technical_analysis,
                risk_assessment
            )

            logger.info(
                f"{instrument}: {recommendation.action} "
                f"(confidence: {recommendation.overall_confidence:.2f})"
            )

            return recommendation

        except Exception as e:
            logger.error(f"Error in agent analysis: {e}")
            # Return safe HOLD recommendation on error
            return TradingRecommendation(
                action="HOLD",
                instrument=instrument,
                overall_confidence=0.0,
                market_intel_weight=self.market_intel_weight,
                technical_weight=self.technical_weight,
                risk_weight=self.risk_weight,
                reasoning=f"Agent analysis failed: {str(e)}"
            )

    async def _run_market_intel(
        self,
        instrument: str,
        current_price: float,
        news_context: Optional[str]
    ) -> MarketIntelligence:
        """Run market intelligence analysis"""
        # Cache key for market intelligence (price agnostic - news doesn't change per pip)
        cache_key = hashlib.md5(f"{instrument}:{news_context or 'none'}".encode()).hexdigest()

        # Check cache
        cached = self.market_intel_cache.get(cache_key)
        if cached:
            self.cost_tracker.track_call("MarketIntelligence", "", "", cached=True)
            return cached

        prompt = f"""{instrument} @ {current_price}
News: {news_context or "None"}

Analyze: sentiment, news impact, economic events, geopolitical risk, confidence."""

        result = await self.market_intel_agent.run(prompt)
        output = result.output

        # Track and cache
        self.cost_tracker.track_call("MarketIntelligence", prompt, str(output.model_dump()))
        self.market_intel_cache.set(cache_key, output)

        return output

    async def _run_technical_analysis(
        self,
        instrument: str,
        current_price: float,
        indicators: Dict[str, Any]
    ) -> TechnicalAnalysis:
        """Run technical analysis"""
        prompt = f"""{instrument} @ {current_price}
RSI: {indicators.get('rsi', 'N/A')} | ATR: {indicators.get('atr', 'N/A')} | MA50: {indicators.get('ma_50', 'N/A')} | MA200: {indicators.get('ma_200', 'N/A')}
High: {indicators.get('recent_high', 'N/A')} | Low: {indicators.get('recent_low', 'N/A')} | Vol: {indicators.get('volatility', 'N/A')}

Signal (BUY/SELL/HOLD), entry/SL/TP, trend strength, confluence (0-5), timeframe alignment, confidence."""

        result = await self.technical_agent.run(prompt)
        output = result.output

        # Track tokens
        self.cost_tracker.track_call("TechnicalAnalysis", prompt, str(output.model_dump()))

        return output

    async def _run_risk_assessment(
        self,
        instrument: str,
        current_price: float,
        indicators: Dict[str, Any],
        account_balance: float,
        active_trades: int
    ) -> RiskAssessment:
        """Run risk assessment"""
        atr = indicators.get('atr', current_price * 0.001)
        sl_dist = 1.5 * atr
        sl_pct = sl_dist / current_price * 100

        prompt = f"""{instrument} @ {current_price}
Acct: ${account_balance:,.0f} | Active: {active_trades} | Risk: 1%
ATR: {atr} | SL dist: {sl_dist} ({sl_pct:.2f}%)

Position size (units), R:R ratio, risk level, correlation warning, max DD ok, confidence."""

        result = await self.risk_agent.run(prompt)
        output = result.output

        # Track tokens
        self.cost_tracker.track_call("RiskAssessment", prompt, str(output.model_dump()))

        return output

    async def _coordinate_decision(
        self,
        instrument: str,
        market_intel: MarketIntelligence,
        technical: TechnicalAnalysis,
        risk: RiskAssessment
    ) -> TradingRecommendation:
        """Coordinate final trading decision"""
        prompt = f"""{instrument} Final Decision

MI: Sentiment={market_intel.sentiment_score} | News={market_intel.news_impact} | Events={', '.join(market_intel.economic_events) or 'None'} | Geo={market_intel.geopolitical_risk} | Conf={market_intel.confidence}
Reasoning: {market_intel.reasoning}

TA: {technical.signal} | Entry={technical.entry_price} | SL={technical.stop_loss} | TP={technical.take_profit} | Trend={technical.trend_strength} | Confluence={technical.indicator_confluence}/5 | Aligned={technical.timeframe_alignment} | Conf={technical.confidence}
Reasoning: {technical.reasoning}

Risk: Size={risk.position_size}u | R:R={risk.risk_reward_ratio} | Level={risk.risk_level} | CorWarn={risk.correlation_warning} | DDok={risk.max_drawdown_ok} | Conf={risk.confidence}
Reasoning: {risk.reasoning}

Weights: MI={self.market_intel_weight*100}% TA={self.technical_weight*100}% Risk={self.risk_weight*100}% | Min Conf={self.min_confidence}

Action, entry/SL/TP, position size, overall confidence (weighted avg), comprehensive reasoning."""

        result = await self.coordinator_agent.run(prompt)
        recommendation = result.output

        # Track tokens
        self.cost_tracker.track_call("Coordinator", prompt, str(recommendation.model_dump()))

        # Ensure instrument is set
        recommendation.instrument = instrument

        return recommendation

    def get_cost_stats(self) -> Dict[str, Any]:
        """Get token usage and cost statistics"""
        return self.cost_tracker.get_stats()

    def estimate_monthly_cost(self, checks_per_day: int = 288) -> Dict[str, Any]:
        """
        Estimate monthly costs based on current usage.

        Args:
            checks_per_day: Number of market scans per day (default: 288 = every 5 min)
        """
        return self.cost_tracker.estimate_monthly_cost(checks_per_day)

    def reset_cost_tracker(self):
        """Reset cost tracking statistics"""
        self.cost_tracker.reset()
        self.market_intel_cache.clear()
