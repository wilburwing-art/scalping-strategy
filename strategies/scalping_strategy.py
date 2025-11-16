import argparse
import json
import time
import pandas as pd
import numpy as np
import requests
from dateutil.parser import parse
from v20 import Context
from v20.errors import V20ConnectionError, V20Timeout
import configparser
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scalping_strategy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ScalpingStrategy")

class ScalpingStrategy:
    def __init__(self, config_file="v20.conf", environment="practice"):
        """Initialize the scalping strategy with configuration."""
        self.config_file = config_file
        self.environment = environment
        self.config = self._load_config()
        
        # Initialize API context
        self.ctx = Context(
            self.config["hostname"],
            token=self.config["token"],
            application="ScalpingStrategy"
        )
        self.account_id = self.config["account_id"]
        
        # Strategy parameters (can be adjusted)
        self.volume_threshold = 1000  # Minimum volume for consideration
        self.volatility_window = 14   # Period for calculating volatility
        self.volatility_min = 0.0005  # Minimum volatility (in decimal)
        self.rsi_period = 14          # Period for RSI calculation
        self.rsi_overbought = 70      # RSI overbought threshold
        self.rsi_oversold = 30        # RSI oversold threshold
        self.risk_percent = 1.0       # Risk per trade (% of account)
        self.reward_risk_ratio = 1.5  # Reward to risk ratio
        
        # Tracking active trades
        self.active_trades = {}
    
    def _load_config(self):
        """Load configuration from the config file."""
        if not os.path.isfile(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        config_parser = configparser.ConfigParser()
        config_parser.read(self.config_file)
        
        return {
            "hostname": config_parser[self.environment]["hostname"],
            "token": config_parser[self.environment]["token"],
            "account_id": config_parser[self.environment]["account_id"],
        }
    
    def get_account_details(self):
        """Get current account details."""
        response = self.ctx.account.summary(self.account_id)
        return response.body.get("account", None)
    
    def get_tradeable_instruments(self):
        """Get list of tradeable instruments."""
        response = self.ctx.account.instruments(self.account_id)
        return response.body.get("instruments", [])
    
    def get_instrument_candles(self, instrument, count=100, granularity="M5"):
        """Get historical candles for an instrument."""
        try:
            response = self.ctx.instrument.candles(
                instrument,
                count=count,
                granularity=granularity,
                price="M"  # Midpoint prices
            )
            return response.body.get("candles", [])
        except Exception as e:
            logger.error(f"Error fetching candles for {instrument}: {str(e)}")
            return []
    
    def calculate_indicators(self, candles):
        """Calculate technical indicators from candles."""
        if not candles or len(candles) < self.volatility_window:
            return None
        
        # Extract prices and volume
        close_prices = [float(candle.mid.c) for candle in candles]
        high_prices = [float(candle.mid.h) for candle in candles]
        low_prices = [float(candle.mid.l) for candle in candles]
        volumes = [int(candle.volume) for candle in candles]
        
        # Convert to pandas Series for easier calculations
        close_series = pd.Series(close_prices)
        high_series = pd.Series(high_prices)
        low_series = pd.Series(low_prices)
        volume_series = pd.Series(volumes)
        
        # Calculate volume metrics
        avg_volume = volume_series.mean()
        recent_volume = volume_series.iloc[-5:].mean()  # Last 5 candles
        
        # Calculate volatility (Average True Range)
        tr1 = high_series - low_series
        tr2 = abs(high_series - close_series.shift(1))
        tr3 = abs(low_series - close_series.shift(1))
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = true_range.rolling(self.volatility_window).mean().iloc[-1]
        
        # Calculate RSI
        delta = close_series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Calculate moving averages
        ma_short = close_series.rolling(10).mean().iloc[-1]
        ma_long = close_series.rolling(20).mean().iloc[-1]
        ma_50 = close_series.rolling(50).mean().iloc[-1] if len(close_series) >= 50 else ma_long
        ma_200 = close_series.rolling(200).mean().iloc[-1] if len(close_series) >= 200 else ma_long

        # Current price
        current_price = close_prices[-1]

        # Calculate volatility as percentage of price
        volatility = atr / current_price if current_price > 0 else 0

        # Recent high/low
        recent_high = high_series.iloc[-20:].max()
        recent_low = low_series.iloc[-20:].max()

        return {
            "price": current_price,
            "close": current_price,
            "avg_volume": avg_volume,
            "recent_volume": recent_volume,
            "atr": atr,
            "rsi": rsi,
            "ma_short": ma_short,
            "ma_long": ma_long,
            "ma_50": ma_50,
            "ma_200": ma_200,
            "volatility": volatility,
            "recent_high": recent_high,
            "recent_low": recent_low
        }
    
    def check_news_impact(self, instrument):
        """
        Placeholder for checking news impact.
        In a real implementation, you would connect to a news API.
        """
        # This is a simplified version - in practice, you would:
        # 1. Connect to a financial news API
        # 2. Filter for relevant news for the specific instrument
        # 3. Analyze news sentiment and impact
        
        # For demo purposes, returning random news impact
        import random
        news_impact = random.choice(["high", "medium", "low", "none"])
        return news_impact
    
    def is_instrument_tradeable(self, instrument_data, indicators):
        """Determine if an instrument meets our trading criteria."""
        if not indicators:
            return False
        
        # Check volume
        if indicators["recent_volume"] < self.volume_threshold:
            return False
        
        # Check volatility
        if indicators["atr"] < self.volatility_min:
            return False
        
        # Check for potential scalping opportunity
        has_trend = indicators["ma_short"] > indicators["ma_long"]  # Uptrend
        has_momentum = indicators["rsi"] < self.rsi_overbought if has_trend else indicators["rsi"] > self.rsi_oversold
        
        return has_trend and has_momentum
    
    def calculate_position_size(self, account_balance, instrument, indicators):
        """Calculate appropriate position size based on risk parameters."""
        if not indicators:
            return 0
        
        # Determine stop loss distance in pips
        current_price = indicators["price"]
        atr = indicators["atr"]
        stop_loss_distance = atr * 1.5  # Using 1.5x ATR for stop loss
        
        # Calculate risk amount in account currency
        risk_amount = account_balance * (self.risk_percent / 100)
        
        # Calculate position size
        pip_value = self._calculate_pip_value(instrument, current_price)
        if pip_value <= 0:
            return 0
            
        # Position size formula: Risk Amount / (Stop Loss in pips * Pip Value)
        position_size = risk_amount / (stop_loss_distance * pip_value)
        
        # Round down to appropriate precision
        return self._round_units(instrument, position_size)
    
    def _calculate_pip_value(self, instrument, price):
        """Calculate the value of a pip for the given instrument."""
        # This is a simplified calculation and would need to be adjusted
        # based on the specific broker and instrument
        
        # For Forex pairs
        if instrument.endswith("_USD"):
            return 0.0001  # For USD denominated pairs
        elif instrument.startswith("USD_"):
            return 0.0001 / price  # For inverted USD pairs
        else:
            return 0.0001  # Default for other pairs
    
    def _round_units(self, instrument, units):
        """Round units to the appropriate precision for the instrument."""
        # In practice, you would check the minimum trade size for the instrument
        return int(units)
    
    def calculate_entry_exit_levels(self, instrument, indicators, direction="BUY"):
        """Calculate entry, stop loss, and take profit levels."""
        if not indicators:
            return None
        
        current_price = indicators["price"]
        atr = indicators["atr"]
        
        # Entry is current price for market orders
        entry_price = current_price
        
        # Stop loss and take profit based on ATR
        if direction == "BUY":
            stop_loss = entry_price - (atr * 1.5)
            take_profit = entry_price + (atr * 1.5 * self.reward_risk_ratio)
        else:  # SELL
            stop_loss = entry_price + (atr * 1.5)
            take_profit = entry_price - (atr * 1.5 * self.reward_risk_ratio)
        
        return {
            "entry": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def execute_trade(self, instrument, units, stop_loss, take_profit):
        """Execute a trade with the specified parameters."""
        try:
            # Create a market order with stop loss and take profit
            response = self.ctx.order.market(
                self.account_id,
                instrument=instrument,
                units=units,
                stopLossOnFill={"price": str(stop_loss), "timeInForce": "GTC"},
                takeProfitOnFill={"price": str(take_profit), "timeInForce": "GTC"}
            )
            
            # Check if the order was successful
            if "orderFillTransaction" in response.body:
                fill_transaction = response.body.get("orderFillTransaction")
                trade_id = str(fill_transaction.id)
                logger.info(f"Trade executed: {instrument}, {units} units, ID: {trade_id}")

                # Track the trade
                self.active_trades[trade_id] = {
                    "instrument": instrument,
                    "units": units,
                    "entry_price": float(fill_transaction.price),
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "time": str(fill_transaction.time)
                }
                
                return trade_id
            else:
                logger.error(f"Failed to execute trade - orderFillTransaction not in response")
                logger.error(f"Response status: {response.status}, reason: {response.reason}")
                return None
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return None
    
    def monitor_active_trades(self):
        """Monitor and manage active trades."""
        try:
            # Get open trades
            response = self.ctx.trade.list_open(self.account_id)
            open_trades = response.body.get("trades", [])
            
            # Update active trades status
            for trade in open_trades:
                trade_id = trade.id
                if trade_id in self.active_trades:
                    self.active_trades[trade_id]["current_price"] = float(trade.price)
                    self.active_trades[trade_id]["unrealized_pl"] = float(trade.unrealizedPL)
            
            # Clean up closed trades
            active_trade_ids = [trade.id for trade in open_trades]
            closed_trade_ids = [tid for tid in self.active_trades if tid not in active_trade_ids]
            
            for tid in closed_trade_ids:
                logger.info(f"Trade closed: {self.active_trades[tid]['instrument']}, ID: {tid}")
                del self.active_trades[tid]
                
            return len(self.active_trades)
        except Exception as e:
            logger.error(f"Error monitoring trades: {str(e)}")
            return -1
    
    def close_trade(self, trade_id):
        """Close a specific trade."""
        try:
            if trade_id not in self.active_trades:
                logger.warning(f"Trade ID {trade_id} not found in active trades")
                return False
            
            response = self.ctx.trade.close(
                self.account_id,
                trade_id
            )
            
            if "orderFillTransaction" in response:
                logger.info(f"Trade {trade_id} closed manually")
                return True
            else:
                logger.error(f"Failed to close trade: {json.dumps(response.body)}")
                return False
        except Exception as e:
            logger.error(f"Error closing trade: {str(e)}")
            return False
    
    def scan_for_opportunities(self):
        """Scan available instruments for trading opportunities."""
        # Get account details
        account = self.get_account_details()
        if not account:
            logger.error("Failed to get account details")
            return []
        
        account_balance = float(account.balance)
        logger.info(f"Account Balance: {account_balance}")
        
        # Get tradeable instruments
        instruments = self.get_tradeable_instruments()
        if not instruments:
            logger.error("Failed to get tradeable instruments")
            return []
        
        opportunities = []
        
        # Filter instruments (focusing on major forex pairs for scalping)
        major_pairs = [inst for inst in instruments 
                      if inst.name.endswith("_USD") or 
                         inst.name.startswith("EUR_") or 
                         inst.name.startswith("GBP_") or
                         inst.name.startswith("USD_")]
        
        # Analyze each instrument
        for instrument in major_pairs[:10]:  # Limit to first 10 for demonstration
            instrument_name = instrument.name
            logger.info(f"Analyzing {instrument_name}")
            
            # Get historical candles
            candles = self.get_instrument_candles(instrument_name)
            if not candles:
                logger.warning(f"No candles retrieved for {instrument_name}")
                continue
            
            # Calculate indicators
            indicators = self.calculate_indicators(candles)
            if not indicators:
                logger.warning(f"Failed to calculate indicators for {instrument_name}")
                continue
            
            # Check if instrument is tradeable based on our criteria
            if not self.is_instrument_tradeable(instrument, indicators):
                logger.info(f"{instrument_name} does not meet trading criteria")
                continue
            
            # Check news impact
            news_impact = self.check_news_impact(instrument_name)
            if news_impact == "high":
                logger.info(f"Skipping {instrument_name} due to high news impact")
                continue
            
            # Determine trade direction
            direction = "BUY" if indicators["ma_short"] > indicators["ma_long"] else "SELL"
            
            # Calculate position size
            units = self.calculate_position_size(account_balance, instrument_name, indicators)
            if direction == "SELL":
                units = -units  # Negative units for sell orders
            
            if abs(units) < 1:
                logger.warning(f"Position size too small for {instrument_name}")
                continue
            
            # Calculate entry, stop loss, and take profit levels
            levels = self.calculate_entry_exit_levels(instrument_name, indicators, direction)
            if not levels:
                continue
            
            opportunity = {
                "instrument": instrument_name,
                "direction": direction,
                "units": units,
                "entry": levels["entry"],
                "stop_loss": levels["stop_loss"],
                "take_profit": levels["take_profit"],
                "indicators": indicators,
                "news_impact": news_impact
            }
            
            opportunities.append(opportunity)
            logger.info(f"Found opportunity: {instrument_name} {direction} {units} units")
        
        return opportunities
    
    def execute_opportunities(self, opportunities, max_trades=3):
        """Execute identified trading opportunities."""
        # Check current number of active trades
        current_trades = self.monitor_active_trades()
        if current_trades < 0:
            logger.error("Failed to monitor active trades")
            return
        
        # Limit the number of concurrent trades
        available_slots = max(0, max_trades - current_trades)
        if available_slots <= 0:
            logger.info("Maximum number of trades already active")
            return
        
        # Sort opportunities by potential (could use other metrics)
        sorted_opportunities = sorted(opportunities, 
                                     key=lambda x: abs(x["indicators"]["rsi"] - 50), 
                                     reverse=True)
        
        # Execute trades for top opportunities
        for opportunity in sorted_opportunities[:available_slots]:
            instrument = opportunity["instrument"]
            units = opportunity["units"]
            stop_loss = opportunity["stop_loss"]
            take_profit = opportunity["take_profit"]
            
            logger.info(f"Executing trade for {instrument}: {units} units, SL: {stop_loss}, TP: {take_profit}")
            trade_id = self.execute_trade(instrument, units, stop_loss, take_profit)
            
            if trade_id:
                logger.info(f"Successfully executed trade with ID: {trade_id}")
            else:
                logger.error(f"Failed to execute trade for {instrument}")
    
    def run(self, interval=300, max_trades=3, runtime=3600):
        """Run the strategy for a specified duration."""
        start_time = time.time()
        logger.info(f"Starting scalping strategy. Max trades: {max_trades}, Scan interval: {interval}s")
        
        while time.time() - start_time < runtime:
            try:
                # Monitor existing trades
                self.monitor_active_trades()
                
                # Scan for new opportunities
                opportunities = self.scan_for_opportunities()
                
                # Execute viable opportunities
                if opportunities:
                    self.execute_opportunities(opportunities, max_trades)
                else:
                    logger.info("No trading opportunities found in this scan")
                
                # Sleep until next scan
                logger.info(f"Sleeping for {interval} seconds until next scan")
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in strategy execution: {str(e)}")
                time.sleep(60)  # Sleep a bit longer if there's an error
        
        logger.info("Strategy run completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forex Scalping Trading Strategy")
    parser.add_argument("--config", default="v20.conf", help="Path to configuration file")
    parser.add_argument("--env", default="practice", help="Environment (practice/live)")
    parser.add_argument("--interval", type=int, default=300, help="Scan interval in seconds")
    parser.add_argument("--max-trades", type=int, default=3, help="Maximum concurrent trades")
    parser.add_argument("--runtime", type=int, default=3600, help="Strategy runtime in seconds")
    
    args = parser.parse_args()
    
    strategy = ScalpingStrategy(config_file=args.config, environment=args.env)
    strategy.run(interval=args.interval, max_trades=args.max_trades, runtime=args.runtime)
