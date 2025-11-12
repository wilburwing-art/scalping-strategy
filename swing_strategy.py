"""
Swing Trading Strategy with AI Agents & Phase 3 Features

This strategy trades on 4H timeframes (swing trading) instead of 5m (scalping).

Key Differences from Scalping:
- Timeframe: 4H instead of 5m (longer holds)
- Target: 30-50 pips instead of 5-10 pips
- Lower transaction cost impact (costs = 5% vs 60%)
- Better for retail traders
- AI agents and Phase 3 features enabled

Usage:
    # Backtest with real OANDA data
    uv run python swing_strategy.py --backtest --months 12

    # Paper trade (practice account)
    uv run python swing_strategy.py --paper-trade

    # Live trade (after validation)
    uv run python swing_strategy.py --live
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
from v20 import Context
import configparser
import os

# Phase 2 & 3 components
from transaction_costs import CostCalculator
from pip_calculator import PipCalculator
from risk_management import RiskManager

# Try to import Phase 3 features
try:
    from economic_calendar import EconomicCalendar
    CALENDAR_AVAILABLE = True
except:
    CALENDAR_AVAILABLE = False

try:
    from sentiment_analyzer import SentimentAnalyzer
    SENTIMENT_AVAILABLE = True
except:
    SENTIMENT_AVAILABLE = False

try:
    from trade_journal import TradeJournal, TradeJournalEntry
    JOURNAL_AVAILABLE = True
except:
    JOURNAL_AVAILABLE = False

try:
    from alert_manager import AlertManager, AlertConfig, AlertPriority
    from system_monitor import SystemMonitor
    MONITORING_AVAILABLE = True
except:
    MONITORING_AVAILABLE = False

# AI agents
try:
    from trading_agents_fixed import get_trading_signal
    AGENTS_AVAILABLE = True
except:
    AGENTS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class SwingTradingStrategy:
    """
    Swing Trading Strategy (4H timeframe)

    Features:
    - Trades 4H candles (longer-term moves)
    - Targets 30-50 pips (vs 5-10 for scalping)
    - Lower cost impact (~5% vs 60%)
    - AI agents enabled
    - Economic calendar filtering
    - Social sentiment analysis
    - Trade journaling
    - System monitoring
    """

    def __init__(
        self,
        config_file: str = "v20.conf",
        environment: str = "practice",
        enable_agents: bool = True,
        enable_calendar: bool = True,
        enable_sentiment: bool = True,
        enable_monitoring: bool = True,
    ):
        self.config_file = config_file
        self.environment = environment

        # Load config
        self.config = self._load_config()

        # Initialize OANDA API
        self.api = Context(
            hostname=self.config["hostname"],
            token=self.config["token"],
            port=443
        )
        self.account_id = self.config["account_id"]

        # Swing trading parameters
        self.instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]
        self.timeframe = "H4"  # 4-hour candles
        self.scan_interval = 3600  # Check every hour

        # RSI parameters (more relaxed for swing trading)
        self.rsi_period = 14
        self.rsi_oversold = 35  # Less extreme (was 30)
        self.rsi_overbought = 65  # Less extreme (was 70)

        # Moving averages (longer periods for swing)
        self.ma_short_period = 20  # Was 10
        self.ma_long_period = 50   # Was 20

        # Risk parameters (swing trading)
        self.risk_percent = 1.0
        self.reward_risk_ratio = 2.0  # Higher R:R (was 1.5)
        self.max_positions = 2  # Fewer concurrent trades

        # Stop loss (wider for swing)
        self.atr_multiplier = 2.0  # Was 1.5

        # Initialize modules
        self.cost_calculator = CostCalculator()
        self.pip_calculator = PipCalculator()
        self.risk_manager = RiskManager(
            max_leverage=10.0,  # Lower leverage for swing
            max_risk_per_trade=self.risk_percent,
            max_total_exposure_ratio=2.0,
        )

        # Initialize Phase 3 components
        self.enable_agents = enable_agents and AGENTS_AVAILABLE
        self.enable_calendar = enable_calendar and CALENDAR_AVAILABLE
        self.enable_sentiment = enable_sentiment and SENTIMENT_AVAILABLE

        self._init_phase3_components(enable_monitoring)

        self._log_initialization()

    def _load_config(self) -> Dict:
        """Load OANDA configuration"""
        if not os.path.isfile(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        parser = configparser.ConfigParser()
        parser.read(self.config_file)

        return {
            "hostname": parser[self.environment]["hostname"],
            "token": parser[self.environment]["token"],
            "account_id": parser[self.environment]["account_id"],
        }

    def _init_phase3_components(self, enable_monitoring):
        """Initialize Phase 3 features"""
        # Economic calendar
        if self.enable_calendar:
            api_key = os.getenv("TRADING_ECONOMICS_API_KEY")
            if api_key:
                try:
                    self.economic_calendar = EconomicCalendar(api_key=api_key)
                    logger.info("✅ Economic calendar enabled")
                except Exception as e:
                    logger.warning(f"Economic calendar failed: {e}")
                    self.economic_calendar = None
            else:
                logger.warning("TRADING_ECONOMICS_API_KEY not set")
                self.economic_calendar = None
        else:
            self.economic_calendar = None

        # Sentiment analyzer
        if self.enable_sentiment:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                try:
                    self.sentiment_analyzer = SentimentAnalyzer(
                        openai_key=openai_key,
                        twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
                        reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
                        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                    )
                    logger.info("✅ Sentiment analysis enabled")
                except Exception as e:
                    logger.warning(f"Sentiment analysis failed: {e}")
                    self.sentiment_analyzer = None
            else:
                logger.warning("OPENAI_API_KEY not set")
                self.sentiment_analyzer = None
        else:
            self.sentiment_analyzer = None

        # Trade journal
        if JOURNAL_AVAILABLE:
            try:
                journal_path = f"swing_trades_{self.environment}.db"
                self.trade_journal = TradeJournal(journal_path)
                logger.info(f"✅ Trade journal: {journal_path}")
            except Exception as e:
                logger.warning(f"Trade journal failed: {e}")
                self.trade_journal = None
        else:
            self.trade_journal = None

        # Monitoring and alerts
        if enable_monitoring and MONITORING_AVAILABLE:
            email_enabled = bool(os.getenv("ALERT_EMAIL") and os.getenv("ALERT_EMAIL_PASSWORD"))

            config = AlertConfig(
                email_enabled=email_enabled,
                smtp_username=os.getenv("ALERT_EMAIL", ""),
                smtp_password=os.getenv("ALERT_EMAIL_PASSWORD", ""),
                from_email=os.getenv("ALERT_EMAIL", ""),
                to_emails=[os.getenv("ALERT_EMAIL", "noreply@example.com")],
                min_priority_email=AlertPriority.WARNING,
            )

            try:
                self.alert_manager = AlertManager(config)
                self.system_monitor = SystemMonitor(
                    alert_manager=self.alert_manager,
                    trade_journal=self.trade_journal,
                    health_check_interval_minutes=5,
                )
                logger.info("✅ Monitoring enabled")
            except Exception as e:
                logger.warning(f"Monitoring failed: {e}")
                self.alert_manager = None
                self.system_monitor = None
        else:
            self.alert_manager = None
            self.system_monitor = None

    def _log_initialization(self):
        """Log initialization status"""
        logger.info("\n" + "="*70)
        logger.info("SWING TRADING STRATEGY INITIALIZED")
        logger.info("="*70)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Timeframe: {self.timeframe} (4-hour candles)")
        logger.info(f"Target: 30-50 pips (vs 5-10 for scalping)")
        logger.info(f"RSI Thresholds: {self.rsi_oversold}/{self.rsi_overbought}")
        logger.info(f"MA Periods: {self.ma_short_period}/{self.ma_long_period}")
        logger.info(f"R:R Ratio: {self.reward_risk_ratio}:1")
        logger.info(f"Max Positions: {self.max_positions}")
        logger.info("")
        logger.info("Phase 3 Features:")
        logger.info(f"  AI Agents: {'✅' if self.enable_agents else '❌'}")
        logger.info(f"  Economic Calendar: {'✅' if self.economic_calendar else '❌'}")
        logger.info(f"  Sentiment Analysis: {'✅' if self.sentiment_analyzer else '❌'}")
        logger.info(f"  Trade Journaling: {'✅' if self.trade_journal else '❌'}")
        logger.info(f"  System Monitoring: {'✅' if self.system_monitor else '❌'}")
        logger.info("="*70 + "\n")

    def get_candles(self, instrument: str, count: int = 100) -> List:
        """Fetch 4H candles from OANDA"""
        try:
            response = self.api.instrument.candles(
                instrument,
                count=count,
                granularity=self.timeframe,
                price="M"  # Midpoint
            )
            return response.body.get("candles", [])
        except Exception as e:
            logger.error(f"Error fetching candles for {instrument}: {e}")
            return []

    def calculate_indicators(self, candles: List) -> Optional[Dict]:
        """Calculate swing trading indicators"""
        if not candles or len(candles) < self.ma_long_period:
            return None

        # Extract prices
        close_prices = [float(c.mid.c) for c in candles]
        high_prices = [float(c.mid.h) for c in candles]
        low_prices = [float(c.mid.l) for c in candles]
        volumes = [int(c.volume) for c in candles]

        # Convert to pandas
        close_series = pd.Series(close_prices)
        high_series = pd.Series(high_prices)
        low_series = pd.Series(low_prices)
        volume_series = pd.Series(volumes)

        # Volume
        avg_volume = volume_series.mean()
        recent_volume = volume_series.iloc[-10:].mean()

        # ATR (using 14 periods)
        tr1 = high_series - low_series
        tr2 = abs(high_series - close_series.shift(1))
        tr3 = abs(low_series - close_series.shift(1))
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]

        # RSI (14 periods)
        delta = close_series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        # Moving averages (swing periods)
        ma_short = close_series.rolling(self.ma_short_period).mean().iloc[-1]
        ma_long = close_series.rolling(self.ma_long_period).mean().iloc[-1]

        # Trend strength
        price_above_ma_long = (close_series.iloc[-1] > ma_long)
        ma_slope = (ma_long - close_series.rolling(self.ma_long_period).mean().iloc[-10]) / ma_long

        return {
            "price": close_prices[-1],
            "avg_volume": avg_volume,
            "recent_volume": recent_volume,
            "atr": atr,
            "rsi": rsi,
            "ma_short": ma_short,
            "ma_long": ma_long,
            "trend_strength": abs(ma_slope),
            "price_above_ma": price_above_ma_long,
        }

    def should_enter_trade(self, indicators: Dict) -> bool:
        """
        Swing trading entry criteria (more relaxed than scalping)

        BUY: Uptrend + RSI < 35 (pullback)
        SELL: Downtrend + RSI > 65 (bounce)
        """
        # Trend
        has_uptrend = indicators["ma_short"] > indicators["ma_long"]
        has_downtrend = indicators["ma_short"] < indicators["ma_long"]

        # RSI (more relaxed thresholds for swing)
        is_oversold = indicators["rsi"] < self.rsi_oversold  # < 35
        is_overbought = indicators["rsi"] > self.rsi_overbought  # > 65

        # Entry conditions
        can_buy = has_uptrend and is_oversold
        can_sell = has_downtrend and is_overbought

        return can_buy or can_sell

    def get_trade_direction(self, indicators: Dict) -> Optional[str]:
        """Determine trade direction"""
        has_uptrend = indicators["ma_short"] > indicators["ma_long"]
        is_oversold = indicators["rsi"] < self.rsi_oversold
        is_overbought = indicators["rsi"] > self.rsi_overbought

        if has_uptrend and is_oversold:
            return "BUY"
        elif not has_uptrend and is_overbought:
            return "SELL"

        return None

    async def analyze_opportunity(self, instrument: str) -> Optional[Dict]:
        """
        Complete opportunity analysis with AI agents and Phase 3 features
        """
        try:
            # Economic calendar check
            if self.economic_calendar:
                is_safe, blocking_event = self.economic_calendar.is_safe_to_trade(
                    instrument,
                    datetime.now(),
                    buffer_minutes_before=60,  # Longer buffer for swing
                    buffer_minutes_after=120,
                )

                if not is_safe:
                    logger.info(f"⏸️  {instrument}: News block - {blocking_event.event_name}")
                    return None

            # Get 4H candles
            candles = self.get_candles(instrument, count=100)
            if not candles:
                return None

            # Calculate indicators
            indicators = self.calculate_indicators(candles)
            if not indicators:
                return None

            # Check entry criteria
            if not self.should_enter_trade(indicators):
                return None

            # Get direction
            direction = self.get_trade_direction(indicators)
            if not direction:
                return None

            logger.info(f"💡 {instrument}: Signal detected - {direction} (RSI: {indicators['rsi']:.1f})")

            # Get sentiment
            sentiment = None
            if self.sentiment_analyzer:
                try:
                    sentiment = await self.sentiment_analyzer.get_sentiment(
                        instrument,
                        lookback_hours=24  # Longer lookback for swing
                    )
                except Exception as e:
                    logger.warning(f"Sentiment failed: {e}")

            # AI agent recommendation
            if self.enable_agents and AGENTS_AVAILABLE:
                try:
                    # Get account info
                    account = self.api.account.get(self.account_id)
                    balance = float(account.body['account'].balance)

                    # Get positions
                    positions_response = self.api.position.list_open(self.account_id)
                    active_positions = positions_response.body.get('positions', [])

                    recommendation = await get_trading_signal(
                        instrument=instrument,
                        account_balance=balance,
                        active_positions=active_positions,
                        price_data={"candles": candles},
                        technical_indicators=indicators,
                        sentiment_data=sentiment,
                    )

                    if recommendation.action == "HOLD" or recommendation.overall_confidence < 0.6:
                        logger.info(f"⏸️  {instrument}: Agent says HOLD (confidence: {recommendation.overall_confidence:.1%})")
                        return None

                    # Agent approves
                    return {
                        "instrument": instrument,
                        "direction": recommendation.action,
                        "confidence": recommendation.overall_confidence,
                        "reasoning": recommendation.reasoning,
                        "indicators": indicators,
                        "sentiment": sentiment,
                        "agent_recommendation": recommendation,
                    }

                except Exception as e:
                    logger.error(f"Agent analysis failed: {e}")

            # Traditional analysis
            return {
                "instrument": instrument,
                "direction": direction,
                "confidence": 0.6,
                "reasoning": f"Swing signal: {direction} (RSI: {indicators['rsi']:.1f})",
                "indicators": indicators,
                "sentiment": sentiment,
            }

        except Exception as e:
            logger.error(f"Error analyzing {instrument}: {e}")
            return None

    async def execute_trade(self, opportunity: Dict) -> bool:
        """Execute swing trade"""
        try:
            instrument = opportunity["instrument"]
            direction = opportunity["direction"]
            indicators = opportunity["indicators"]

            # Get account
            account = self.api.account.get(self.account_id)
            balance = float(account.body['account'].balance)

            # Calculate position size
            current_price = indicators["price"]
            atr = indicators["atr"]
            stop_loss_distance = atr * self.atr_multiplier  # Wider for swing

            pip_value = self.pip_calculator.calculate_pip_value(
                instrument=instrument,
                account_currency="USD",
                current_rate=current_price,
                units=10000,
            )

            pip_location = 0.01 if "_JPY" in instrument else 0.0001
            stop_loss_pips = stop_loss_distance / pip_location

            sizing = self.pip_calculator.calculate_position_size_from_risk(
                instrument=instrument,
                account_balance=balance,
                risk_percent=self.risk_percent,
                stop_loss_pips=stop_loss_pips,
                account_currency="USD",
                current_rate=current_price,
            )

            units = sizing["units"]
            if direction == "SELL":
                units = -abs(units)
            else:
                units = abs(units)

            # Calculate stops (wider for swing)
            if direction == "BUY":
                stop_loss = current_price - stop_loss_distance
                take_profit = current_price + (stop_loss_distance * self.reward_risk_ratio)
            else:
                stop_loss = current_price + stop_loss_distance
                take_profit = current_price - (stop_loss_distance * self.reward_risk_ratio)

            # Log trade
            logger.info(f"\n{'='*70}")
            logger.info(f"🎯 SWING TRADE: {direction} {instrument}")
            logger.info(f"{'='*70}")
            logger.info(f"Confidence: {opportunity['confidence']:.1%}")
            logger.info(f"Reasoning: {opportunity['reasoning']}")
            logger.info(f"RSI: {indicators['rsi']:.1f}")
            logger.info(f"Timeframe: 4H")
            logger.info(f"Units: {units}")
            logger.info(f"Entry: {current_price:.5f}")
            logger.info(f"Stop Loss: {stop_loss:.5f} ({stop_loss_pips:.1f} pips)")
            logger.info(f"Take Profit: {take_profit:.5f} ({stop_loss_pips * self.reward_risk_ratio:.1f} pips)")
            logger.info(f"R:R Ratio: {self.reward_risk_ratio}:1")
            logger.info(f"{'='*70}\n")

            # Execute trade
            response = self.api.order.market(
                self.account_id,
                instrument=instrument,
                units=units,
                stopLossOnFill={"price": str(stop_loss)},
                takeProfitOnFill={"price": str(take_profit)}
            )

            if response.status == 201:
                logger.info(f"✅ Trade executed successfully!")

                # Journal
                if self.trade_journal:
                    entry = TradeJournalEntry(
                        trade_id=response.body['orderFillTransaction'].id,
                        timestamp=datetime.now(),
                        instrument=instrument,
                        direction=direction,
                        units=units,
                        entry_price=current_price,
                        entry_time=datetime.now(),
                        overall_confidence=opportunity["confidence"],
                        environment=self.environment,
                        stop_loss_price=stop_loss,
                        take_profit_price=take_profit,
                    )
                    self.trade_journal.log_entry(entry)

                # Alert
                if self.alert_manager:
                    await self.alert_manager.alert_trade_opened({
                        "instrument": instrument,
                        "direction": direction,
                        "units": units,
                        "entry_price": current_price,
                        "confidence": opportunity["confidence"],
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                    })

                return True
            else:
                logger.error(f"❌ Trade failed: {response.body}")
                return False

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            if self.alert_manager:
                await self.alert_manager.alert_system_error("TradeExecutionError", str(e))
            return False

    async def run(self):
        """Main trading loop"""
        logger.info("🚀 Swing Trading Strategy Started\n")

        if self.alert_manager:
            await self.alert_manager.alert_info(
                "Swing Trading Started",
                f"Strategy initialized at {datetime.now()}"
            )

        last_health_check = datetime.now()

        try:
            while True:
                # Health check
                if (datetime.now() - last_health_check).seconds > 300:
                    if self.system_monitor:
                        await self.system_monitor.run_health_check()
                    last_health_check = datetime.now()

                # Scan instruments
                for instrument in self.instruments:
                    # Check max positions
                    positions_response = self.api.position.list_open(self.account_id)
                    open_count = len(positions_response.body.get('positions', []))

                    if open_count >= self.max_positions:
                        logger.info(f"Max positions ({self.max_positions}) reached")
                        break

                    # Analyze
                    opportunity = await self.analyze_opportunity(instrument)
                    if opportunity:
                        await self.execute_trade(opportunity)

                # Wait before next scan (1 hour for 4H timeframe)
                logger.info(f"Waiting {self.scan_interval}s before next scan...")
                await asyncio.sleep(self.scan_interval)

        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutting down...")
            await self.shutdown()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            if self.alert_manager:
                await self.alert_manager.alert_emergency("System Crash", str(e))
            await self.shutdown()

    async def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down swing trading strategy...")

        if self.alert_manager:
            await self.alert_manager.alert_info(
                "System Stopped",
                f"Swing strategy shut down at {datetime.now()}"
            )

        if self.economic_calendar:
            await self.economic_calendar.close()

        if self.sentiment_analyzer:
            await self.sentiment_analyzer.close()

        if self.trade_journal:
            self.trade_journal.close()

        if self.alert_manager:
            await self.alert_manager.close()

        logger.info("✅ Shutdown complete")


async def main():
    parser = argparse.ArgumentParser(description="Swing Trading Strategy")
    parser.add_argument("--config", default="v20.conf")
    parser.add_argument("--env", choices=["practice", "live"], default="practice")
    parser.add_argument("--backtest", action="store_true", help="Run backtest mode")
    parser.add_argument("--paper-trade", action="store_true", help="Paper trade (practice)")
    parser.add_argument("--live", action="store_true", help="Live trade (real money)")
    parser.add_argument("--months", type=int, default=12, help="Backtest months")
    parser.add_argument("--disable-agents", action="store_true")
    parser.add_argument("--disable-calendar", action="store_true")
    parser.add_argument("--disable-sentiment", action="store_true")

    args = parser.parse_args()

    if args.backtest:
        logger.info("Backtest mode not yet implemented for swing strategy")
        logger.info("Use: uv run python comprehensive_backtest.py --months 12")
        logger.info("Then adjust unified_strategy.py to 4H timeframe")
        return

    if args.live and args.env == "live":
        logger.error("⚠️  LIVE TRADING NOT RECOMMENDED!")
        logger.error("Strategy needs validation with positive backtest results first.")
        response = input("Type 'I understand the risks' to proceed: ")
        if response != "I understand the risks":
            logger.info("Aborting live trading.")
            return

    # Initialize strategy
    strategy = SwingTradingStrategy(
        config_file=args.config,
        environment=args.env,
        enable_agents=not args.disable_agents,
        enable_calendar=not args.disable_calendar,
        enable_sentiment=not args.disable_sentiment,
    )

    # Run
    await strategy.run()


if __name__ == "__main__":
    asyncio.run(main())
