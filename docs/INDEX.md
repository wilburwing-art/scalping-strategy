# Documentation Index

## Quick Start
- **[README.md](../README.md)** - Project overview and getting started
- **[CLAUDE.md](../CLAUDE.md)** - Claude Code agent instructions

## Guides

### Setup & Configuration
- **[API_KEY_SETUP_GUIDE.md](guides/API_KEY_SETUP_GUIDE.md)** - Setting up OANDA and OpenAI API keys
- **[DEPLOYMENT_GUIDE.md](guides/DEPLOYMENT_GUIDE.md)** - Deploying the strategy in production
- **[SCHEDULING.md](guides/SCHEDULING.md)** - Scheduling strategy runs during market hours

### Strategy & Analysis
- **[UNIFIED_STRATEGY_GUIDE.md](guides/UNIFIED_STRATEGY_GUIDE.md)** - Comprehensive strategy documentation
- **[STRATEGY_REFINEMENTS.md](guides/STRATEGY_REFINEMENTS.md)** - Recommended strategy improvements
- **[TRANSACTION_ANALYSIS.md](guides/TRANSACTION_ANALYSIS.md)** - Analysis of trading performance
- **[AI_OPTIMIZATION_SUMMARY.md](guides/AI_OPTIMIZATION_SUMMARY.md)** - AI agent optimization results

### Status & Progress
- **[PROJECT_STATUS.md](guides/PROJECT_STATUS.md)** - Current project status
- **[NEXT_STEPS.md](guides/NEXT_STEPS.md)** - Planned improvements and roadmap
- **[API_STATUS.md](guides/API_STATUS.md)** - API integration status

## Code Structure

```
scalping-strategy/
├── core/                       # Core strategy implementation
│   ├── enhanced_scalping_strategy.py
│   ├── trading_agents.py      # Multi-agent AI system
│   └── ai_cost_tracker.py     # OpenAI cost tracking
│
├── strategies/                 # Strategy implementations
│   └── scalping_strategy.py   # Base scalping strategy
│
├── modules/                    # Additional modules
│   ├── alert_manager.py       # Trading alerts
│   ├── economic_calendar.py   # Economic event tracking
│   ├── multi_timeframe.py     # MTF analysis
│   ├── parameter_optimizer.py # Strategy optimization
│   ├── sentiment_analyzer.py  # Market sentiment
│   ├── system_monitor.py      # Health monitoring
│   └── trade_journal.py       # Trade logging
│
├── backend/                    # API backend
│   ├── api.py                 # FastAPI server
│   └── log_parser.py          # Log parsing utilities
│
├── frontend/                   # React dashboard
│   ├── src/
│   │   ├── components/        # React components
│   │   └── lib/              # Utilities
│   └── public/
│
├── scripts/                    # Utility scripts
│   ├── analysis/
│   │   └── analyze_strategy.py
│   └── run_during_market_hours.py
│
├── tests/                      # Test suite
│   ├── test_ai_optimization.py
│   ├── test_position_sizing.py
│   └── ...
│
├── docs/                       # Documentation
│   ├── INDEX.md (this file)
│   └── guides/
│
└── outputs/                    # Generated outputs
    ├── backtests/
    └── logs/
```

## Running the Strategy

### Basic Usage
```bash
# Run strategy (wrapper script)
uv run run_strategy.py

# Run with custom parameters
uv run core/enhanced_scalping_strategy.py --max-trades 5 --runtime 3600

# Analyze logs
uv run analyze_logs.py

# Run during market hours only
uv run scripts/run_during_market_hours.py
```

### Dashboard
```bash
# Start backend API
uv run uvicorn backend.api:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend && npm run dev
```

## Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific test
uv run pytest tests/test_position_sizing.py

# Test position sizing calculations
uv run tests/test_position_sizing.py
```

## Analysis Tools

```bash
# Full strategy analysis
uv run scripts/analysis/analyze_strategy.py

# Cost tracking
uv run core/ai_cost_tracker.py
```

## Configuration

- **`v20.conf`** - OANDA and OpenAI API credentials
- **`config.example.ini`** - Example configuration template
- **`pyproject.toml`** - Python dependencies and project metadata

## Logs

- **`scalping_strategy.log`** - Main strategy execution log
- **`enhanced_scalping_strategy.log`** - Enhanced strategy with AI agents
- **`logs/scheduler.log`** - Scheduled execution log
- **`logs/scheduler.error.log`** - Scheduler errors

## Next Steps

1. Review [STRATEGY_REFINEMENTS.md](guides/STRATEGY_REFINEMENTS.md) for recommended improvements
2. Check [TRANSACTION_ANALYSIS.md](guides/TRANSACTION_ANALYSIS.md) for position sizing fixes
3. See [NEXT_STEPS.md](guides/NEXT_STEPS.md) for future enhancements
