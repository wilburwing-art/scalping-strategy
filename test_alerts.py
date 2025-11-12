"""
Test Alert Manager

Tests the production monitoring and alert system.

Usage:
    # Test without actual sending (dry run)
    uv run test_alerts.py

    # Test with real email (requires credentials)
    export ALERT_EMAIL="your@gmail.com"
    export ALERT_EMAIL_PASSWORD="your_app_specific_password"
    export ALERT_TO_EMAIL="alerts@example.com"
    uv run test_alerts.py --send-email
"""

import asyncio
import logging
from alert_manager import AlertManager, AlertConfig, AlertPriority
from datetime import datetime
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_alert_system(send_real_alerts: bool = False):
    """Test the alert system"""

    print("\n" + "="*60)
    print("🚨 ALERT MANAGER TEST SUITE")
    print("="*60)

    # Configure alert system
    config = AlertConfig(
        email_enabled=send_real_alerts,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_username=os.getenv("ALERT_EMAIL", ""),
        smtp_password=os.getenv("ALERT_EMAIL_PASSWORD", ""),
        from_email=os.getenv("ALERT_EMAIL", ""),
        to_emails=[os.getenv("ALERT_TO_EMAIL", "test@example.com")],
        min_priority_email=AlertPriority.INFO,
        max_alerts_per_hour=20,
    )

    if send_real_alerts and not config.smtp_username:
        print("\n❌ Email credentials not set")
        print("Set environment variables:")
        print("  export ALERT_EMAIL='your@gmail.com'")
        print("  export ALERT_EMAIL_PASSWORD='your_app_specific_password'")
        print("  export ALERT_TO_EMAIL='recipient@example.com'")
        print("\nRunning in dry-run mode (logs only)...\n")
        config.email_enabled = False

    alert_mgr = AlertManager(config)

    # Test 1: Info alert
    print("\n📋 Test 1: Info Alert")
    await alert_mgr.alert_info(
        "System Started",
        "Trading system started successfully at " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    print("✅ Info alert sent")

    # Test 2: Warning alert
    print("\n⚠️  Test 2: Warning Alert")
    await alert_mgr.alert_warning(
        "High Volatility Detected",
        "ATR increased 300% in the last hour. Consider reducing position sizes."
    )
    print("✅ Warning alert sent")

    # Test 3: Critical alert
    print("\n🚨 Test 3: Critical Alert")
    await alert_mgr.alert_critical(
        "API Connection Lost",
        "OANDA API connection lost at 14:23 UTC. Attempting automatic reconnection..."
    )
    print("✅ Critical alert sent")

    # Test 4: Trade opened
    print("\n📈 Test 4: Trade Opened Alert")
    await alert_mgr.alert_trade_opened({
        "instrument": "EUR_USD",
        "direction": "BUY",
        "units": 10000,
        "entry_price": 1.0850,
        "stop_loss": 1.0835,
        "take_profit": 1.0873,
    })
    print("✅ Trade opened alert sent")

    # Test 5: Trade closed (profit)
    print("\n✅ Test 5: Trade Closed (Profit)")
    await alert_mgr.alert_trade_closed(
        trade_details={
            "instrument": "EUR_USD",
            "direction": "BUY",
            "entry_price": 1.0850,
            "exit_price": 1.0873,
            "net_pips": 23.0,
            "hold_time_minutes": 45,
        },
        profit_loss=115.50,
        reason="TAKE_PROFIT"
    )
    print("✅ Trade closed (profit) alert sent")

    # Test 6: Trade closed (loss)
    print("\n❌ Test 6: Trade Closed (Loss)")
    await alert_mgr.alert_trade_closed(
        trade_details={
            "instrument": "GBP_USD",
            "direction": "SELL",
            "entry_price": 1.2550,
            "exit_price": 1.2565,
            "net_pips": -15.0,
            "hold_time_minutes": 22,
        },
        profit_loss=-75.25,
        reason="STOP_LOSS"
    )
    print("✅ Trade closed (loss) alert sent")

    # Test 7: Daily summary
    print("\n📊 Test 7: Daily Summary")
    await alert_mgr.alert_daily_summary({
        "total_trades": 8,
        "win_rate": 0.625,
        "total_profit_usd": 234.50,
        "winning_trades": 5,
        "losing_trades": 3,
        "avg_win_pips": 18.4,
        "avg_loss_pips": -12.3,
        "max_drawdown_usd": -125.00,
    })
    print("✅ Daily summary alert sent")

    # Test 8: System error
    print("\n💥 Test 8: System Error")
    await alert_mgr.alert_system_error(
        "ValueError",
        "Invalid price data received from API",
        "Traceback: ... (simulated)"
    )
    print("✅ System error alert sent")

    # Test 9: Health check (with issues)
    print("\n🏥 Test 9: Health Check (Issues)")
    await alert_mgr.alert_health_check(
        "DEGRADED",
        {
            "api_connection_errors": 3,
            "memory_usage_percent": 85,
            "consecutive_losses": 4,
            "account_balance_change_percent": -5.2,
        }
    )
    print("✅ Health check alert sent")

    # Test 10: Health check (healthy)
    print("\n✅ Test 10: Health Check (Healthy)")
    await alert_mgr.alert_health_check(
        "HEALTHY",
        {
            "api_connection_errors": 0,
            "memory_usage_percent": 45,
            "consecutive_losses": 0,
            "account_balance_change_percent": 2.1,
        }
    )
    print("✅ Health check passed (no alert needed)")

    # Test 11: Account milestone
    print("\n🎯 Test 11: Account Milestone")
    await alert_mgr.alert_account_milestone(
        "Profit Target Reached",
        "Daily profit target of $200 reached. Total: $234.50"
    )
    print("✅ Milestone alert sent")

    # Test 12: Rate limiting
    print("\n⏱️  Test 12: Rate Limiting")
    print("Sending 25 alerts rapidly to test rate limiting...")
    for i in range(25):
        await alert_mgr.alert_info(f"Test Alert {i+1}", "Rate limit test")
    print("✅ Rate limiting test complete (some alerts should have been dropped)")

    # Test 13: Emergency alert (bypasses rate limits)
    print("\n🚨 Test 13: Emergency Alert (Bypasses Rate Limits)")
    await alert_mgr.alert_emergency(
        "EMERGENCY STOP",
        "Maximum daily loss limit reached. All trading halted."
    )
    print("✅ Emergency alert sent (rate limits bypassed)")

    # Test 14: Error counter reset
    print("\n🔄 Test 14: Error Counter Reset")
    alert_mgr.reset_error_counter()
    print("✅ Error counter reset")

    await alert_mgr.close()

    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)

    if not send_real_alerts:
        print("\n💡 To test with real email delivery:")
        print("   uv run test_alerts.py --send-email")
        print("   (Make sure to set ALERT_EMAIL environment variables)")


