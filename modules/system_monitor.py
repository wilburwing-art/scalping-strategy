"""
System Health Monitoring

Monitors trading system health, performance metrics, and sends alerts
when issues are detected.

Usage:
    monitor = SystemMonitor(alert_manager, journal)

    # Update metrics periodically
    await monitor.update_metrics({
        "api_latency_ms": 150,
        "memory_usage_mb": 450,
        "active_trades": 2,
    })

    # Run health check
    await monitor.run_health_check()
"""

import asyncio
import logging
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from alert_manager import AlertManager

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Current system metrics"""
    timestamp: datetime = field(default_factory=datetime.now)

    # System resources
    cpu_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0

    # Trading metrics
    active_trades: int = 0
    total_trades_today: int = 0
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    account_balance: float = 0.0
    account_balance_change_percent: float = 0.0
    daily_profit_loss: float = 0.0

    # API health
    api_connection_errors: int = 0
    api_latency_ms: float = 0.0
    last_successful_api_call: Optional[datetime] = None

    # Strategy performance
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_percent: float = 0.0

    # Error tracking
    total_errors_today: int = 0
    last_error_time: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_usage_mb": self.memory_usage_mb,
            "memory_usage_percent": self.memory_usage_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "active_trades": self.active_trades,
            "total_trades_today": self.total_trades_today,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "account_balance": self.account_balance,
            "account_balance_change_percent": self.account_balance_change_percent,
            "daily_profit_loss": self.daily_profit_loss,
            "api_connection_errors": self.api_connection_errors,
            "api_latency_ms": self.api_latency_ms,
            "last_successful_api_call": self.last_successful_api_call.isoformat() if self.last_successful_api_call else None,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown_percent": self.max_drawdown_percent,
            "total_errors_today": self.total_errors_today,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }


class SystemMonitor:
    """
    Comprehensive system health monitoring with automatic alerting.

    Monitors:
    - System resources (CPU, memory, disk)
    - Trading performance (P/L, win rate, drawdown)
    - API health (latency, errors, connectivity)
    - Error rates and patterns

    Alerts when:
    - Resource usage exceeds thresholds
    - API connection issues
    - Consecutive losses exceed limit
    - Daily loss limit reached
    - Performance degrades

    Usage:
        from alert_manager import AlertManager, AlertConfig
        from trade_journal import TradeJournal

        alert_mgr = AlertManager(AlertConfig(...))
        journal = TradeJournal("trades.db")

        monitor = SystemMonitor(alert_mgr, journal)

        # In main loop
        while True:
            await monitor.run_health_check()
            await asyncio.sleep(300)  # Every 5 minutes
    """

    def __init__(
        self,
        alert_manager: AlertManager,
        trade_journal=None,  # Optional TradeJournal instance
        health_check_interval_minutes: int = 5,
    ):
        """
        Args:
            alert_manager: AlertManager instance for sending alerts
            trade_journal: Optional TradeJournal for performance metrics
            health_check_interval_minutes: How often to run health checks
        """
        self.alert_manager = alert_manager
        self.trade_journal = trade_journal
        self.health_check_interval = timedelta(minutes=health_check_interval_minutes)

        # Current metrics
        self.metrics = SystemMetrics()

        # Baseline metrics (set at start of day)
        self.baseline_account_balance: Optional[float] = None

        # Last check times
        self.last_health_check = datetime.now()
        self.last_daily_summary = datetime.now().date()

        # Alert thresholds
        self.thresholds = {
            "max_cpu_percent": 90.0,
            "max_memory_percent": 85.0,
            "max_disk_percent": 90.0,
            "max_consecutive_losses": 5,
            "max_daily_loss_percent": -10.0,
            "max_drawdown_percent": -15.0,
            "max_api_latency_ms": 2000,
            "max_api_errors_per_hour": 10,
            "min_win_rate": 0.40,  # 40%
        }

        logger.info(f"SystemMonitor initialized - Health check every {health_check_interval_minutes} minutes")

    async def update_metrics(self, custom_metrics: Dict = None):
        """
        Update system metrics.

        Args:
            custom_metrics: Dictionary of custom metrics to update
        """
        # Update system resource metrics
        self.metrics.timestamp = datetime.now()
        self.metrics.cpu_percent = psutil.cpu_percent(interval=1)

        memory = psutil.virtual_memory()
        process = psutil.Process(os.getpid())
        self.metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        self.metrics.memory_usage_percent = memory.percent

        disk = psutil.disk_usage('/')
        self.metrics.disk_usage_percent = disk.percent

        # Update custom metrics if provided
        if custom_metrics:
            for key, value in custom_metrics.items():
                if hasattr(self.metrics, key):
                    setattr(self.metrics, key, value)

        # Update trading metrics from journal if available
        if self.trade_journal:
            await self._update_trading_metrics()

    async def _update_trading_metrics(self):
        """Update trading metrics from trade journal"""
        try:
            # Get today's statistics
            stats = self.trade_journal.get_statistics(days=1, environment="practice")

            if stats and stats.get("total_trades", 0) > 0:
                self.metrics.total_trades_today = stats.get("total_trades", 0)
                self.metrics.win_rate = stats.get("win_rate", 0.0)
                self.metrics.profit_factor = stats.get("profit_factor", 0.0)
                self.metrics.sharpe_ratio = stats.get("sharpe_ratio", 0.0)
                self.metrics.daily_profit_loss = stats.get("total_profit_usd", 0.0)

                # Calculate drawdown if we have baseline
                if self.baseline_account_balance and self.metrics.account_balance > 0:
                    balance_change = self.metrics.account_balance - self.baseline_account_balance
                    self.metrics.account_balance_change_percent = (
                        (balance_change / self.baseline_account_balance) * 100
                    )

            # Get recent trades to check consecutive wins/losses
            recent_trades = self.trade_journal.get_recent_trades(limit=10)
            if recent_trades:
                self.metrics.consecutive_losses = self._count_consecutive_outcomes(recent_trades, "loss")
                self.metrics.consecutive_wins = self._count_consecutive_outcomes(recent_trades, "win")

        except Exception as e:
            logger.error(f"Failed to update trading metrics: {e}")

    def _count_consecutive_outcomes(self, trades: List, outcome_type: str) -> int:
        """Count consecutive wins or losses from most recent trades"""
        count = 0
        for trade in trades:
            is_win = trade.get("net_pips", 0) > 0
            if outcome_type == "win" and is_win:
                count += 1
            elif outcome_type == "loss" and not is_win:
                count += 1
            else:
                break
        return count

    def set_baseline_account_balance(self, balance: float):
        """Set baseline account balance (call at start of day)"""
        self.baseline_account_balance = balance
        logger.info(f"Baseline account balance set: ${balance:,.2f}")

    def update_account_balance(self, balance: float):
        """Update current account balance"""
        self.metrics.account_balance = balance

        if self.baseline_account_balance:
            change = balance - self.baseline_account_balance
            self.metrics.account_balance_change_percent = (
                (change / self.baseline_account_balance) * 100
            )

    def record_api_call(self, success: bool, latency_ms: float = 0):
        """Record API call result"""
        if success:
            self.metrics.last_successful_api_call = datetime.now()
            self.metrics.api_latency_ms = latency_ms
        else:
            self.metrics.api_connection_errors += 1

    def record_error(self):
        """Record an error occurrence"""
        self.metrics.total_errors_today += 1
        self.metrics.last_error_time = datetime.now()

    async def run_health_check(self) -> Dict:
        """
        Run comprehensive health check and send alerts if issues detected.

        Returns:
            Dictionary with health status and issues
        """
        # Check if it's time for health check
        if datetime.now() - self.last_health_check < self.health_check_interval:
            return {"status": "SKIPPED", "reason": "Too soon since last check"}

        self.last_health_check = datetime.now()

        # Update metrics
        await self.update_metrics()

        # Check for issues
        issues = []
        warnings = []

        # System resource checks
        if self.metrics.cpu_percent > self.thresholds["max_cpu_percent"]:
            issues.append(f"High CPU usage: {self.metrics.cpu_percent:.1f}%")

        if self.metrics.memory_usage_percent > self.thresholds["max_memory_percent"]:
            issues.append(f"High memory usage: {self.metrics.memory_usage_percent:.1f}%")

        if self.metrics.disk_usage_percent > self.thresholds["max_disk_percent"]:
            warnings.append(f"High disk usage: {self.metrics.disk_usage_percent:.1f}%")

        # Trading performance checks
        if self.metrics.consecutive_losses >= self.thresholds["max_consecutive_losses"]:
            issues.append(f"Consecutive losses: {self.metrics.consecutive_losses}")

        if self.metrics.account_balance_change_percent < self.thresholds["max_daily_loss_percent"]:
            issues.append(f"Daily loss limit approached: {self.metrics.account_balance_change_percent:.1f}%")

        if self.metrics.win_rate < self.thresholds["min_win_rate"] and self.metrics.total_trades_today > 10:
            warnings.append(f"Low win rate: {self.metrics.win_rate:.1%} ({self.metrics.total_trades_today} trades)")

        # API health checks
        if self.metrics.api_connection_errors > 0:
            warnings.append(f"API connection errors: {self.metrics.api_connection_errors}")

        if self.metrics.api_latency_ms > self.thresholds["max_api_latency_ms"]:
            warnings.append(f"High API latency: {self.metrics.api_latency_ms:.0f}ms")

        # Determine overall status
        if issues:
            status = "CRITICAL"
        elif warnings:
            status = "WARNING"
        else:
            status = "HEALTHY"

        # Send alert if issues detected
        if status != "HEALTHY":
            await self.alert_manager.alert_health_check(status, self.metrics.to_dict())
        else:
            logger.info(f"Health check: {status} - All systems normal")

        # Check if we should send daily summary
        await self._check_daily_summary()

        return {
            "status": status,
            "issues": issues,
            "warnings": warnings,
            "metrics": self.metrics.to_dict(),
        }

    async def _check_daily_summary(self):
        """Send daily summary if it's a new day"""
        today = datetime.now().date()

        if today > self.last_daily_summary and self.trade_journal:
            # New day - send yesterday's summary
            stats = self.trade_journal.get_statistics(days=1, environment="practice")

            if stats and stats.get("total_trades", 0) > 0:
                await self.alert_manager.alert_daily_summary(stats)

            self.last_daily_summary = today

            # Reset daily counters
            self.metrics.total_trades_today = 0
            self.metrics.daily_profit_loss = 0.0
            self.metrics.api_connection_errors = 0
            self.metrics.total_errors_today = 0

    async def check_emergency_stop_conditions(self) -> tuple[bool, Optional[str]]:
        """
        Check if emergency stop conditions are met.

        Returns:
            (should_stop, reason)
        """
        # Daily loss limit
        if self.metrics.account_balance_change_percent <= self.thresholds["max_daily_loss_percent"]:
            reason = f"Daily loss limit reached: {self.metrics.account_balance_change_percent:.1f}%"
            await self.alert_manager.alert_emergency("EMERGENCY STOP", reason)
            return True, reason

        # Maximum drawdown
        if self.metrics.max_drawdown_percent <= self.thresholds["max_drawdown_percent"]:
            reason = f"Maximum drawdown exceeded: {self.metrics.max_drawdown_percent:.1f}%"
            await self.alert_manager.alert_emergency("EMERGENCY STOP", reason)
            return True, reason

        # API completely unavailable
        if (self.metrics.last_successful_api_call and
            datetime.now() - self.metrics.last_successful_api_call > timedelta(minutes=10)):
            reason = "API unavailable for 10+ minutes"
            await self.alert_manager.alert_emergency("EMERGENCY STOP", reason)
            return True, reason

        return False, None

    def get_current_status(self) -> str:
        """Get human-readable status summary"""
        lines = [
            f"System Status: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"Resources:",
            f"  CPU: {self.metrics.cpu_percent:.1f}%",
            f"  Memory: {self.metrics.memory_usage_mb:.1f}MB ({self.metrics.memory_usage_percent:.1f}%)",
            f"  Disk: {self.metrics.disk_usage_percent:.1f}%",
            f"",
            f"Trading:",
            f"  Active Trades: {self.metrics.active_trades}",
            f"  Trades Today: {self.metrics.total_trades_today}",
            f"  Win Rate: {self.metrics.win_rate:.1%}",
            f"  Daily P/L: ${self.metrics.daily_profit_loss:+,.2f}",
            f"  Account Change: {self.metrics.account_balance_change_percent:+.2f}%",
            f"  Consecutive Losses: {self.metrics.consecutive_losses}",
            f"",
            f"API Health:",
            f"  Connection Errors: {self.metrics.api_connection_errors}",
            f"  Latency: {self.metrics.api_latency_ms:.0f}ms",
            f"  Last Success: {self.metrics.last_successful_api_call.strftime('%H:%M:%S') if self.metrics.last_successful_api_call else 'Never'}",
        ]
        return "\n".join(lines)
