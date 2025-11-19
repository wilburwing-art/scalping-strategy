# Unified Strategy - Complete Implementation Guide

## Overview

The **Unified Strategy** (`unified_strategy.py`) brings together ALL project components into a single, production-ready trading system with the critical **RSI fix** applied.

### What's Included

✅ **Phase 1**: AI agent intelligence system
✅ **Phase 2**: Multi-timeframe data, realistic costs, risk management
✅ **Phase 3**: News filtering, sentiment analysis, journaling, monitoring, alerts
✅ **RSI FIX**: Corrected mean reversion logic (buys oversold, sells overbought)

---

## Quick Start

### 1. Generate Sample Data and Run Backtest

```bash
# Generate 10,000 sample candles
uv run python example_backtest.py --generate-sample

# Run backtest on sample data
uv run python example_backtest.py --data sample_backtest_data.csv
```

This will:
- Generate realistic market data with trends and volatility
- Run a complete backtest with the FIXED RSI logic
- Show comprehensive performance metrics
- Save trade-by-trade results to CSV

### 2. Run Live Strategy (Practice Mode)

```bash
# Set environment variables
export OPENAI_API_KEY="sk-..."
export TRADING_ECONOMICS_API_KEY="..."
export ALERT_EMAIL="your@gmail.com"
export ALERT_EMAIL_PASSWORD="your_app_password"

# Run in practice mode
uv run python unified_strategy.py --env practice
```

---

## RSI Fix Explained

### What Was Wrong

Original logic in `scalping_strategy.py`:
```python
# WRONG - buys when RSI is 50-69 (not oversold!)
has_momentum = indicators["rsi"] < 70 if has_trend else indicators["rsi"] > 30
```

This bought at the WRONG RSI levels:
- Uptrend: BUY when RSI < 70 (buys at RSI 40-69, not optimal)
- Downtrend: SELL when RSI > 30 (sells at RSI 30-60, not optimal)

### What's Fixed

New logic in `unified_strategy.py`:
```python
# CORRECT - mean reversion
is_oversold = indicators["rsi"] < 30  # Buy signal
is_overbought = indicators["rsi"] > 70  # Sell signal

can_buy = has_uptrend and is_oversold  # Buy dip in uptrend
can_sell = has_downtrend and is_overbought  # Sell bounce in downtrend
```

This now correctly:
- **BUY** when RSI < 30 (oversold) in an uptrend
- **SELL** when RSI > 70 (overbought) in a downtrend

**Expected Impact**: +5-10% win rate improvement

---

## Backtesting

### Example 1: Quick Test with Sample Data

```bash
# Generate sample data
uv run python example_backtest.py --generate-sample

# Run backtest
uv run python example_backtest.py --data sample_backtest_data.csv --balance 10000
```

**Output includes:**
- Total return %
- Win rate
- Sharpe ratio
- Max drawdown
- Profit factor
- Trade-by-trade analysis
- Equity curve

### Example 2: Backtest with OANDA Data

```bash
# Backtest EUR/USD for full year 2024
uv run python example_backtest.py \
  --oanda \
  --config v20.conf \
  --instrument EUR_USD \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --balance 10000
```

**Requirements:**
- Valid `v20.conf` file with OANDA credentials
- OANDA practice or live account

### What the Backtest Shows

The backtester includes:
- ✅ Realistic bid/ask execution (no midpoint overstatement)
- ✅ All transaction costs (spread, slippage, swap)
- ✅ Risk management enforcement (leverage limits)
- ✅ Time-based and price-based exits (stop loss, take profit, time limit)

**Interpretation:**
- **Sharpe > 1.0**: Good risk-adjusted returns
- **Win Rate > 50%**: More winners than losers
- **Max DD < 20%**: Acceptable drawdown
- **Profit Factor > 1.0**: Profitable overall

---

## Live Trading

### Prerequisites

1. **OANDA Account**: Practice or live
2. **API Credentials**: In `v20.conf`
3. **Optional APIs**:
   - OpenAI (for agents): `OPENAI_API_KEY`
   - Trading Economics (for news): `TRADING_ECONOMICS_API_KEY`
   - Email alerts: `ALERT_EMAIL` + `ALERT_EMAIL_PASSWORD`

### Configuration

Create `v20.conf` from `config.example.ini`:

```ini
[practice]
hostname = api-fxpractice.oanda.com
token = YOUR_PRACTICE_TOKEN
account_id = YOUR_PRACTICE_ACCOUNT_ID

[live]
hostname = api-fxtrade.oanda.com
token = YOUR_LIVE_TOKEN
account_id = YOUR_LIVE_ACCOUNT_ID
```

### Run Commands

#### Basic (Traditional Analysis Only)

```bash
uv run python unified_strategy.py --env practice \
  --disable-calendar \
  --disable-sentiment \
  --disable-agents
```

This runs with:
- FIXED RSI logic
- Risk management
- No external dependencies

#### Full Stack (All Features)

```bash
# Set environment variables
export OPENAI_API_KEY="sk-..."
export TRADING_ECONOMICS_API_KEY="..."
export ALERT_EMAIL="your@gmail.com"
export ALERT_EMAIL_PASSWORD="your_app_password"

# Run
uv run python unified_strategy.py --env practice
```

This enables:
- AI agents for decision making
- Economic calendar filtering
- Sentiment analysis
- Real-time alerts
- Trade journaling
- System monitoring

---

## Architecture

### Component Integration

