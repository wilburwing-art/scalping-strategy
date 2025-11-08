# Phase 2 Implementation Plan: Base Strategy Fixes & Validation
## Ultra-Deep Technical Analysis & Implementation Strategy

**Status**: Ready for implementation
**Estimated Effort**: 25-35 hours
**Priority**: CRITICAL - Required before live trading
**Dependencies**: Phase 1 (Agent system) ✅ COMPLETE

---

## Executive Summary

Phase 1 fixed the agent system (pydantic_ai API, model selection, real data integration). Phase 2 fixes the **base trading strategy** that the agents depend on. Without these fixes, the system will lose money even with perfect agent decisions.

**Core Problem**: The base strategy (`scalping_strategy.py`) has fundamental flaws that make profitable trading impossible:
- Single timeframe data (agents can't do multi-timeframe analysis)
- No transaction costs modeled (blind to 3-4 pips/trade in costs)
- Wrong pip calculations (incorrect position sizing)
- Midpoint pricing (backtest overstates profits by 2-5 pips)
- No leverage limits (risk of account blow-up)
- Backwards RSI logic (buying at wrong times)

---

## Critical Path Analysis

### Dependency Graph

```
Multi-Timeframe Data ──┐
                       ├──> Agent Integration ──> Backtesting ──> Validation
Transaction Costs ─────┘

Bid/Ask Pricing ───────┐
Pip Value Fix ─────────├──> Position Sizing ──> Risk Management
Leverage Limits ───────┘

RSI Logic Fix ─────────> Better Entries ──> Higher Win Rate
Session Filtering ─────> Avoid Bad Hours ──> Lower Costs
```

**Critical Path**: Multi-timeframe → Transaction Costs → Backtesting (20-25 hours)
**Parallel Track**: Pip Value → Bid/Ask → Position Sizing (6-8 hours)
**Quick Wins**: RSI Logic, Leverage Limits (2-3 hours)

---

## Component 1: Multi-Timeframe Data Fetching

### Current State (BROKEN)
```python
# scalping_strategy.py:77
def get_instrument_candles(self, instrument, count=100, granularity="M5"):
    # Only fetches 5-minute candles
    # Agents expect multi-timeframe but only get single timeframe
```

### Problem Analysis
- Agents prompt says "analyze across 1m, 5m, 15m, 1H, 4H timeframes"
- Current code only provides 5m data
- Agents have low confidence when multi-timeframe data missing
- Multi-timeframe alignment is CRITICAL for strong signals

### Solution Architecture

#### Approach 1: Parallel Fetching (RECOMMENDED)
```python
async def get_multi_timeframe_data(self, instrument: str) -> Dict[str, List]:
    """
    Fetch multiple timeframes in parallel for speed.

    Returns:
        {
            "1m": [candles],
            "5m": [candles],
            "15m": [candles],
            "1H": [candles],
            "4H": [candles],
        }
    """
    timeframes = {
        "1m": ("M1", 100),   # Last ~100 minutes
        "5m": ("M5", 100),   # Last ~8 hours
        "15m": ("M15", 100), # Last ~1 day
        "1H": ("H1", 100),   # Last ~4 days
        "4H": ("H4", 100),   # Last ~17 days
    }

    tasks = [
        self._fetch_candles_async(instrument, gran, count)
        for gran, count in timeframes.values()
    ]

    results = await asyncio.gather(*tasks)

    return dict(zip(timeframes.keys(), results))
```

**Rationale**:
- 5 API calls in parallel vs sequential (saves 80% time)
- OANDA API supports async requests
- 100 candles per timeframe provides sufficient history

#### Approach 2: Sequential Fetching (FALLBACK)
If async not possible, fetch sequentially with caching.

**Implementation Complexity**: ⭐⭐ (Medium)
**Estimated Time**: 2-3 hours
**Critical**: ✅ YES - Blocks agent effectiveness

### Validation Tests
- [ ] All 5 timeframes fetched successfully
- [ ] Data aligned properly (timestamps match across timeframes)
- [ ] Handles API failures gracefully (fallback to fewer timeframes)
- [ ] Cache implemented to avoid redundant API calls
- [ ] Performance: <2 seconds for all timeframes

---

## Component 2: Bid/Ask Pricing Model

### Current State (BROKEN)
```python
# scalping_strategy.py:84
price="M"  # ❌ Midpoint pricing
```

### Problem Analysis
**Impact on Backtesting**:
- Midpoint assumes you buy/sell at average of bid/ask
- Reality: Buy at ASK, Sell at BID
- Difference: 2-3 pips for majors, 5-10 pips for exotics
- **This makes backtest show 2-5 pips better performance than reality**

**Example**:
```
EUR/USD:
  Bid: 1.08000
  Ask: 1.08020  (2 pip spread)
  Mid: 1.08010

Current (WRONG):
  Buy at: 1.08010
  Sell at: 1.08010
  Net cost: 0 pips

Reality (CORRECT):
  Buy at: 1.08020 (ask)
  Sell at: 1.08000 (bid)
  Net cost: 2 pips per round trip
```

### Solution Architecture

#### Step 1: Fetch Bid/Ask Data
```python
def get_instrument_candles(self, instrument, count=100, granularity="M5"):
    response = self.ctx.instrument.candles(
        instrument,
        count=count,
        granularity=granularity,
        price="BA"  # ✅ Bid AND Ask prices
    )
    return response.get("candles", [])
```

#### Step 2: Use Correct Price for Execution
```python
def get_execution_price(self, candle, direction: str) -> float:
    """
    Get realistic execution price.

    Args:
        direction: "BUY" or "SELL"

    Returns:
        Ask price for BUY, Bid price for SELL
    """
    if direction == "BUY":
        return float(candle.ask.c)  # Pay the ask
    else:
        return float(candle.bid.c)  # Receive the bid
```

#### Step 3: Calculate Spread Explicitly
```python
def calculate_spread(self, candle) -> float:
    """Calculate spread in pips for cost modeling."""
    bid = float(candle.bid.c)
    ask = float(candle.ask.c)
    spread_pips = (ask - bid) * 10000  # Convert to pips
    return spread_pips
```

**Implementation Complexity**: ⭐ (Easy)
**Estimated Time**: 1-2 hours
**Critical**: ✅ YES - Affects backtest accuracy

### Validation Tests
- [ ] Spread calculated correctly for all pairs
- [ ] Buy uses ask, sell uses bid
- [ ] Backtest results match live execution (within 0.5 pips)

---

## Component 3: Accurate Pip Value Calculation

### Current State (BROKEN)
```python
# scalping_strategy.py:203-214
def _calculate_pip_value(self, instrument, price):
    if instrument.endswith("_USD"):
        return 0.0001  # ❌ OVERSIMPLIFIED
    elif instrument.startswith("USD_"):
        return 0.0001 / price  # ❌ WRONG FOR MANY PAIRS
    else:
        return 0.0001  # ❌ DANGEROUS DEFAULT
```

### Problem Analysis

**Why Current Code is Wrong**:

1. **EUR/USD** (quote currency = USD):
   - Current: `0.0001` ✅ CORRECT
   - Reality: `$10 per pip per 100k units` ✅

2. **USD/JPY** (quote currency = JPY):
   - Current: `0.0001 / price` ❌ WRONG
   - Reality: Pip is `0.01` not `0.0001` (JPY pairs different)
   - Correct formula: `(0.01 / price) * USD/JPY rate`

3. **GBP/JPY** (neither USD):
   - Current: `0.0001` ❌ COMPLETELY WRONG
   - Reality: Need to convert GBP to USD via GBP/USD rate
   - This can be 3x off from correct value

**Impact**: Position sizing can be 50-300% wrong → wrong risk exposure

### Solution Architecture

#### Approach 1: Use OANDA Instrument Details API (RECOMMENDED)
```python
def get_pip_value_accurate(self, instrument: str, units: int = 100000) -> float:
    """
    Get accurate pip value using OANDA's instrument details.

    OANDA provides:
    - pipLocation: decimal place of pip (4 for most, 2 for JPY)
    - displayPrecision: number of decimals

    Args:
        instrument: e.g., "EUR_USD"
        units: position size (default 100k = 1 standard lot)

    Returns:
        Pip value in account currency (USD)
    """
    # Fetch instrument details from OANDA
    instruments = self.get_tradeable_instruments()
    instrument_details = next(
        (i for i in instruments if i.name == instrument),
        None
    )

    if not instrument_details:
        raise ValueError(f"Instrument {instrument} not found")

    # OANDA provides pip location (-4 for most pairs, -2 for JPY)
    pip_location = int(instrument_details.pipLocation)
    pip_size = 10 ** pip_location  # 0.0001 for -4, 0.01 for -2

    # Get current price for conversion
    candles = self.get_instrument_candles(instrument, count=1)
    current_price = float(candles[-1].mid.c)

    # Calculate pip value
    quote_currency = instrument.split("_")[1]

    if quote_currency == "USD":
        # Direct: pip value in USD
        pip_value = pip_size * units
    else:
        # Need conversion rate to USD
        conversion_rate = self._get_conversion_rate(quote_currency, "USD")
        pip_value = pip_size * units * conversion_rate

    return pip_value

def _get_conversion_rate(self, from_currency: str, to_currency: str) -> float:
    """
    Get conversion rate between two currencies.

    Examples:
        JPY -> USD: fetch USD/JPY, return 1/price
        GBP -> USD: fetch GBP/USD, return price
    """
    # Try direct pair
    instrument = f"{from_currency}_{to_currency}"
    try:
        candles = self.get_instrument_candles(instrument, count=1)
        return float(candles[-1].mid.c)
    except:
        pass

    # Try inverse pair
    instrument = f"{to_currency}_{from_currency}"
    try:
        candles = self.get_instrument_candles(instrument, count=1)
        return 1.0 / float(candles[-1].mid.c)
    except:
        pass

    # Fallback: approximate using triangulation via EUR
    # EUR/from * EUR/to = from/to
    logger.warning(f"Using EUR triangulation for {from_currency}/{to_currency}")
    # Implementation left as exercise - query EUR pairs

    return 1.0  # Dangerous fallback
```

#### Approach 2: Hardcoded Table with Formulas (FALLBACK)
If API fails, use lookup table with proper formulas.

**Implementation Complexity**: ⭐⭐⭐ (Medium-Hard)
**Estimated Time**: 3-4 hours
**Critical**: ✅ YES - Affects risk management

### Validation Tests
- [ ] EUR/USD: $10 per pip per 100k units
- [ ] USD/JPY: ~$9.17 per pip (varies with rate)
- [ ] GBP/JPY: Converts correctly via GBP/USD
- [ ] All 28 major pairs tested
- [ ] Matches OANDA position calculator

---

## Component 4: Leverage Limits & Margin Checks

### Current State (MISSING)
```python
# scalping_strategy.py:179-201
def calculate_position_size(self, account_balance, instrument, indicators):
    # No leverage check ❌
    # Could request $500k position on $10k account
    # OANDA allows 50:1, this allows unlimited
```

### Problem Analysis

**Scenario**:
```
Account: $10,000
Risk: 1% = $100
Stop: 20 pips
Pip value: $10 per pip per 100k

Current formula:
  Position = $100 / (20 pips * $10/pip) = 0.5 lots = 50k units
  Notional value = 50k * 1.08 = $54,000
  Leverage = $54k / $10k = 5.4:1 ✅ OK

But if ATR is 5 pips (low volatility):
  Position = $100 / (7.5 pips * $10/pip) = 1.33 lots = 133k units
  Notional value = 133k * 1.08 = $143,640
  Leverage = $143k / $10k = 14.4:1 ⚠️ RISKY

If ATR is 2 pips (ultra low):
  Position = $100 / (3 pips * $10/pip) = 3.33 lots = 333k units
  Notional value = $360,000
  Leverage = 36:1 ❌ DANGEROUS
```

**Result**: Low volatility → massive position sizes → over-leveraging

### Solution Architecture

```python
def calculate_position_size_safe(
    self,
    account_balance: float,
    instrument: str,
    stop_loss_pips: float,
    max_leverage: float = 10.0,  # Conservative limit
    risk_percent: float = 1.0,
) -> int:
    """
    Calculate position size with leverage safety checks.

    Args:
        max_leverage: Maximum leverage allowed (default 10:1)
                      OANDA allows 50:1, we enforce 10:1 for safety

    Returns:
        Position size in units (capped by leverage limit)
    """
    # Step 1: Calculate risk-based position size
    risk_amount = account_balance * (risk_percent / 100)
    pip_value = self.get_pip_value_accurate(instrument)

    # Add buffer for spread and slippage
    effective_stop_pips = stop_loss_pips + 2  # +2 pips for costs

    position_size = risk_amount / (effective_stop_pips * pip_value)

    # Step 2: Calculate leverage for this position
    current_price = self.get_current_price(instrument)
    notional_value = position_size * current_price
    leverage = notional_value / account_balance

    # Step 3: Cap by leverage limit
    if leverage > max_leverage:
        logger.warning(
            f"Position size {position_size} exceeds leverage limit "
            f"({leverage:.1f}:1 > {max_leverage}:1). Reducing position."
        )
        max_notional = account_balance * max_leverage
        position_size = max_notional / current_price

    # Step 4: Check OANDA margin requirements
    margin_required = self._calculate_margin_required(
        instrument,
        position_size,
        current_price
    )

    if margin_required > account_balance * 0.5:  # Use max 50% for margin
        logger.warning(
            f"Margin required (${margin_required:.2f}) > 50% of account. "
            f"Reducing position."
        )
        position_size *= (account_balance * 0.5) / margin_required

    # Step 5: Round to valid precision
    return self._round_units(instrument, position_size)

def _calculate_margin_required(
    self,
    instrument: str,
    units: float,
    price: float
) -> float:
    """
    Calculate margin required for position.

    OANDA margin formula:
        Margin = (Units × Price) / Leverage

    Leverage varies by instrument and account type:
        - Major pairs: 50:1 (2% margin)
        - Minor pairs: 20:1 (5% margin)
        - Exotics: 10:1 (10% margin)
    """
    # Get instrument-specific leverage from OANDA
    instruments = self.get_tradeable_instruments()
    instrument_obj = next(
        (i for i in instruments if i.name == instrument),
        None
    )

    if instrument_obj and hasattr(instrument_obj, 'marginRate'):
        margin_rate = float(instrument_obj.marginRate)
    else:
        # Conservative default: 5% margin (20:1 leverage)
        margin_rate = 0.05

    notional_value = abs(units) * price
    margin_required = notional_value * margin_rate

    return margin_required
```

**Implementation Complexity**: ⭐⭐ (Medium)
**Estimated Time**: 2 hours
**Critical**: ✅ YES - Risk management

### Validation Tests
- [ ] EUR/USD position capped at 10:1 leverage
- [ ] Low volatility doesn't create massive positions
- [ ] Margin requirements respected
- [ ] Warning logs when leverage limit hit
- [ ] No positions opened if margin > 50% of account

---

## Component 5: Transaction Cost Modeling

### Current State (MISSING)
No spread, slippage, or swap costs modeled anywhere.

### Problem Analysis

**Real Trading Costs**:

| Cost Type | EUR/USD | USD/JPY | GBP/JPY | Notes |
|-----------|---------|---------|---------|-------|
| Spread | 1-2 pips | 1-2 pips | 3-5 pips | Higher in Asian session |
| Slippage | 0.5-1 pips | 0.5-2 pips | 1-3 pips | Worse during news |
| Swap/Rollover | 0-0.5 pips/day | 0-0.5 pips/day | 0-1 pip/day | Holding overnight |
| **Total per trade** | **2-3.5 pips** | **2-4.5 pips** | **4-9 pips** | Round trip |

**Impact on Scalping**:
```
Strategy targeting +5 pips per trade:
  Gross: +5 pips
  Costs: -3 pips
  Net: +2 pips (60% of profit lost to costs!)

Win rate needed:
  Without costs: 50% (breakeven at 1:1 R/R)
  With costs: 65-70% (breakeven accounting for costs)

Conclusion: Scalping is VERY difficult for retail
```

### Solution Architecture

#### Cost Model Implementation
```python
@dataclass
class TransactionCosts:
    """Comprehensive transaction cost model"""
    spread_pips: float
    slippage_pips: float
    swap_pips_per_day: float
    total_entry_cost_pips: float
    total_exit_cost_pips: float

    @property
    def total_round_trip_pips(self) -> float:
        """Total cost for entry + exit"""
        return self.total_entry_cost_pips + self.total_exit_cost_pips

class CostCalculator:
    """Calculate realistic transaction costs"""

    def calculate_costs(
        self,
        instrument: str,
        candle,
        session: str,  # "asian", "london", "ny"
        is_news_event: bool = False,
        holding_days: float = 0.0,
    ) -> TransactionCosts:
        """
        Calculate expected transaction costs.

        Args:
            session: Trading session (spreads wider in Asian)
            is_news_event: High slippage during news
            holding_days: For swap calculation
        """
        # Base spread from candle
        bid = float(candle.bid.c)
        ask = float(candle.ask.c)
        spread_pips = (ask - bid) * 10000

        # Session multiplier
        session_multipliers = {
            "asian": 1.5,    # Wider spreads
            "london": 1.0,   # Normal
            "ny": 1.0,       # Normal
            "overlap": 0.9,  # Tightest spreads (London+NY)
        }
        spread_pips *= session_multipliers.get(session, 1.0)

        # Slippage estimation
        if is_news_event:
            slippage_pips = spread_pips * 2.0  # 2x spread during news
        else:
            slippage_pips = max(0.5, spread_pips * 0.3)  # 30% of spread

        # Swap/rollover (approximate)
        swap_pips_per_day = self._get_swap_rate(instrument)
        total_swap = swap_pips_per_day * holding_days

        # Total costs
        entry_cost = spread_pips + slippage_pips
        exit_cost = spread_pips + slippage_pips

        return TransactionCosts(
            spread_pips=spread_pips,
            slippage_pips=slippage_pips,
            swap_pips_per_day=swap_pips_per_day,
            total_entry_cost_pips=entry_cost,
            total_exit_cost_pips=exit_cost + total_swap,
        )

    def _get_swap_rate(self, instrument: str) -> float:
        """
        Get swap rate for instrument.

        In production: query OANDA financing API
        For now: use approximations
        """
        # Major pairs: low swap
        if instrument in ["EUR_USD", "GBP_USD", "USD_JPY"]:
            return 0.2  # ~0.2 pips per day
        # Exotics: higher swap
        else:
            return 0.5  # ~0.5 pips per day
```

#### Integration with Position Sizing
```python
def calculate_position_size_with_costs(
    self,
    account_balance: float,
    instrument: str,
    stop_loss_pips: float,
    costs: TransactionCosts,
) -> int:
    """
    Calculate position size accounting for transaction costs.

    Effective stop = Intended stop + Entry costs + Exit costs
    """
    # Add costs to effective stop
    effective_stop_pips = (
        stop_loss_pips +
        costs.total_entry_cost_pips +
        costs.total_exit_cost_pips
    )

    # Use effective stop for position sizing
    risk_amount = account_balance * (self.risk_percent / 100)
    pip_value = self.get_pip_value_accurate(instrument)
    position_size = risk_amount / (effective_stop_pips * pip_value)

    return self._round_units(instrument, position_size)
```

**Implementation Complexity**: ⭐⭐⭐ (Medium-Hard)
**Estimated Time**: 3-4 hours
**Critical**: ✅ YES - Profitability validation

### Validation Tests
- [ ] Spread calculated from bid/ask correctly
- [ ] Session multipliers applied
- [ ] Slippage increases during news events
- [ ] Swap calculated for overnight holds
- [ ] Position sizing reflects total costs
- [ ] Backtest P/L matches live trading (within 10%)

---

## Component 6: Fix RSI Logic

### Current State (BROKEN)
```python
# scalping_strategy.py:175
has_momentum = (
    indicators["rsi"] < self.rsi_overbought if has_trend
    else indicators["rsi"] > self.rsi_oversold
)
```

### Problem Analysis

**Current Logic** (WRONG):
```
If uptrend (MA short > MA long):
    Buy if RSI < 70

Problem: This buys at RSI 30, 40, 50, 60, 69 (all accepted)
         RSI 50-69 is NOT oversold - these are weak entries
```

**Correct Logic**:
```
If uptrend (MA short > MA long):
    Buy on PULLBACK: RSI 30-40 (oversold in uptrend)
    Avoid: RSI > 50 (already extended)

If downtrend (MA short < MA long):
    Sell on BOUNCE: RSI 60-70 (overbought in downtrend)
    Avoid: RSI < 50 (already oversold)
```

### Solution

```python
def is_instrument_tradeable(self, instrument_data, indicators):
    """
    Fixed RSI logic: Buy pullbacks in uptrends, sell bounces in downtrends.
    """
    if not indicators:
        return False

    # Volume and volatility checks (unchanged)
    if indicators["recent_volume"] < self.volume_threshold:
        return False
    if indicators["atr"] < self.volatility_min:
        return False

    rsi = indicators["rsi"]

    # Trend determination
    is_uptrend = indicators["ma_short"] > indicators["ma_long"]
    is_downtrend = indicators["ma_short"] < indicators["ma_long"]

    # ✅ FIXED RSI LOGIC
    if is_uptrend:
        # Buy pullbacks in uptrend (RSI oversold)
        return self.rsi_oversold <= rsi <= self.rsi_oversold + 15  # 30-45

    elif is_downtrend:
        # Sell bounces in downtrend (RSI overbought)
        return self.rsi_overbought - 15 <= rsi <= self.rsi_overbought  # 55-70

    else:
        # No clear trend - don't trade
        return False
```

**Implementation Complexity**: ⭐ (Easy)
**Estimated Time**: 30 minutes
**Critical**: ⚠️ MEDIUM - Improves win rate

### Validation Tests
- [ ] Uptrend: only signals when RSI 30-45
- [ ] Downtrend: only signals when RSI 55-70
- [ ] No signals in ranging market (MA's flat)
- [ ] Backtest: Win rate improves by 5-10%

---

## Component 7: Backtesting Framework

### Architecture Overview

```
BacktestEngine
├── HistoricalDataProvider
│   ├── Fetch multi-timeframe data from OANDA
│   └── Cache locally to avoid API limits
├── SimulatedBroker
│   ├── Execute trades at bid/ask (not mid)
│   ├── Apply transaction costs
│   ├── Track positions and P/L
│   └── Handle margin calls
├── PerformanceAnalyzer
│   ├── Calculate Sharpe ratio
│   ├── Calculate max drawdown
│   ├── Win rate, profit factor
│   └── Generate equity curve
└── ParameterOptimizer
    ├── Grid search over parameters
    ├── Walk-forward validation
    └── Out-of-sample testing
```

### Implementation Plan

#### Phase 7.1: Historical Data Provider
```python
class HistoricalDataProvider:
    """
    Fetch and cache historical OANDA data.
    """

    def __init__(self, ctx, cache_dir="./data/historical"):
        self.ctx = ctx
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_historical_range(
        self,
        instrument: str,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "M5",
    ) -> pd.DataFrame:
        """
        Fetch historical candles for date range.

        OANDA limits: 5000 candles per request
        Strategy: Chunk into multiple requests
        """
        cache_file = self._get_cache_path(
            instrument, start_date, end_date, granularity
        )

        # Check cache first
        if os.path.exists(cache_file):
            logger.info(f"Loading cached data from {cache_file}")
            return pd.read_parquet(cache_file)

        # Fetch from API
        all_candles = []
        current_start = start_date

        while current_start < end_date:
            # Fetch chunk (max 5000 candles)
            response = self.ctx.instrument.candles(
                instrument,
                fromTime=current_start.isoformat() + "Z",
                toTime=min(current_start + timedelta(days=7), end_date).isoformat() + "Z",
                granularity=granularity,
                price="BA",  # Bid and Ask
            )

            candles = response.get("candles", [])
            all_candles.extend(candles)

            if not candles:
                break

            # Move to next chunk
            last_time = parse(candles[-1].time)
            current_start = last_time + timedelta(seconds=1)

            # Rate limiting
            time.sleep(0.1)

        # Convert to DataFrame
        df = self._candles_to_dataframe(all_candles)

        # Cache for future use
        df.to_parquet(cache_file)
        logger.info(f"Cached {len(df)} candles to {cache_file}")

        return df
```

#### Phase 7.2: Simulated Broker
```python
class SimulatedBroker:
    """
    Simulate trade execution with realistic costs.
    """

    def __init__(
        self,
        initial_balance: float,
        cost_calculator: CostCalculator,
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions = []
        self.closed_trades = []
        self.cost_calculator = cost_calculator

    def execute_market_order(
        self,
        instrument: str,
        units: int,
        current_candle,
        stop_loss: float,
        take_profit: float,
        timestamp: datetime,
    ) -> Optional[int]:
        """
        Execute trade at realistic prices.

        Returns:
            trade_id if successful, None if rejected
        """
        direction = "BUY" if units > 0 else "SELL"

        # Get execution price (ask for buy, bid for sell)
        if direction == "BUY":
            execution_price = float(current_candle.ask.c)
        else:
            execution_price = float(current_candle.bid.c)

        # Calculate costs
        costs = self.cost_calculator.calculate_costs(
            instrument,
            current_candle,
            session=self._get_session(timestamp),
        )

        # Check margin
        margin_required = self._calculate_margin(instrument, units, execution_price)
        if margin_required > self.balance * 0.5:
            logger.warning(f"Insufficient margin: ${margin_required:.2f} > ${self.balance * 0.5:.2f}")
            return None

        # Create position
        trade_id = len(self.closed_trades) + len(self.positions) + 1
        position = {
            "id": trade_id,
            "instrument": instrument,
            "units": units,
            "entry_price": execution_price,
            "entry_time": timestamp,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_costs_pips": costs.total_entry_cost_pips,
            "status": "open",
        }

        self.positions.append(position)
        logger.info(f"[BACKTEST] Opened {direction} {abs(units)} {instrument} @ {execution_price}")

        return trade_id

    def update_positions(self, current_candle, timestamp: datetime):
        """
        Update position P/L and check for stop/target hits.
        """
        for position in self.positions[:]:  # Copy to allow removal
            # Get current prices
            current_bid = float(current_candle.bid.c)
            current_ask = float(current_candle.ask.c)

            # Check stop loss
            if position["units"] > 0:  # Long position
                if current_bid <= position["stop_loss"]:
                    self._close_position(position, position["stop_loss"], "STOP_LOSS", timestamp)
                    continue
                if current_bid >= position["take_profit"]:
                    self._close_position(position, position["take_profit"], "TAKE_PROFIT", timestamp)
                    continue
            else:  # Short position
                if current_ask >= position["stop_loss"]:
                    self._close_position(position, position["stop_loss"], "STOP_LOSS", timestamp)
                    continue
                if current_ask <= position["take_profit"]:
                    self._close_position(position, position["take_profit"], "TAKE_PROFIT", timestamp)
                    continue

            # Update unrealized P/L
            if position["units"] > 0:
                current_price = current_bid  # Exit at bid
            else:
                current_price = current_ask  # Exit at ask

            pip_diff = (current_price - position["entry_price"]) * 10000
            if position["units"] < 0:
                pip_diff *= -1  # Invert for short

            position["unrealized_pips"] = pip_diff

    def _close_position(self, position, exit_price: float, reason: str, timestamp: datetime):
        """Close position and calculate final P/L"""
        # Calculate exit costs
        exit_candle = ...  # Get current candle
        costs = self.cost_calculator.calculate_costs(...)

        # Calculate P/L in pips
        pip_diff = (exit_price - position["entry_price"]) * 10000
        if position["units"] < 0:
            pip_diff *= -1

        # Subtract costs
        net_pips = pip_diff - position["entry_costs_pips"] - costs.total_exit_cost_pips

        # Convert to dollars
        pip_value = self._get_pip_value(position["instrument"])
        profit_usd = net_pips * pip_value * (abs(position["units"]) / 100000)

        # Update balance
        self.balance += profit_usd

        # Record trade
        closed_trade = {
            **position,
            "exit_price": exit_price,
            "exit_time": timestamp,
            "exit_reason": reason,
            "gross_pips": pip_diff,
            "costs_pips": position["entry_costs_pips"] + costs.total_exit_cost_pips,
            "net_pips": net_pips,
            "profit_usd": profit_usd,
        }

        self.closed_trades.append(closed_trade)
        self.positions.remove(position)

        logger.info(
            f"[BACKTEST] Closed {position['instrument']} @ {exit_price} "
            f"({reason}): {net_pips:+.1f} pips, ${profit_usd:+.2f}"
        )
```

#### Phase 7.3: Performance Metrics
```python
class PerformanceAnalyzer:
    """Calculate comprehensive performance metrics"""

    def analyze(self, trades: List[Dict], initial_balance: float) -> Dict:
        """
        Calculate all performance metrics.

        Returns:
            {
                "total_return": float,
                "sharpe_ratio": float,
                "max_drawdown": float,
                "win_rate": float,
                "profit_factor": float,
                "avg_win": float,
                "avg_loss": float,
                ...
            }
        """
        df = pd.DataFrame(trades)

        # Basic stats
        total_trades = len(df)
        winners = df[df["net_pips"] > 0]
        losers = df[df["net_pips"] < 0]

        win_rate = len(winners) / total_trades if total_trades > 0 else 0

        # P/L stats
        total_profit = df["profit_usd"].sum()
        total_return_pct = (total_profit / initial_balance) * 100

        avg_win_pips = winners["net_pips"].mean() if len(winners) > 0 else 0
        avg_loss_pips = losers["net_pips"].mean() if len(losers) > 0 else 0

        # Profit factor
        gross_profit = winners["profit_usd"].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers["profit_usd"].sum()) if len(losers) > 0 else 0.01
        profit_factor = gross_profit / gross_loss

        # Sharpe ratio (annualized)
        returns = df["profit_usd"] / initial_balance
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        # Max drawdown
        equity_curve = initial_balance + df["profit_usd"].cumsum()
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown_pct = drawdown.min() * 100

        # Cost analysis
        total_costs = df["costs_pips"].sum()
        avg_cost_per_trade = total_costs / total_trades

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_return_usd": total_profit,
            "total_return_pct": total_return_pct,
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": max_drawdown_pct,
            "profit_factor": profit_factor,
            "avg_win_pips": avg_win_pips,
            "avg_loss_pips": avg_loss_pips,
            "avg_cost_per_trade_pips": avg_cost_per_trade,
            "total_costs_pips": total_costs,
        }
```

**Implementation Complexity**: ⭐⭐⭐⭐⭐ (Very Hard)
**Estimated Time**: 12-15 hours
**Critical**: ✅ YES - Can't validate without this

---

## Component 8: Session Filtering

### Problem
Trading EUR/USD during Asian session = low volume + wide spreads + poor execution

### Solution
```python
def get_trading_session(self, timestamp: datetime) -> str:
    """
    Determine trading session based on UTC time.

    Sessions (UTC):
        Tokyo: 00:00 - 09:00
        London: 08:00 - 17:00
        New York: 13:00 - 22:00
        Overlap (best): 13:00 - 17:00
    """
    hour_utc = timestamp.hour

    if 0 <= hour_utc < 8:
        return "asian"
    elif 8 <= hour_utc < 13:
        return "london"
    elif 13 <= hour_utc < 17:
        return "overlap"  # Best liquidity
    elif 17 <= hour_utc < 22:
        return "ny"
    else:
        return "asian"

def should_trade_instrument(self, instrument: str, session: str) -> bool:
    """
    Check if instrument should be traded in current session.
    """
    # EUR/USD, GBP/USD: Trade during London/NY, avoid Asian
    if instrument in ["EUR_USD", "GBP_USD", "EUR_GBP"]:
        return session in ["london", "ny", "overlap"]

    # USD/JPY, AUD/JPY: OK during Asian
    if "JPY" in instrument:
        return session in ["asian", "overlap", "ny"]

    # Default: trade during high liquidity
    return session in ["london", "ny", "overlap"]
```

**Estimated Time**: 1-2 hours
**Critical**: ⚠️ MEDIUM - Reduces costs

---

## Component 9: Correlation Risk Checks

### Solution
```python
class CorrelationManager:
    """Manage correlation risk across portfolio"""

    # Known correlations (approximate)
    CORRELATIONS = {
        ("EUR_USD", "GBP_USD"): 0.75,
        ("EUR_USD", "USD_CHF"): -0.85,
        ("EUR_USD", "AUD_USD"): 0.65,
        ("GBP_USD", "EUR_GBP"): -0.70,
    }

    def check_correlation_risk(
        self,
        new_instrument: str,
        active_positions: List[Dict],
        max_correlation: float = 0.7,
    ) -> tuple[bool, List[str]]:
        """
        Check if new position would create correlation risk.

        Returns:
            (should_trade, warnings)
        """
        warnings = []

        for position in active_positions:
            existing_instrument = position["instrument"]

            # Check correlation
            corr = self._get_correlation(new_instrument, existing_instrument)

            if abs(corr) > max_correlation:
                warnings.append(
                    f"High correlation ({corr:.2f}) with existing "
                    f"{existing_instrument} position"
                )

        should_trade = len(warnings) == 0
        return should_trade, warnings
```

**Estimated Time**: 2 hours
**Critical**: ⚠️ MEDIUM - Portfolio risk

---

## Integration Plan: Putting It All Together

### New Enhanced Strategy Architecture

```python
class EnhancedScalpingStrategy:
    """
    Production-ready trading strategy with all Phase 2 fixes.

    Features:
    - Multi-timeframe analysis
    - Transaction cost modeling
    - Accurate pip values
    - Leverage limits
    - Session filtering
    - Correlation checks
    - Backtesting support
    - AI agent integration
    """

    def __init__(self, config_file, environment="practice"):
        # Core components
        self.base_strategy = ScalpingStrategyFixed(config_file, environment)
        self.cost_calculator = CostCalculator()
        self.correlation_manager = CorrelationManager()

        # AI agents (from Phase 1)
        self.trading_agents = TradingIntelligenceSystem(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            alpha_vantage_key=os.getenv("ALPHA_VANTAGE_API_KEY"),
        )

    async def analyze_opportunity(self, instrument: str) -> Optional[TradingRecommendation]:
        """
        Complete analysis pipeline with all fixes.
        """
        # 1. Multi-timeframe data
        mtf_data = await self.base_strategy.get_multi_timeframe_data(instrument)

        # 2. Session check
        session = self.base_strategy.get_trading_session(datetime.now())
        if not self.base_strategy.should_trade_instrument(instrument, session):
            return None

        # 3. Calculate indicators on all timeframes
        indicators = {}
        for tf, candles in mtf_data.items():
            indicators[tf] = self.base_strategy.calculate_indicators(candles)

        # 4. Transaction costs
        costs = self.cost_calculator.calculate_costs(
            instrument,
            mtf_data["5m"][-1],
            session=session,
        )

        # 5. AI agent analysis
        recommendation = await self.trading_agents.analyze_opportunity(
            instrument=instrument,
            account_balance=self.base_strategy.get_account_balance(),
            active_positions=self.base_strategy.get_active_positions(),
            price_data={"timeframes": mtf_data},
            technical_indicators=indicators,
        )

        # 6. Correlation check
        if recommendation.action in [SignalStrength.BUY, SignalStrength.STRONG_BUY]:
            should_trade, warnings = self.correlation_manager.check_correlation_risk(
                instrument,
                self.base_strategy.get_active_positions()
            )
            if not should_trade:
                logger.warning(f"Skipping {instrument} due to correlation: {warnings}")
                return None

        # 7. Adjust position size for costs + leverage limits
        if recommendation.position_size:
            recommendation.position_size = self.base_strategy.calculate_position_size_safe(
                account_balance=self.base_strategy.get_account_balance(),
                instrument=instrument,
                stop_loss_pips=...,
                costs=costs,
            )

        return recommendation
```

---

## Testing Strategy

### Unit Tests
- [ ] Multi-timeframe fetching works for all pairs
- [ ] Pip value calculations match OANDA calculator
- [ ] Cost modeling accurate within 0.5 pips
- [ ] Leverage limits enforced correctly
- [ ] Session detection works for all timezones

### Integration Tests
- [ ] Full pipeline: data → agents → execution
- [ ] Backtest runs on 2 years data without errors
- [ ] Performance metrics calculated correctly
- [ ] Agent + base strategy integration works

### Validation Tests
- [ ] Backtest EUR/USD 2023-2024: Sharpe > 1.0, DD < 20%
- [ ] Paper trade 30 days: Results match backtest (±20%)
- [ ] Live costs match modeled costs (±10%)

---

## Risk Assessment

### What Could Go Wrong

1. **API Rate Limits**
   - Risk: OANDA limits multi-timeframe fetching
   - Mitigation: Cache aggressively, batch requests

2. **Backtest Overfitting**
   - Risk: Parameters optimized for past data
   - Mitigation: Walk-forward validation, out-of-sample testing

3. **Slippage Underestimated**
   - Risk: Real slippage > modeled slippage
   - Mitigation: Conservative estimates, monitor live vs model

4. **Agent Costs Too High**
   - Risk: $50-100/day in OpenAI API costs
   - Mitigation: Use gpt-4o-mini where possible, cache agent decisions

---

## Success Criteria

### Phase 2 Complete When:
- [ ] All 12 components implemented and tested
- [ ] Backtest shows profitability on 2 years EUR/USD data
- [ ] Sharpe ratio > 1.0
- [ ] Max drawdown < 20%
- [ ] Win rate > 50%
- [ ] Costs accurately modeled (within 10% of live)
- [ ] Multi-timeframe data integrated with agents
- [ ] No leverage violations in backtest
- [ ] Paper trading for 30 days validates backtest

### Ready for Live Trading When:
- [ ] 90 days paper trading successful
- [ ] Paper P/L matches backtest (±20%)
- [ ] All costs match predictions (±15%)
- [ ] No system failures or crashes
- [ ] Risk management proven effective
- [ ] Agent decisions validated by performance

---

## Estimated Timeline

### Week 1: Core Fixes (Critical Path)
- Day 1-2: Multi-timeframe data fetching (3h) + Bid/ask pricing (2h) = **5 hours**
- Day 3: Pip value calculation (4h) = **4 hours**
- Day 4: Leverage limits (2h) + RSI fix (1h) + Session filtering (2h) = **5 hours**
- Day 5: Transaction cost model (4h) = **4 hours**

**Week 1 Total**: 18 hours

### Week 2: Backtesting
- Day 6-7: Historical data provider (4h) = **4 hours**
- Day 8-10: Simulated broker (6h) = **6 hours**
- Day 11-12: Performance analyzer (3h) = **3 hours**

**Week 2 Total**: 13 hours

### Week 3: Integration & Testing
- Day 13-14: Integration layer (4h) = **4 hours**
- Day 15: Unit tests (3h) = **3 hours**
- Day 16-17: Run backtests, fix bugs (6h) = **6 hours**
- Day 18: Documentation (2h) = **2 hours**

**Week 3 Total**: 15 hours

### Week 4: Validation
- Paper trading (30+ days, monitor daily)
- Performance comparison
- Cost validation
- System hardening

**Total Effort**: 46 hours coding + 30 days validation

---

## Next Steps

1. ✅ Review this plan
2. ⏭️ Implement Component 1 (Multi-timeframe)
3. ⏭️ Implement Component 2 (Bid/ask pricing)
4. ⏭️ Continue sequentially through critical path
5. ⏭️ Run first backtest after Week 2
6. ⏭️ Paper trade after Week 3
7. ⏭️ Consider live trading after 90 days paper success

---

## Questions to Resolve

Before starting implementation:

1. **Backtesting Data Source**: Use OANDA historical or buy premium data?
2. **Agent Model Costs**: Budget $50-100/day for OpenAI API during development?
3. **Alpha Vantage API**: Free tier sufficient or need premium?
4. **Target Timeframe**: Still scalping (5m) or shift to swing (4H)?
5. **Risk Tolerance**: Stick with 1% per trade or adjust?

---

**This plan is comprehensive, prioritized, and ready for execution.**
