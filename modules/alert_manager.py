"""
Production Monitoring & Alert System

Sends alerts for critical trading events via email, SMS (Twilio), and logs.
Monitors system health, trade execution, and error conditions.

Usage:
    alert_mgr = AlertManager(config)

    # Send critical alert
    await alert_mgr.alert_critical("System Error", "OANDA API connection lost")

    # Monitor trade execution
    await alert_mgr.alert_trade_opened(trade)
    await alert_mgr.alert_trade_closed(trade, profit_loss)
"""

import smtplib
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertChannel(Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    LOG = "log"
    WEBHOOK = "webhook"


@dataclass
class AlertConfig:
    """Alert system configuration"""
    # Email settings (Gmail SMTP)
    email_enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""  # Use app-specific password for Gmail
    from_email: str = ""
    to_emails: List[str] = None

    # SMS settings (Twilio)
    sms_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_to_numbers: List[str] = None

    # Webhook settings (Slack, Discord, etc.)
    webhook_enabled: bool = False
    webhook_url: str = ""

    # Alert filtering
    min_priority_email: AlertPriority = AlertPriority.WARNING
    min_priority_sms: AlertPriority = AlertPriority.CRITICAL

    # Rate limiting (avoid spam)
    max_alerts_per_hour: int = 20
    max_sms_per_day: int = 10

    def __post_init__(self):
        if self.to_emails is None:
            self.to_emails = []
        if self.twilio_to_numbers is None:
            self.twilio_to_numbers = []


class AlertManager:
    """
    Comprehensive alert and monitoring system for production trading.

    Features:
    - Multi-channel alerts (email, SMS, webhook)
    - Priority-based routing
    - Rate limiting to prevent spam
    - Alert history tracking
    - System health monitoring

    Usage:
        config = AlertConfig(
            email_enabled=True,
            smtp_username="your@gmail.com",
            smtp_password="app_specific_password",
            to_emails=["alerts@example.com"],
        )

        alert_mgr = AlertManager(config)

        # Critical system alert
        await alert_mgr.alert_critical(
            "API Connection Lost",
            "OANDA API disconnected at 14:23 UTC. Attempting reconnection..."
        )

        # Trade notification
        await alert_mgr.alert_trade_opened({
            "instrument": "EUR_USD",
            "direction": "BUY",
            "units": 10000,
            "price": 1.0850
        })
    """

    def __init__(self, config: AlertConfig):
        """
        Args:
            config: AlertConfig with email/SMS/webhook settings
        """
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=10.0)

        # Rate limiting tracking
        self._alert_history: List[tuple[datetime, AlertPriority]] = []
        self._sms_history: List[datetime] = []

        # System health tracking
        self._last_health_alert = datetime.now()
        self._consecutive_errors = 0

        logger.info(f"AlertManager initialized - Email: {config.email_enabled}, SMS: {config.sms_enabled}, Webhook: {config.webhook_enabled}")

    async def alert_critical(self, subject: str, message: str):
        """Send critical priority alert (all channels)"""
        await self._send_alert(subject, message, AlertPriority.CRITICAL)

    async def alert_warning(self, subject: str, message: str):
        """Send warning priority alert (email + log)"""
        await self._send_alert(subject, message, AlertPriority.WARNING)

    async def alert_info(self, subject: str, message: str):
        """Send info priority alert (log only)"""
        await self._send_alert(subject, message, AlertPriority.INFO)

    async def alert_emergency(self, subject: str, message: str):
        """Send emergency alert (all channels, bypasses rate limits)"""
        await self._send_alert(subject, message, AlertPriority.EMERGENCY, bypass_rate_limit=True)

    async def alert_trade_opened(self, trade_details: Dict):
        """Alert when trade is opened"""
        instrument = trade_details.get("instrument", "UNKNOWN")
        direction = trade_details.get("direction", "UNKNOWN")
        units = trade_details.get("units", 0)
        price = trade_details.get("entry_price", 0.0)

        message = f"""
Trade Opened:
- Instrument: {instrument}
- Direction: {direction}
- Units: {units:,}
- Entry Price: {price:.5f}
- Stop Loss: {trade_details.get('stop_loss', 'N/A')}
- Take Profit: {trade_details.get('take_profit', 'N/A')}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """.strip()

        await self.alert_info(f"Trade Opened: {direction} {instrument}", message)

    async def alert_trade_closed(self, trade_details: Dict, profit_loss: float, reason: str = "UNKNOWN"):
        """Alert when trade is closed"""
        instrument = trade_details.get("instrument", "UNKNOWN")
        direction = trade_details.get("direction", "UNKNOWN")
        pips = trade_details.get("net_pips", 0.0)

        outcome = "PROFIT" if profit_loss > 0 else "LOSS"
        priority = AlertPriority.INFO if profit_loss > 0 else AlertPriority.WARNING

        message = f"""
Trade Closed ({outcome}):
- Instrument: {instrument}
- Direction: {direction}
- Exit Reason: {reason}
- P/L: ${profit_loss:+,.2f} ({pips:+.1f} pips)
- Entry: {trade_details.get('entry_price', 'N/A')}
- Exit: {trade_details.get('exit_price', 'N/A')}
- Hold Time: {trade_details.get('hold_time_minutes', 'N/A')} minutes
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """.strip()

        # For large losses, upgrade to WARNING
        if profit_loss < -100:
            priority = AlertPriority.WARNING
            message = f"⚠️ LARGE LOSS\n\n{message}"

        await self._send_alert(f"Trade Closed: {outcome} {instrument}", message, priority)

    async def alert_daily_summary(self, stats: Dict):
        """Send daily performance summary"""
        total_trades = stats.get("total_trades", 0)
        win_rate = stats.get("win_rate", 0.0)
        total_pl = stats.get("total_profit_usd", 0.0)

        message = f"""
Daily Trading Summary:
- Total Trades: {total_trades}
- Win Rate: {win_rate:.1%}
- Total P/L: ${total_pl:+,.2f}
- Winners: {stats.get('winning_trades', 0)}
- Losers: {stats.get('losing_trades', 0)}
- Avg Win: {stats.get('avg_win_pips', 0):+.1f} pips
- Avg Loss: {stats.get('avg_loss_pips', 0):+.1f} pips
- Max Drawdown: ${stats.get('max_drawdown_usd', 0):,.2f}
- Date: {datetime.now().strftime('%Y-%m-%d')}
        """.strip()

        priority = AlertPriority.INFO if total_pl >= 0 else AlertPriority.WARNING
        await self._send_alert("Daily Trading Summary", message, priority)

    async def alert_system_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None):
        """Alert on system errors"""
        self._consecutive_errors += 1

        message = f"""
System Error Detected:
- Error Type: {error_type}
- Message: {error_message}
- Consecutive Errors: {self._consecutive_errors}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """.strip()

        if stack_trace:
            message += f"\n\nStack Trace:\n{stack_trace}"

        # Escalate to CRITICAL if multiple consecutive errors
        priority = AlertPriority.CRITICAL if self._consecutive_errors >= 3 else AlertPriority.WARNING

        await self._send_alert(f"System Error: {error_type}", message, priority)

    async def alert_health_check(self, status: str, metrics: Dict):
        """Periodic health check alert (only send if issues detected)"""
        issues = []

        # Check various health metrics
        if metrics.get("api_connection_errors", 0) > 0:
            issues.append(f"API Connection Errors: {metrics['api_connection_errors']}")

        if metrics.get("memory_usage_percent", 0) > 90:
            issues.append(f"High Memory Usage: {metrics['memory_usage_percent']}%")

        if metrics.get("consecutive_losses", 0) > 5:
            issues.append(f"Consecutive Losses: {metrics['consecutive_losses']}")

        if metrics.get("account_balance_change_percent", 0) < -10:
            issues.append(f"Account Drawdown: {metrics['account_balance_change_percent']:.1f}%")

        # Only alert if issues found
        if issues:
            message = f"""
System Health Check - ISSUES DETECTED:

Status: {status}

Issues:
{chr(10).join(f"- {issue}" for issue in issues)}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            """.strip()

            await self.alert_warning("Health Check: Issues Detected", message)
        else:
            # Healthy - just log it
            logger.info(f"Health check: {status} - All systems normal")

    async def alert_account_milestone(self, milestone_type: str, details: str):
        """Alert on account milestones (profit targets, drawdown limits, etc.)"""
        message = f"""
Account Milestone:
- Type: {milestone_type}
- Details: {details}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """.strip()

        await self.alert_info(f"Milestone: {milestone_type}", message)

    def reset_error_counter(self):
        """Reset consecutive error counter (call after successful recovery)"""
        if self._consecutive_errors > 0:
            logger.info(f"Resetting error counter (was {self._consecutive_errors})")
            self._consecutive_errors = 0

    async def _send_alert(
        self,
        subject: str,
        message: str,
        priority: AlertPriority,
        bypass_rate_limit: bool = False,
    ):
        """
        Internal method to send alerts via configured channels.
        """
        # Check rate limits
        if not bypass_rate_limit and not self._check_rate_limit(priority):
            logger.warning(f"Alert rate limit exceeded - dropping: {subject}")
            return

        # Always log
        log_level = {
            AlertPriority.INFO: logging.INFO,
            AlertPriority.WARNING: logging.WARNING,
            AlertPriority.CRITICAL: logging.CRITICAL,
            AlertPriority.EMERGENCY: logging.CRITICAL,
        }.get(priority, logging.INFO)

        logger.log(log_level, f"[{priority.value}] {subject}: {message}")

        # Send to appropriate channels based on priority
        tasks = []

        # Email
        if (self.config.email_enabled and
            self._should_send_to_channel(priority, self.config.min_priority_email)):
            tasks.append(self._send_email(subject, message, priority))

        # SMS
        if (self.config.sms_enabled and
            self._should_send_to_channel(priority, self.config.min_priority_sms) and
            self._check_sms_rate_limit()):
            tasks.append(self._send_sms(f"{subject}: {message[:100]}"))

        # Webhook
        if self.config.webhook_enabled:
            tasks.append(self._send_webhook(subject, message, priority))

        # Send all in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Alert delivery failed: {result}")

    def _should_send_to_channel(self, alert_priority: AlertPriority, min_priority: AlertPriority) -> bool:
        """Check if alert should be sent to channel based on priority"""
        priority_order = {
            AlertPriority.INFO: 0,
            AlertPriority.WARNING: 1,
            AlertPriority.CRITICAL: 2,
            AlertPriority.EMERGENCY: 3,
        }
        return priority_order[alert_priority] >= priority_order[min_priority]

    def _check_rate_limit(self, priority: AlertPriority) -> bool:
        """Check if alert rate limit allows sending"""
        # Emergency alerts bypass rate limits
        if priority == AlertPriority.EMERGENCY:
            return True

        # Remove alerts older than 1 hour
        cutoff = datetime.now() - timedelta(hours=1)
        self._alert_history = [(ts, p) for ts, p in self._alert_history if ts > cutoff]

        # Check limit
        if len(self._alert_history) >= self.config.max_alerts_per_hour:
            return False

        # Add this alert to history
        self._alert_history.append((datetime.now(), priority))
        return True

    def _check_sms_rate_limit(self) -> bool:
        """Check SMS-specific rate limit (more restrictive)"""
        # Remove SMS older than 24 hours
        cutoff = datetime.now() - timedelta(days=1)
        self._sms_history = [ts for ts in self._sms_history if ts > cutoff]

        # Check limit
        if len(self._sms_history) >= self.config.max_sms_per_day:
            return False

        # Add this SMS to history
        self._sms_history.append(datetime.now())
        return True

    async def _send_email(self, subject: str, body: str, priority: AlertPriority):
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.from_email
            msg["To"] = ", ".join(self.config.to_emails)
            msg["Subject"] = f"[{priority.value}] {subject}"

            # Add priority header for email clients
            if priority in [AlertPriority.CRITICAL, AlertPriority.EMERGENCY]:
                msg["X-Priority"] = "1"  # Highest priority

            msg.attach(MIMEText(body, "plain"))

            # Connect and send
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)

            logger.info(f"Email alert sent: {subject}")

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            raise

    async def _send_sms(self, message: str):
        """Send SMS via Twilio"""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.twilio_account_sid}/Messages.json"

            for to_number in self.config.twilio_to_numbers:
                data = {
                    "From": self.config.twilio_from_number,
                    "To": to_number,
                    "Body": message[:160],  # SMS character limit
                }

                auth = (self.config.twilio_account_sid, self.config.twilio_auth_token)

                response = await self.http_client.post(url, data=data, auth=auth)
                response.raise_for_status()

                logger.info(f"SMS alert sent to {to_number}")

        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
            raise

    async def _send_webhook(self, subject: str, message: str, priority: AlertPriority):
        """Send to webhook (Slack, Discord, etc.)"""
        try:
            # Generic webhook format (can be customized for specific services)
            payload = {
                "subject": subject,
                "message": message,
                "priority": priority.value,
                "timestamp": datetime.now().isoformat(),
            }

            # For Slack format
            if "slack.com" in self.config.webhook_url:
                payload = {
                    "text": f"*[{priority.value}] {subject}*\n{message}",
                    "username": "Trading Bot",
                }

            # For Discord format
            elif "discord.com" in self.config.webhook_url:
                color = {
                    AlertPriority.INFO: 0x3498db,      # Blue
                    AlertPriority.WARNING: 0xf39c12,   # Orange
                    AlertPriority.CRITICAL: 0xe74c3c,  # Red
                    AlertPriority.EMERGENCY: 0x8b0000, # Dark red
                }.get(priority, 0x3498db)

                payload = {
                    "embeds": [{
                        "title": f"[{priority.value}] {subject}",
                        "description": message,
                        "color": color,
                        "timestamp": datetime.now().isoformat(),
                    }]
                }

            response = await self.http_client.post(self.config.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Webhook alert sent: {subject}")

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            raise

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