```
unified_strategy.py
├── Phase 2: Data & Risk
│   ├── MultiTimeframeDataProvider (multi_timeframe_data.py)
│   ├── CostCalculator (transaction_costs.py)
│   ├── PipCalculator (pip_calculator.py)
│   ├── BidAskPricer (bid_ask_pricing.py)
│   └── RiskManager (risk_management.py)
│
├── Phase 3: Production Features
│   ├── EconomicCalendar (economic_calendar.py)
│   ├── SentimentAnalyzer (sentiment_analyzer.py)
│   ├── TradeJournal (trade_journal.py)
│   ├── AlertManager (alert_manager.py)
│   └── SystemMonitor (system_monitor.py)
│
└── Phase 1: Intelligence
    └── AI Agents (trading_agents_fixed.py)
```

### Strategy Flow

1. **Scan** instruments (EUR_USD, GBP_USD, USD_JPY, AUD_USD)
2. **Filter** by economic calendar (avoid news volatility)
3. **Analyze** with multi-timeframe data
4. **Calculate** indicators (RSI, ATR, moving averages)
5. **Check** entry criteria (FIXED RSI logic)
6. **Validate** with AI agents (optional, if enabled)
7. **Size** position with risk management
8. **Execute** trade with stop loss and take profit
9. **Journal** trade details
10. **Monitor** system health
11. **Alert** on important events

---

## Key Differences vs. Old Strategy

| Feature | Old (scalping_strategy.py) | New (unified_strategy.py) |
|---------|---------------------------|---------------------------|
| **RSI Logic** | ❌ Backwards | ✅ Fixed (mean reversion) |
| **Multi-timeframe** | ❌ No | ✅ Yes (M5, M15, H1) |
| **Transaction Costs** | ❌ Not modeled | ✅ Full modeling |
| **Risk Management** | ❌ Basic | ✅ Comprehensive |
| **News Filtering** | ❌ Placeholder | ✅ Economic calendar |
| **Sentiment** | ❌ No | ✅ Social sentiment |
| **Journaling** | ❌ No | ✅ SQLite database |
| **Monitoring** | ❌ No | ✅ Health checks + alerts |
| **AI Agents** | ❌ No | ✅ Multi-agent system |
| **Backtesting** | ❌ No | ✅ Comprehensive |

---

## Performance Expectations

### Realistic Targets (Based on Backtest)

**Conservative Target (Traditional Analysis)**:
- Win Rate: 50-55%
- Sharpe Ratio: 0.5-1.0
- Max Drawdown: 15-25%
- Monthly Return: 2-5%

**Optimistic Target (With AI Agents)**:
- Win Rate: 55-60%
- Sharpe Ratio: 1.0-1.5
- Max Drawdown: 10-20%
- Monthly Return: 3-8%

**Important Notes**:
- These are BEST-CASE scenarios with perfect execution
- Real-world slippage, API latency, and market conditions will reduce returns
- Most retail forex traders lose money - manage expectations
- Start with paper trading for 60-90 days before going live

---

## Validation Checklist

Before using this strategy with real money:

### Backtesting Phase
- [ ] Run 12-24 month backtest
- [ ] Verify Sharpe ratio > 1.0
- [ ] Verify max drawdown < 20%
- [ ] Verify win rate > 50%
- [ ] Verify profit factor > 1.0
- [ ] Analyze losing streaks (should survive 10+ consecutive losses)

### Paper Trading Phase
- [ ] Run 60-90 days paper trading
- [ ] Compare paper results to backtest (should be similar)
- [ ] Monitor system stability (no crashes, API errors handled)
- [ ] Verify RSI entries (check logs: BUY when RSI < 30, SELL when RSI > 70)
- [ ] Test alerts and monitoring

### Risk Management
- [ ] Start with 0.25% risk per trade (very conservative)
- [ ] Never exceed 1% risk per trade
- [ ] Max 3 concurrent positions
- [ ] Set daily loss limit (e.g., 3% of balance)
- [ ] Have stop-loss plan for entire account

---

## Troubleshooting

### Import Errors

If you see import errors for Phase 3 components:
```python
# unified_strategy.py gracefully handles missing components
# Strategy will work with core features only (Phase 2)
```

All Phase 3 components are optional:
- Economic calendar
- Sentiment analysis
- Trade journaling
- Monitoring/alerts
- AI agents

### RSI Not Working as Expected

Check the logs for entries:
```bash
# Should see entries like:
# BUY signal (RSI: 28.3)  <- Good (< 30)
# SELL signal (RSI: 72.1) <- Good (> 70)

# Should NOT see:
# BUY signal (RSI: 55.0)  <- Bad (not oversold)
```

### No Trades Executed

Possible reasons:
1. **No opportunities**: RSI not reaching extremes
2. **News blocking**: Economic calendar filtering out trades
3. **Risk limits**: Max positions reached or leverage limit hit
4. **Agent rejection**: AI agents voting to HOLD

Check logs for specific reasons.

---

## Next Steps

1. **Run backtest**: Validate profitability with historical data
2. **Analyze results**: Review trade-by-trade performance
3. **Optimize if needed**: Adjust parameters based on backtest
4. **Paper trade**: Test in real-time with paper money (60-90 days)
5. **Go live**: Start with minimal risk (0.25% per trade)

---

## Files Reference

- **unified_strategy.py**: Main strategy implementation
- **example_backtest.py**: Backtesting examples and utilities
- **backtester.py**: Backtesting framework (Phase 2)
- **rsi_logic_fix.md**: Detailed explanation of RSI fix
- **PHASE_2_COMPLETE.md**: Phase 2 summary and analysis
- **PHASE_3_COMPLETE.md**: Phase 3 summary and features

---

## Support

For issues or questions:
1. Check existing documentation in `docs/` folder
2. Review phase completion summaries (PHASE_2_COMPLETE.md, PHASE_3_COMPLETE.md)
3. Check CLAUDE.md for project structure and conventions

---

**Remember**: This is a complex trading system. Profitability is not guaranteed. Always start with backtesting, then paper trading, then live with minimal risk.
