# Strategy Refinement Analysis

**Analysis Date:** 2025-11-18
**Signals Analyzed:** 153
**Total Cost:** $0.053
**Agent Calls:** 453

---

## Key Findings

### 1. **CRITICAL: Signal Action Imbalance**
- **SELL: 54.9%** (84 signals)
- **HOLD: 38.6%** (59 signals)
- **BUY: 6.5%** (10 signals)

**Problem:** Massive bias towards SELL signals. Only 10 BUY signals out of 153 total.

**Root Causes:**
- Market conditions during testing period may have been bearish
- Agent prompts may have directional bias
- Technical indicators (RSI, MA) may be calibrated for downtrends

**Action Required:**
1. Review TechnicalAnalysis agent prompt for bias
2. Add balanced sampling across market conditions
3. Implement "bias detector" that warns when BUY/SELL ratio deviates >2:1

---

### 2. **CRITICAL: Max Trades Bottleneck**
- **100% of skipped trades** are due to max_trades=3 limit being reached
- 75 opportunities were skipped despite having valid signals

**Impact:**
- Missing 49% of potential trades (75 skipped / 153 analyzed)
- High-confidence signals are being rejected simply due to timing

**Recommended Changes:**

```python
# Current
max_trades = 3

# Proposed
max_trades = 5  # or implement priority queue
```

**Alternative: Priority Queue**
- Close lowest-confidence trade when new higher-confidence signal appears
- Requires tracking active trade confidence scores

---

### 3. **HOLD Signal Optimization**
- 38.6% of signals are HOLD with average confidence of only 0.406
- Many HOLD signals have near-zero confidence (min=0.000)

**Issue:** Agents defaulting to HOLD when uncertain rather than abstaining

**Recommended Changes:**
1. Add "minimum confidence for HOLD" threshold (e.g., 0.4)
2. Instruct agents to return HOLD only when genuinely neutral, not uncertain
3. Consider ternary system: BUY/SELL/INSUFFICIENT_DATA

---

### 4. Agent Cost Efficiency

**Cost Breakdown:**
| Agent | Tokens/Call | Cost % |
|-------|-------------|--------|
| Market Intelligence | 126.1 | 20.9% |
| Technical Analysis | 245.7 | 21.5% |
| Risk Assessment | 176.6 | 21.1% |
| Coordinator | 508.5 | **36.4%** |

**Observations:**
- Coordinator uses 508 tokens/call vs 126-245 for specialists
- This is expected (needs to process all inputs) but could be optimized

**Cost Projection:**
- Current: **$4.04/month** (24h operation, 5-min intervals)
- With max_trades=5: ~$4.50/month (more analyses run)

**Optimization Options:**
1. Use `gpt-4o-mini` for Coordinator only (60% cost reduction)
2. Implement response caching for similar market conditions
3. Reduce coordinator prompt verbosity

---

### 5. Confidence Distribution

**Good News:**
- 53.6% of signals are high confidence (≥0.70)
- BUY signals: avg 0.752 (very good)
- SELL signals: avg 0.749 (very good)
- HOLD signals: avg 0.406 (problematic)

**Recommendation:** Current 0.6 threshold is appropriate. Do not lower.

---

## Recommended Configuration Changes

### Immediate (High Priority)

```python
# In enhanced_scalping_strategy.py or config

# 1. Increase max trades
max_trades = 5  # was 3

# 2. Add HOLD confidence filter
min_hold_confidence = 0.4  # Reject low-confidence HOLD signals

# 3. Add bias monitoring
def check_signal_bias(recent_signals, window=50):
    """Alert if BUY/SELL ratio is imbalanced"""
    buys = sum(1 for s in recent_signals[-window:] if s.action == "BUY")
    sells = sum(1 for s in recent_signals[-window:] if s.action == "SELL")

    if sells > 0 and buys / sells < 0.5:
        logger.warning(f"Signal bias detected: {buys} BUY vs {sells} SELL (last {window})")
```

### Medium Priority

**Review Agent Prompts:**

1. **TechnicalAnalysis Agent** - Check for bearish bias:
   - Ensure RSI logic is symmetric (30 oversold = 70 overbought)
   - Verify MA crossover logic works both directions
   - Add explicit "consider both long and short setups equally"

2. **MarketIntelligence Agent** - Reduce noise:
   - Currently returning generic "slightly positive" sentiment
   - Either improve sentiment analysis or reduce weight from 30% to 20%

3. **Coordinator Agent** - Optimize token usage:
   - Reduce "explain your reasoning" prompt length
   - Use more structured output (JSON) vs prose

### Low Priority

**Data Quality:**
```python
# Add entry price to all signals
signal_data = {
    "instrument": instrument,
    "action": action,
    "confidence": confidence,
    "entry_price": current_price,  # <- Currently missing
    "timestamp": datetime.now().isoformat()
}
```

---

## Testing Plan

### Phase 1: Validate Changes (1 week)
1. Implement max_trades=5
2. Add bias monitoring
3. Run for 1 week in practice mode
4. Compare signal distribution to baseline

**Success Criteria:**
- BUY signals increase to >15% of total
- Skipped trades due to max_trades <30%
- No degradation in confidence scores

### Phase 2: Agent Optimization (1 week)
1. Review and update agent prompts
2. Test with gpt-4o-mini for Coordinator
3. Implement HOLD confidence filter

**Success Criteria:**
- Cost reduction to <$3.50/month
- HOLD signals <25% of total
- High-confidence signals >60%

### Phase 3: Production Ready (ongoing)
1. Implement priority queue for trade management
2. Add real-time bias correction
3. Backtest on historical data

---

## Risk Mitigation

**Changes That Could Go Wrong:**

1. **Increasing max_trades to 5:**
   - Risk: Overexposure, higher drawdown
   - Mitigation: Monitor total portfolio risk, add correlation checks

2. **Filtering HOLD signals:**
   - Risk: Missing genuine neutral opportunities
   - Mitigation: Track "filtered HOLD" count, review if >10/day

3. **Reducing Coordinator tokens:**
   - Risk: Loss of reasoning quality
   - Mitigation: A/B test with current prompt, validate decisions match

---

## Quick Wins (Implement Today)

```bash
# 1. Update config
# In v20.conf or strategy file
max_trades = 5

# 2. Run analysis weekly
uv run python analyze_strategy.py > analysis_$(date +%Y%m%d).txt

# 3. Monitor logs for bias
grep "Agent recommendation: BUY" scalping_strategy.log | wc -l
grep "Agent recommendation: SELL" scalping_strategy.log | wc -l
```

---

## Next Steps

1. ✅ Review this document
2. ⬜ Implement max_trades=5 change
3. ⬜ Add bias monitoring code
4. ⬜ Review TechnicalAnalysis agent prompt
5. ⬜ Run 1-week test with changes
6. ⬜ Analyze results and iterate

---

## Questions to Investigate

1. **Why so few BUY signals?**
   - Is this the market or the strategy?
   - Check if test period coincided with bearish market

2. **Are skipped high-confidence trades costing money?**
   - Track "missed opportunity" metric
   - Calculate theoretical P&L of skipped signals

3. **Is MarketIntelligence adding value?**
   - Currently generic sentiment ("slightly positive")
   - Consider removing or improving data sources

4. **Should we trade during specific hours only?**
   - Analyze signal quality by time of day
   - Forex most active during London/NY overlap (8am-12pm EST)
