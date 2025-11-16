"""
FastAPI backend for Trading Dashboard
Provides REST API endpoints for performance metrics, configuration, and trade data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random

app = FastAPI(title="Trading Dashboard API")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class StrategyConfig(BaseModel):
    riskPercent: float
    rewardRiskRatio: float
    volumeThreshold: int
    volatilityWindow: int
    rsiPeriod: int
    maxTrades: int
    interval: int
    useAgents: bool
    agentModel: str
    minConfidence: float

class PerformanceMetrics(BaseModel):
    totalTrades: int
    winRate: float
    profitFactor: float
    sharpeRatio: float
    maxDrawdown: float
    avgWin: float
    avgLoss: float
    totalProfit: float
    bestTrade: float
    worstTrade: float

class EquityDataPoint(BaseModel):
    date: str
    equity: float
    profit: float
    trades: int

class StrategyStatus(BaseModel):
    isRunning: bool
    lastUpdate: str
    totalTrades: int
    openPositions: int

class AgentScore(BaseModel):
    name: str
    confidence: float
    sentiment: Optional[float] = None
    reasoning: str

class AISignal(BaseModel):
    instrument: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[int] = None
    timestamp: str
    agents: List[AgentScore]
    overall_reasoning: str

class AgentStatus(BaseModel):
    enabled: bool
    model: str
    min_confidence: float
    market_intel_weight: float
    technical_weight: float
    risk_weight: float
    total_analyses: int
    avg_confidence: float
    last_analysis: Optional[str] = None

class CostStats(BaseModel):
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    api_calls: int
    cached_calls: int
    cache_hit_rate: float
    estimated_cost: float
    cost_per_hour: float
    tokens_per_hour: float

# In-memory storage (replace with database in production)
current_config = StrategyConfig(
    riskPercent=1.0,
    rewardRiskRatio=1.5,
    volumeThreshold=1000,
    volatilityWindow=14,
    rsiPeriod=14,
    maxTrades=3,
    interval=300,
    useAgents=True,
    agentModel="gpt-4o",
    minConfidence=0.6,
)

strategy_status = StrategyStatus(
    isRunning=False,
    lastUpdate=datetime.now().isoformat(),
    totalTrades=0,
    openPositions=0,
)

# AI agent storage with initial mock data
recent_ai_signals: List[AISignal] = [
    AISignal(
        instrument="EUR_USD",
        action="BUY",
        confidence=0.85,
        entry_price=1.0850,
        stop_loss=1.0820,
        take_profit=1.0900,
        position_size=10000,
        timestamp=datetime.now().isoformat(),
        agents=[
            AgentScore(name="Market Intelligence", confidence=0.80, reasoning="Positive ECB sentiment, EUR strength indicators"),
            AgentScore(name="Technical Analysis", confidence=0.85, reasoning="Strong uptrend, RSI oversold bounce, MA alignment"),
            AgentScore(name="Risk Assessment", confidence=0.90, reasoning="Low volatility, favorable R:R ratio 1:2.5")
        ],
        overall_reasoning="High-probability long setup: Technical indicators show strong momentum with RSI bounce from oversold, supported by positive market sentiment and low correlation risk."
    ),
    AISignal(
        instrument="GBP_JPY",
        action="SELL",
        confidence=0.72,
        entry_price=189.45,
        stop_loss=189.95,
        take_profit=188.70,
        position_size=8000,
        timestamp=(datetime.now() - timedelta(minutes=15)).isoformat(),
        agents=[
            AgentScore(name="Market Intelligence", confidence=0.65, reasoning="BOJ hawkish stance, risk-off sentiment building"),
            AgentScore(name="Technical Analysis", confidence=0.75, reasoning="Resistance at 189.50, bearish divergence on 1H"),
            AgentScore(name="Risk Assessment", confidence=0.75, reasoning="Moderate risk, trending pair with clear levels")
        ],
        overall_reasoning="Counter-trend setup at resistance: Price approaching key resistance with divergence signals. Risk managed with tight stop above resistance zone."
    ),
]

agent_status = AgentStatus(
    enabled=current_config.useAgents,
    model=current_config.agentModel,
    min_confidence=current_config.minConfidence,
    market_intel_weight=0.3,
    technical_weight=0.4,
    risk_weight=0.3,
    total_analyses=2,
    avg_confidence=0.785,
    last_analysis=datetime.now().isoformat(),
)

# Helper function to generate mock equity data
def generate_equity_data(days: int = 30) -> List[EquityDataPoint]:
    data = []
    equity = 10000
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        change = (random.random() - 0.45) * 100
        equity += change
        data.append(EquityDataPoint(
            date=(base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            equity=round(equity, 2),
            profit=round(change, 2),
            trades=random.randint(1, 10),
        ))

    return data

# API Endpoints

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Trading Dashboard API"}

@app.get("/api/metrics", response_model=PerformanceMetrics)
def get_metrics():
    """Get current performance metrics"""
    # TODO: Calculate from actual trading history
    return PerformanceMetrics(
        totalTrades=247,
        winRate=68.4,
        profitFactor=2.3,
        sharpeRatio=1.8,
        maxDrawdown=-8.5,
        avgWin=45.2,
        avgLoss=-32.8,
        totalProfit=2847.50,
        bestTrade=285.40,
        worstTrade=-124.30,
    )

@app.get("/api/equity", response_model=List[EquityDataPoint])
def get_equity_data(days: int = 30):
    """Get equity curve data"""
    return generate_equity_data(days)

@app.get("/api/config", response_model=StrategyConfig)
def get_config():
    """Get current strategy configuration"""
    return current_config

@app.post("/api/config", response_model=StrategyConfig)
def update_config(config: StrategyConfig):
    """Update strategy configuration"""
    global current_config
    current_config = config
    # TODO: Apply configuration to running strategy
    return current_config

@app.get("/api/status", response_model=StrategyStatus)
def get_status():
    """Get strategy running status"""
    return strategy_status

@app.post("/api/start")
def start_strategy():
    """Start the trading strategy"""
    global strategy_status
    strategy_status.isRunning = True
    strategy_status.lastUpdate = datetime.now().isoformat()
    # TODO: Actually start the strategy
    return {"status": "started", "message": "Strategy started successfully"}

@app.post("/api/stop")
def stop_strategy():
    """Stop the trading strategy"""
    global strategy_status
    strategy_status.isRunning = False
    strategy_status.lastUpdate = datetime.now().isoformat()
    # TODO: Actually stop the strategy
    return {"status": "stopped", "message": "Strategy stopped successfully"}

@app.get("/api/ai-signals", response_model=List[AISignal])
def get_ai_signals(limit: int = 20):
    """Get recent AI agent trading signals"""
    return recent_ai_signals[-limit:] if recent_ai_signals else []

@app.get("/api/agent-status", response_model=AgentStatus)
def get_agent_status():
    """Get current AI agent system status"""
    return agent_status

@app.post("/api/agent-signal")
def add_ai_signal(signal: AISignal):
    """Add a new AI signal (called by strategy)"""
    global recent_ai_signals, agent_status

    recent_ai_signals.append(signal)

    # Keep only last 100 signals
    if len(recent_ai_signals) > 100:
        recent_ai_signals = recent_ai_signals[-100:]

    # Update agent status
    agent_status.total_analyses += 1
    agent_status.last_analysis = signal.timestamp

    # Update rolling average confidence
    if agent_status.total_analyses == 1:
        agent_status.avg_confidence = signal.confidence
    else:
        agent_status.avg_confidence = (
            agent_status.avg_confidence * 0.9 + signal.confidence * 0.1
        )

    return {"status": "ok", "message": "Signal added"}

@app.get("/api/cost-stats")
def get_cost_stats():
    """Get AI token usage and cost statistics"""
    # Mock data for now - will be populated by strategy
    return {
        "total": {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "api_calls": 0,
            "cached_calls": 0,
            "cache_hit_rate": 0.0,
            "estimated_cost": 0.0,
            "cost_per_hour": 0.0,
            "tokens_per_hour": 0.0
        },
        "by_agent": {},
        "model": current_config.agentModel,
        "monthly_estimate": {
            "cost_per_check": 0.0,
            "daily_cost": 0.0,
            "monthly_cost": 0.0,
            "daily_tokens": 0,
            "monthly_tokens": 0,
            "within_free_tier": True,
            "free_tier_limit": 2_500_000,
            "free_tier_usage_pct": 0.0
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
