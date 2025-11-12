# Swing Trading Analysis - November 11, 2025

## Backtest Results Summary

### Swing (4H) vs Scalping (5m) Comparison

| Metric | Scalping (5m) | Swing (4H) | Winner |
|--------|---------------|------------|--------|
| Total Return | -4.52% | -15.36% | Scalping |
| Win Rate | 10.5% | 14.3% | Swing |
| Sharpe Ratio | -0.46 | -9.16 | Scalping |
| Total Trades | 95 | 28 | Scalping (more data) |
| Profit Factor | 0.37 | 0.31 | Scalping |

## Key Findings

### Why Swing Strategy Failed (Sample Data)

1. **Very Low Win Rate**: 14.3% (4/28 trades won)
   - Need at least 40-50% win rate with 2:1 R:R for profitability
   - Current: 4 wins, 24 losses

2. **Poor Profit Factor**: 0.31
   - Need > 1.0 to be profitable
   - Total wins ($694) < Total losses ($2,230)

3. **Parameter Issues**:
   - RSI thresholds (35/65) might be TOO relaxed
   - Entering too early in trends
   - Stop loss distance (2.0x ATR) might be too wide for sample data volatility

4. **Sample Data Limitations**:
   - Randomly generated, not realistic market conditions
   - No real trend persistence
   - Volatility patterns don't match real forex
   - Missing market microstructure

## Critical Insight: Sample Data vs Real Data

**These results are from SYNTHETIC data, not real markets.**

Sample data issues:
- Random walk with regime changes
- No true market structure (support/resistance)
- No correlation between timeframes
- No real economic events
- Spread/slippage are estimated

**Next step: MUST test with real OANDA historical data.**

## Parameter Adjustment Recommendations

### Option 1: Tighten RSI Thresholds
Current: 35/65 (very relaxed)
Suggested: 30/70 (more extreme)

Rationale: Only trade the most extreme pullbacks

```python
self.rsi_oversold = 30  # Was 35
self.rsi_overbought = 70  # Was 65
```

### Option 2: Adjust R:R Ratio
Current: 2:1
Suggested: 1.5:1

Rationale: Wider targets (2:1) harder to hit, lower win rate

```python
self.reward_risk_ratio = 1.5  # Was 2.0
```

### Option 3: Tighter Stops
Current: 2.0x ATR
Suggested: 1.5x ATR

Rationale: Reduce loss size, improve profit factor

```python
self.atr_multiplier = 1.5  # Was 2.0
```

### Option 4: Add Volume Filter
Add minimum volume requirement to avoid low-liquidity trades:

```python
min_volume = 500  # 4H candles need decent volume
if row['volume'] < min_volume:
    continue  # Skip entry
```

## AI Agents & Phase 3 Impact

**Important**: The backtest does NOT include AI agents or Phase 3 features because:

1. **AI Agents**: Require real-time OpenAI API calls
   - Not practical for 12-month backtest (expensive, slow)
   - Can't backtest agent decisions on historical data accurately

2. **Economic Calendar**: Would need historical event data
   - Trading Economics API doesn't provide historical free-tier access

3. **Sentiment Analysis**: Would need historical social data
   - Twitter/Reddit historical data not available

**Where AI Agents Help**: Live/paper trading only
- Real-time market intelligence
- News impact assessment
- Risk management decisions
- Entry timing refinement

## Recommended Action Plan

### Path A: Test with Real OANDA Data (RECOMMENDED)

1. Modify backtest to fetch real historical data from OANDA API
2. Run 12-month backtest with EUR/USD 4H candles
3. Compare results to sample data

**Why**: Real market structure will give accurate win rate, R:R, and profitability metrics.

**How**: Create `swing_backtest_oanda.py` that uses OANDA v20 API to fetch historical candles.

### Path B: Optimize Parameters on Sample Data

1. Run grid search on:
   - RSI thresholds: [30/70, 35/65, 40/60]
   - R:R ratios: [1.5, 2.0, 2.5]
   - ATR multipliers: [1.5, 2.0, 2.5]
   - MA periods: [10/20, 20/50, 50/200]

2. Find best combination
3. Test on out-of-sample data

**Why**: Might find profitable parameters for current data.

**Risk**: Overfitting to sample data. Results won't generalize to real markets.

### Path C: Paper Trade with AI Agents (HIGHEST VALUE)

1. Skip backtest validation (we know sample data isn't reliable)
2. Deploy swing_strategy.py to OANDA practice account
3. Enable ALL Phase 3 features:
   - AI agents for entry/exit decisions
   - Economic calendar filtering
   - Sentiment analysis
   - Trade journaling
   - System monitoring

4. Paper trade for 30-60 days
5. Analyze real performance

**Why**:
- AI agents can significantly improve win rate (estimated +10-20%)
- Real market conditions expose true strategy performance
- Fastest path to validation

**Risk**: No historical validation. Could lose practice account balance.

## Cost-Benefit Analysis

### Path A: Real OANDA Data Backtest
- **Cost**: 2-3 hours development, API rate limits
- **Benefit**: Accurate historical performance metrics
- **Risk**: Low

### Path B: Parameter Optimization
- **Cost**: 1-2 hours, overfitting risk
- **Benefit**: Might find profitable parameters (for sample data only)
- **Risk**: High (results won't generalize)

### Path C: Paper Trading with AI
- **Cost**: $10-20/month (OpenAI, APIs), practice account balance
- **Benefit**: Real performance data, AI agent validation
- **Risk**: Medium (might lose practice balance)

## My Recommendation

**Go with Path C: Paper Trading with Full Phase 3 Stack**

Reasoning:
1. Sample data backtests are unreliable (we've proven this twice)
2. Real OANDA historical data is better but still backward-looking
3. AI agents are the differentiator - they can't be backtested accurately
4. Paper trading gives real-time validation with no financial risk
5. 30-60 days of paper trading > 12 months of synthetic backtest

## Implementation Steps (Path C)

1. **Configure API Keys** (5 minutes):
   ```bash
   export OPENAI_API_KEY="your-key"
   export TRADING_ECONOMICS_API_KEY="your-key"  # Optional
   ```

2. **Update v20.conf** (done - already configured)

3. **Run Paper Trading**:
   ```bash
   uv run python swing_strategy.py --env practice --paper-trade
   ```

4. **Monitor Performance** (daily):
   - Check trade journal database
   - Review system monitoring alerts
   - Analyze AI agent recommendations

5. **Validation Criteria** (after 30-60 days):
   - Win rate > 40%
   - Sharpe ratio > 0.5
   - Max drawdown < 15%
   - Profit factor > 1.2

6. **Decision Point**:
   - If profitable → Continue paper trading for 90 days total
   - If not profitable → Adjust parameters, re-test for 30 days
   - If still not profitable → Reconsider strategy fundamentals

## Alternative: Quick Parameter Test

If you want to try adjusted parameters before paper trading:

```bash
# Create swing_backtest_v2.py with:
# - RSI: 30/70 (was 35/65)
# - R:R: 1.5 (was 2.0)
# - ATR multiplier: 1.5 (was 2.0)
# - Add volume filter

uv run python swing_backtest_v2.py
```

If this shows > 0% return on sample data, it's a positive signal (but still need real validation).

## Bottom Line

**Sample data backtests have failed to show profitability for both strategies.**

This doesn't mean the strategies are bad - it means:
1. Sample data is too simplistic
2. Strategies need real market conditions to perform
3. AI agents can't be backtested (they're the secret sauce)

**Next step**: Either get real historical data OR skip to paper trading with full Phase 3 stack.

**My vote**: Paper trading with AI agents. Let's see what the system can do in the real world.
