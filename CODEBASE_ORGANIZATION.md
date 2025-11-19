# Codebase Organization

**Date:** 2025-11-18
**Status:** ✅ Complete

---

## Summary

Reorganized codebase into a clean, professional structure with proper separation of concerns.

## New Directory Structure

```
scalping-strategy/
├── 📄 Root-level files
│   ├── README.md                  # Project overview
│   ├── CLAUDE.md                  # AI assistant instructions
│   ├── pyproject.toml             # Python dependencies
│   ├── v20.conf                   # OANDA API credentials (gitignored)
│   ├── config.example.ini         # Configuration template
│   ├── run_strategy.py            # 🆕 Wrapper to run strategy
│   └── analyze_logs.py            # 🆕 Wrapper to analyze logs
│
├── 📦 core/                       # 🆕 Core strategy implementation
│   ├── enhanced_scalping_strategy.py  # Main strategy with AI agents
│   ├── trading_agents.py              # Multi-agent AI system
│   └── ai_cost_tracker.py             # OpenAI cost tracking
│
├── 📊 strategies/                 # Strategy implementations
│   └── scalping_strategy.py      # Base scalping strategy (✅ FIXED position sizing)
│
├── 🧩 modules/                    # Feature modules
│   ├── alert_manager.py           # Trading alerts
│   ├── economic_calendar.py       # Economic events
│   ├── multi_timeframe.py         # Multi-timeframe analysis
│   ├── parameter_optimizer.py     # Strategy optimization
│   ├── sentiment_analyzer.py      # Market sentiment
│   ├── system_monitor.py          # Health monitoring
│   └── trade_journal.py           # Trade logging
│
├── 🔧 scripts/                    # 🆕 Utility scripts
│   ├── analysis/
│   │   └── analyze_strategy.py    # Log analysis tool
│   └── run_during_market_hours.py # Scheduler script
│
├── 🧪 tests/                      # Test suite
│   ├── test_position_sizing.py    # 🆕 Position sizing tests
│   ├── test_ai_optimization.py    # AI optimization tests
│   ├── test_alpha_vantage.py      # API integration tests
│   ├── test_openai_agents.py      # Agent system tests
│   └── test_*.py                  # Other tests
│
├── 🌐 backend/                    # API server
│   ├── api.py                     # FastAPI server
│   └── log_parser.py              # Log parsing utilities
│
├── 💻 frontend/                   # React dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── About.jsx          # 🆕 About page
│   │   │   ├── AIAgents.jsx       # ✅ FIXED confidence scores
│   │   │   ├── PerformanceAnalytics.jsx
│   │   │   └── StrategyConfig.jsx
│   │   └── lib/
│   │       ├── api.js
│   │       └── utils.js
│   └── public/
│
├── 📚 docs/                       # 🆕 Documentation
│   ├── INDEX.md                   # 🆕 Documentation index
│   └── guides/                    # 🆕 Organized guides
│       ├── STRATEGY_REFINEMENTS.md    # 🆕 Strategy analysis
│       ├── TRANSACTION_ANALYSIS.md    # 🆕 Position sizing fix
│       ├── API_KEY_SETUP_GUIDE.md
│       ├── DEPLOYMENT_GUIDE.md
│       ├── UNIFIED_STRATEGY_GUIDE.md
│       └── ...
│
├── 📤 outputs/                    # Generated files
│   ├── backtests/
│   └── logs/
│
└── 📝 logs/                       # Runtime logs
    ├── scheduler.log
    └── scheduler.error.log
```

---

## What Changed

### Moved Files

**Core Strategy → `core/`**
```
enhanced_scalping_strategy.py  → core/enhanced_scalping_strategy.py
trading_agents.py              → core/trading_agents.py
ai_cost_tracker.py             → core/ai_cost_tracker.py
```

**Tests → `tests/`**
```
test_ai_optimization.py        → tests/test_ai_optimization.py
test_alpha_vantage.py          → tests/test_alpha_vantage.py
test_openai_agents.py          → tests/test_openai_agents.py
test_position_sizing.py        → tests/test_position_sizing.py (🆕)
test_twitter_api.py            → tests/test_twitter_api.py
```

**Scripts → `scripts/`**
```
analyze_strategy.py            → scripts/analysis/analyze_strategy.py
run_during_market_hours.py     → scripts/run_during_market_hours.py
```