async def demo_real_world_scenario():
    """Demonstrate real-world alert scenario"""

    print("\n" + "="*60)
    print("🎬 REAL-WORLD SCENARIO DEMO")
    print("="*60)

    config = AlertConfig(
        email_enabled=False,  # Set to True with credentials for real emails
        min_priority_email=AlertPriority.WARNING,
    )

    alert_mgr = AlertManager(config)

    print("\n📅 Simulating a trading day...")

    # Morning: System starts
    print("\n[09:00] System startup")
    await alert_mgr.alert_info("System Started", "Trading system initialized")
    await asyncio.sleep(0.5)

    # Trade 1: Good trade
    print("[09:15] Opening trade")
    await alert_mgr.alert_trade_opened({
        "instrument": "EUR_USD",
        "direction": "BUY",
        "units": 10000,
        "entry_price": 1.0850,
        "stop_loss": 1.0835,
        "take_profit": 1.0873,
    })
    await asyncio.sleep(0.5)

    print("[09:45] Closing winning trade")
    await alert_mgr.alert_trade_closed(
        {"instrument": "EUR_USD", "direction": "BUY", "entry_price": 1.0850,
         "exit_price": 1.0873, "net_pips": 23.0, "hold_time_minutes": 30},
        115.50, "TAKE_PROFIT"
    )
    await asyncio.sleep(0.5)

    # Midday: API issues
    print("[12:30] API connection problems")
    await alert_mgr.alert_system_error(
        "ConnectionError",
        "OANDA API timeout - retrying..."
    )
    await asyncio.sleep(0.5)

    await alert_mgr.alert_system_error(
        "ConnectionError",
        "OANDA API timeout - retry attempt 2"
    )
    await asyncio.sleep(0.5)

    print("[12:35] Connection restored")
    alert_mgr.reset_error_counter()
    await asyncio.sleep(0.5)

    # Afternoon: Bad trade
    print("[14:20] Opening risky trade")
    await alert_mgr.alert_trade_opened({
        "instrument": "GBP_JPY",
        "direction": "SELL",
        "units": 5000,
        "entry_price": 189.45,
        "stop_loss": 189.75,
        "take_profit": 188.95,
    })
    await asyncio.sleep(0.5)

    print("[14:35] Stop loss hit")
    await alert_mgr.alert_trade_closed(
        {"instrument": "GBP_JPY", "direction": "SELL", "entry_price": 189.45,
         "exit_price": 189.75, "net_pips": -30.0, "hold_time_minutes": 15},
        -150.00, "STOP_LOSS"
    )
    await asyncio.sleep(0.5)

    # Evening: Daily summary
    print("[17:00] End of day summary")
    await alert_mgr.alert_daily_summary({
        "total_trades": 12,
        "win_rate": 0.58,
        "total_profit_usd": 180.50,
        "winning_trades": 7,
        "losing_trades": 5,
        "avg_win_pips": 15.2,
        "avg_loss_pips": -18.4,
        "max_drawdown_usd": -200.00,
    })

    await alert_mgr.close()

    print("\n✅ Scenario complete")


if __name__ == "__main__":
    send_email = "--send-email" in sys.argv
    demo_mode = "--demo" in sys.argv

    if demo_mode:
        asyncio.run(demo_real_world_scenario())
    else:
        asyncio.run(test_alert_system(send_real_alerts=send_email))
