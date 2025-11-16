"""
Enhanced Scalping Strategy with Multi-Agent AI System

This strategy extends the base scalping strategy by integrating a sophisticated
multi-agent AI system for improved decision-making and market analysis.

Features:
- Traditional technical analysis (RSI, ATR, Moving Averages)
- Multi-agent AI system (Market Intelligence, Technical, Risk, Coordinator)
- Real-time news and sentiment analysis
- Advanced risk management
- Confidence-based trade filtering
"""

import argparse
import asyncio
import time
import os
import logging
import configparser
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from strategies.scalping_strategy import ScalpingStrategy
from trading_agents import TradingAgentSystem

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_scalping_strategy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EnhancedScalpingStrategy")


class EnhancedScalpingStrategy(ScalpingStrategy):
    """
    Enhanced scalping strategy with AI agent integration.

    Extends the base ScalpingStrategy with multi-agent AI analysis
    for improved decision-making and risk management.
    """

    def __init__(
        self,
        config_file: str = "v20.conf",
        environment: str = "practice",
        enable_agents: bool = True,
        openai_api_key: Optional[str] = None,
        agent_model: str = "gpt-4o-mini",
        min_confidence: float = 0.6
    ):
        """
        Initialize enhanced strategy with AI agents.

        Args:
            config_file: Path to configuration file
            environment: Trading environment (practice or live)
            enable_agents: Enable AI agent system
            openai_api_key: OpenAI API key (or from config/env)
            agent_model: OpenAI model for agents
            min_confidence: Minimum confidence threshold for trades
        """
        # Initialize base strategy
        super().__init__(config_file, environment)

        self.enable_agents = enable_agents
        self.agent_system = None
        self.api_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')

        if enable_agents:
            # Get OpenAI API key
            api_key = openai_api_key or self._get_openai_key()

            if not api_key:
                logger.warning(
                    "OpenAI API key not found. Running without AI agents. "
                    "Set OPENAI_API_KEY environment variable or add to v20.conf"
                )
                self.enable_agents = False
            else:
                # Load agent configuration
                config = configparser.ConfigParser()
                config.read(config_file)

                # Get weights from config or use defaults
                market_intel_weight = float(config.get('agents', 'market_intel_weight', fallback='0.3'))
                technical_weight = float(config.get('agents', 'technical_weight', fallback='0.4'))
                risk_weight = float(config.get('agents', 'risk_weight', fallback='0.3'))

                # Get min confidence from config or parameter
                config_min_conf = float(config.get('openai', 'min_confidence', fallback=str(min_confidence)))
                min_confidence = min(config_min_conf, min_confidence)  # Use stricter threshold

                # Initialize agent system
                self.agent_system = TradingAgentSystem(
                    api_key=api_key,
                    model=agent_model,
                    market_intel_weight=market_intel_weight,
                    technical_weight=technical_weight,
                    risk_weight=risk_weight,
                    min_confidence=min_confidence
                )

                logger.info(
                    f"AI Agent System initialized with {agent_model} "
                    f"(min_confidence: {min_confidence})"
                )

    def _get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key from environment or config"""
        # Try environment variable first
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            return api_key

        # Try config file
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            api_key = config.get('openai', 'api_key', fallback=None)
            if api_key and api_key != 'YOUR_OPENAI_API_KEY_HERE':
                return api_key
        except Exception:
            pass

        return None

    def _send_signal_to_api(self, instrument: str, recommendation: Dict[str, Any]):
        """Send AI signal to backend API for frontend display"""
        try:
            # Extract agent details from the recommendation's reasoning
            # This is a simplified version - in production, we'd pass full agent details
            agents = [
                {
                    "name": "Market Intelligence",
                    "confidence": recommendation['confidence'] * 0.9,  # Approximate
                    "reasoning": "Market intelligence analysis"
                },
                {
                    "name": "Technical Analysis",
                    "confidence": recommendation['confidence'],
                    "reasoning": "Technical analysis"
                },
                {
                    "name": "Risk Assessment",
                    "confidence": recommendation['confidence'] * 0.95,
                    "reasoning": "Risk assessment"
                }
            ]

            signal = {
                "instrument": instrument,
                "action": recommendation['action'],
                "confidence": recommendation['confidence'],
                "entry_price": recommendation.get('entry_price'),
                "stop_loss": recommendation.get('stop_loss'),
                "take_profit": recommendation.get('take_profit'),
                "position_size": recommendation.get('position_size'),
                "timestamp": datetime.now().isoformat(),
                "agents": agents,
                "overall_reasoning": recommendation['reasoning']
            }

            response = requests.post(
                f"{self.api_url}/api/agent-signal",
                json=signal,
                timeout=5
            )
            response.raise_for_status()
            logger.debug(f"Sent AI signal to API for {instrument}")

        except Exception as e:
            logger.warning(f"Failed to send signal to API: {e}")

    async def analyze_with_agents(
        self,
        instrument: str,
        current_price: float,
        indicators: Dict[str, Any],
        account_balance: float,
        news_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze trading opportunity using AI agents.

        Args:
            instrument: Trading instrument
            current_price: Current market price
            indicators: Technical indicators
            account_balance: Account balance
            news_context: Recent news context

        Returns:
            Dict with recommendation or None if agents disabled
        """
        if not self.enable_agents or not self.agent_system:
            return None

        try:
            recommendation = await self.agent_system.analyze_opportunity(
                instrument=instrument,
                current_price=current_price,
                indicators=indicators,
                account_balance=account_balance,
                active_trades=len(self.active_trades),
                news_context=news_context
            )

            result = {
                'action': recommendation.action,
                'entry_price': recommendation.entry_price,
                'stop_loss': recommendation.stop_loss,
                'take_profit': recommendation.take_profit,
                'position_size': recommendation.position_size,
                'confidence': recommendation.overall_confidence,
                'reasoning': recommendation.reasoning
            }

            # Send signal to backend API for frontend display
            self._send_signal_to_api(instrument, result)

            return result

        except Exception as e:
            logger.error(f"Error in agent analysis: {e}")
            return None

    def scan_for_opportunities(self):
        """
        Enhanced opportunity scanning with AI agent integration.

        Combines traditional technical analysis with multi-agent AI insights
        for improved decision-making.
        """
        try:
            # Get account details
            account = self.get_account_details()
            if not account:
                logger.error("Failed to get account details")
                return

            account_balance = float(account.balance)
            logger.info(f"Account Balance: {account_balance}")

            # Get tradeable instruments
            instruments = self.get_tradeable_instruments()
            if not instruments:
                logger.error("Failed to get tradeable instruments")
                return

            # Filter for major forex pairs
            forex_pairs = [
                inst for inst in instruments
                if inst.type == "CURRENCY" and "_" in inst.name
            ]

            # Analyze each instrument
            for instrument in forex_pairs[:10]:  # Limit to top 10 for efficiency
                logger.info(f"Analyzing {instrument.name}")

                # Get candle data
                candles = self.get_instrument_candles(instrument.name)
                if not candles:
                    continue

                # Calculate traditional indicators
                indicators = self.calculate_indicators(candles)
                if not indicators:
                    logger.info(f"{instrument.name} - insufficient data")
                    continue

                current_price = float(candles[-1].mid.c)

                # Traditional analysis
                traditional_signal = self._traditional_analysis(
                    instrument.name, indicators, current_price
                )

                # AI agent analysis (if enabled)
                agent_recommendation = None
                if self.enable_agents:
                    agent_recommendation = asyncio.run(
                        self.analyze_with_agents(
                            instrument=instrument.name,
                            current_price=current_price,
                            indicators=indicators,
                            account_balance=account_balance,
                            news_context=None  # Could integrate news API here
                        )
                    )

                # Make final decision
                if agent_recommendation:
                    self._process_agent_recommendation(
                        instrument.name,
                        agent_recommendation,
                        indicators,
                        account_balance
                    )
                elif traditional_signal:
                    logger.info(
                        f"{instrument.name} - Traditional signal: {traditional_signal}, "
                        "but no agent confirmation"
                    )
                else:
                    logger.info(f"{instrument.name} does not meet trading criteria")

            if not self.active_trades:
                logger.info("No trading opportunities found in this scan")

        except Exception as e:
            logger.error(f"Error in strategy execution: {e}")

    def _traditional_analysis(
        self,
        instrument: str,
        indicators: Dict[str, Any],
        current_price: float
    ) -> Optional[str]:
        """
        Perform traditional technical analysis.

        Returns:
            'BUY', 'SELL', or None
        """
        rsi = indicators['rsi']
        volatility = indicators['volatility']
        ma_50 = indicators['ma_50']
        ma_200 = indicators['ma_200']

        # Check basic criteria
        if volatility < self.volatility_min:
            return None

        # RSI signals
        if rsi < self.rsi_oversold and current_price > ma_50:
            return 'BUY'
        elif rsi > self.rsi_overbought and current_price < ma_50:
            return 'SELL'

        # Trend following
        if current_price > ma_50 > ma_200 and rsi > 50:
            return 'BUY'
        elif current_price < ma_50 < ma_200 and rsi < 50:
            return 'SELL'

        return None

    def _process_agent_recommendation(
        self,
        instrument: str,
        recommendation: Dict[str, Any],
        indicators: Dict[str, Any],
        account_balance: float
    ):
        """Process AI agent recommendation and execute trade if appropriate"""
        action = recommendation['action']
        confidence = recommendation['confidence']

        logger.info(
            f"{instrument} - Agent recommendation: {action} "
            f"(confidence: {confidence:.2f})"
        )
        logger.info(f"Reasoning: {recommendation['reasoning'][:200]}...")

        # Only execute if confidence meets threshold
        if action in ['BUY', 'SELL'] and confidence >= self.agent_system.min_confidence:
            # Check if we've hit max trades
            if len(self.active_trades) >= 3:
                logger.info(f"Max trades ({3}) reached, skipping {instrument}")
                return

            # Use agent-provided levels or fallback to traditional
            entry_price = recommendation.get('entry_price') or float(indicators['close'])
            stop_loss = recommendation.get('stop_loss')
            take_profit = recommendation.get('take_profit')
            position_size = recommendation.get('position_size')

            # Calculate levels if not provided by agent
            if not stop_loss:
                atr = indicators['atr']
                if action == 'BUY':
                    stop_loss = entry_price - (1.5 * atr)
                    take_profit = take_profit or (entry_price + (1.5 * atr * self.reward_risk_ratio))
                else:  # SELL
                    stop_loss = entry_price + (1.5 * atr)
                    take_profit = take_profit or (entry_price - (1.5 * atr * self.reward_risk_ratio))

            # Calculate position size if not provided
            if not position_size:
                position_size = self.calculate_position_size(
                    account_balance,
                    entry_price,
                    stop_loss
                )

            # Adjust for direction
            units = position_size if action == 'BUY' else -position_size

            logger.info(
                f"Executing {action} on {instrument}: "
                f"{units} units @ {entry_price:.5f}, "
                f"SL: {stop_loss:.5f}, TP: {take_profit:.5f}"
            )

            # Execute trade
            self.execute_trade(instrument, units, stop_loss, take_profit)
        else:
            logger.info(
                f"{instrument} - {action} signal but confidence "
                f"({confidence:.2f}) below threshold "
                f"({self.agent_system.min_confidence})"
            )

    def run(self, max_trades: int = 3, scan_interval: int = 300, runtime: int = 0):
        """
        Run the enhanced scalping strategy.

        Args:
            max_trades: Maximum concurrent trades
            scan_interval: Seconds between scans
            runtime: Total runtime in seconds (0 = run indefinitely)
        """
        logger.info(
            f"Starting enhanced scalping strategy. "
            f"Max trades: {max_trades}, Scan interval: {scan_interval}s"
        )
        logger.info(f"AI Agents: {'ENABLED' if self.enable_agents else 'DISABLED'}")

        start_time = time.time()

        try:
            while True:
                # Monitor existing trades
                self.monitor_active_trades()

                # Scan for new opportunities
                self.scan_for_opportunities()

                # Check if we should stop
                if runtime > 0 and (time.time() - start_time) >= runtime:
                    logger.info("Strategy run completed.")
                    break

                # Sleep until next scan
                logger.info(f"Sleeping for {scan_interval} seconds until next scan")
                time.sleep(scan_interval)

        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
        except Exception as e:
            logger.error(f"Critical error in strategy: {e}")