**Documentation → `docs/guides/`**
```
AI_OPTIMIZATION_SUMMARY.md     → docs/guides/
API_KEY_SETUP_GUIDE.md         → docs/guides/
API_STATUS.md                  → docs/guides/
DEPLOYMENT_GUIDE.md            → docs/guides/
NEXT_STEPS.md                  → docs/guides/
PROJECT_STATUS.md              → docs/guides/
SCHEDULING.md                  → docs/guides/
STRATEGY_REFINEMENTS.md        → docs/guides/ (🆕)
TRANSACTION_ANALYSIS.md        → docs/guides/ (🆕)
UNIFIED_STRATEGY_GUIDE.md      → docs/guides/
```

### New Files

**Root-level convenience scripts:**
- `run_strategy.py` - Wrapper to run enhanced strategy
- `analyze_logs.py` - Wrapper to analyze strategy logs

**Documentation:**
- `docs/INDEX.md` - Complete documentation index
- `docs/guides/STRATEGY_REFINEMENTS.md` - Strategy analysis & recommendations
- `docs/guides/TRANSACTION_ANALYSIS.md` - Position sizing bug analysis & fix

**Tests:**
- `tests/test_position_sizing.py` - Position sizing calculation tests

**Frontend:**
- `frontend/src/components/About.jsx` - About page with strategy details

### Updated Files

**Fixed imports:**
- `core/enhanced_scalping_strategy.py` - Updated to import from `core.trading_agents`
- `core/trading_agents.py` - Updated to import from `core.ai_cost_tracker`

**Fixed bugs:**
- `strategies/scalping_strategy.py` - **CRITICAL FIX**: Position sizing now converts price to pips correctly
- `frontend/src/components/AIAgents.jsx` - Fixed confidence score display (NaN% → actual percentages)

---

## How to Use

### Run Strategy

```bash
# New convenient way
uv run run_strategy.py

# Direct way
uv run core/enhanced_scalping_strategy.py --max-trades 5

# With scheduler
uv run scripts/run_during_market_hours.py
```

### Analyze Logs

```bash
# New convenient way
uv run analyze_logs.py

# Direct way
uv run scripts/analysis/analyze_strategy.py
```

### Run Tests

```bash
# All tests
uv run pytest tests/

# Specific test
uv run pytest tests/test_position_sizing.py

# Position sizing validation
uv run tests/test_position_sizing.py
```

### Dashboard

```bash
# Start backend
uv run uvicorn backend.api:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Open browser: http://localhost:3000
```

---

## Import Changes

If you have custom scripts that import these files, update them:

**Old:**
```python
from enhanced_scalping_strategy import EnhancedScalpingStrategy
from trading_agents import TradingAgentSystem
from ai_cost_tracker import CostTracker
```

**New:**
```python
from core.enhanced_scalping_strategy import EnhancedScalpingStrategy
from core.trading_agents import TradingAgentSystem
from core.ai_cost_tracker import CostTracker
```

---

## Benefits

1. **Clear separation of concerns** - Core code, tests, scripts, and docs in separate directories
2. **Easier navigation** - Find files quickly based on purpose
3. **Professional structure** - Standard Python project layout
4. **Better documentation** - All guides organized in docs/guides/
5. **Convenience wrappers** - Easy-to-use scripts in root directory
6. **Maintained backwards compatibility** - Wrapper scripts preserve original usage patterns

---

## Documentation

See **[docs/INDEX.md](docs/INDEX.md)** for complete documentation index with links to all guides.

---

## Next Steps

1. ✅ Position sizing fixed - test with real trades
2. ✅ Dashboard displaying real data
3. ⬜ Implement max_trades=5 recommendation
4. ⬜ Review agent prompts for BUY/SELL bias
5. ⬜ Run 1-week test with fixes

---

## Files Kept in Root

**Essential config:**
- `README.md` - Project overview
- `CLAUDE.md` - AI assistant instructions
- `pyproject.toml` - Dependencies
- `v20.conf` - API credentials (gitignored)
- `config.example.ini` - Config template

**Logs (generated at runtime):**
- `scalping_strategy.log`
- `enhanced_scalping_strategy.log`

**Convenience scripts:**
- `run_strategy.py` - Quick access to run strategy
- `analyze_logs.py` - Quick access to analyze logs
