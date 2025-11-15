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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