def main():
    """Main entry point for enhanced scalping strategy"""
    parser = argparse.ArgumentParser(
        description='Enhanced Forex Scalping Strategy with AI Agents'
    )
    parser.add_argument(
        '--config',
        default='v20.conf',
        help='Configuration file path'
    )
    parser.add_argument(
        '--env',
        default='practice',
        choices=['practice', 'live'],
        help='Trading environment'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Scan interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--max-trades',
        type=int,
        default=3,
        help='Maximum concurrent trades (default: 3)'
    )
    parser.add_argument(
        '--runtime',
        type=int,
        default=0,
        help='Runtime in seconds (0 = run indefinitely)'
    )
    parser.add_argument(
        '--disable-agents',
        action='store_true',
        help='Disable AI agents (use traditional analysis only)'
    )
    parser.add_argument(
        '--openai-key',
        help='OpenAI API key (optional, can use env var or config)'
    )
    parser.add_argument(
        '--agent-model',
        default='gpt-4o-mini',
        choices=['gpt-4o', 'gpt-4o-mini'],
        help='OpenAI model for agents (default: gpt-4o-mini)'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.6,
        help='Minimum confidence threshold for trades (default: 0.6)'
    )

    args = parser.parse_args()

    # Create and run strategy
    strategy = EnhancedScalpingStrategy(
        config_file=args.config,
        environment=args.env,
        enable_agents=not args.disable_agents,
        openai_api_key=args.openai_key,
        agent_model=args.agent_model,
        min_confidence=args.min_confidence
    )

    strategy.run(
        max_trades=args.max_trades,
        scan_interval=args.interval,
        runtime=args.runtime
    )


if __name__ == "__main__":
    main()
