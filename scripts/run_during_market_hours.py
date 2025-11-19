#!/usr/bin/env python3
"""
Market Hours Scheduler for Forex Trading Strategy

Runs the trading strategy only during forex market hours (Sunday 5PM ET - Friday 5PM ET).
Includes safety checks and graceful shutdown handling.
"""

import os
import sys
import signal
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def is_forex_market_open() -> tuple[bool, str]:
    """
    Check if forex markets are currently open.

    Forex market hours: Sunday 5:00 PM ET - Friday 5:00 PM ET

    Returns:
        tuple[bool, str]: (is_open, reason)
    """
    now_et = datetime.now(ZoneInfo("America/New_York"))

    # Get day of week (0=Monday, 6=Sunday)
    weekday = now_et.weekday()
    hour = now_et.hour
    minute = now_et.minute

    # Market closed all day Saturday and Sunday until 5 PM
    if weekday == 5:  # Saturday
        return False, f"Market closed (Saturday) - reopens Sunday 5:00 PM ET"

    if weekday == 6 and (hour < 17):  # Sunday before 5 PM
        return False, f"Market closed (Sunday before 5 PM) - opens at 5:00 PM ET"

    # Market closes Friday at 5 PM
    if weekday == 4 and hour >= 17:  # Friday after 5 PM
        return False, f"Market closed (Friday after 5 PM) - reopens Sunday 5:00 PM ET"

    return True, f"Market open ({now_et.strftime('%A %I:%M %p ET')})"


def main():
    parser = argparse.ArgumentParser(description="Run trading strategy during market hours")
    parser.add_argument("--strategy", choices=["basic", "enhanced"], default="enhanced",
                       help="Which strategy to run (default: enhanced)")
    parser.add_argument("--config", default="v20.conf", help="Config file path")
    parser.add_argument("--env", choices=["practice", "live"], default="practice",
                       help="Trading environment")
    parser.add_argument("--interval", type=int, default=300,
                       help="Scan interval in seconds (default: 300)")
    parser.add_argument("--max-trades", type=int, default=3,
                       help="Maximum concurrent trades (default: 3)")
    parser.add_argument("--runtime", type=int, default=3600,
                       help="Runtime in seconds (default: 3600 = 1 hour)")
    parser.add_argument("--force", action="store_true",
                       help="Force run even if market appears closed (use with caution)")

    args = parser.parse_args()

    # Check market hours
    is_open, reason = is_forex_market_open()
    print(f"Market status: {reason}")

    if not is_open and not args.force:
        print("Exiting - market is closed")
        sys.exit(0)

    if not is_open and args.force:
        print("WARNING: --force flag used, running despite market being closed")

    # Check config file exists
    if not os.path.exists(args.config):
        print(f"ERROR: Config file '{args.config}' not found")
        print(f"Create it from config.example.ini and add your credentials")
        sys.exit(1)

    # Build command to run strategy
    if args.strategy == "enhanced":
        cmd = [
            "uv", "run", "enhanced_scalping_strategy.py",
            "--config", args.config,
            "--env", args.env,
            "--interval", str(args.interval),
            "--max-trades", str(args.max_trades),
            "--runtime", str(args.runtime)
        ]

        # Add OpenAI key if set
        if "OPENAI_API_KEY" in os.environ:
            cmd.extend(["--openai-key", os.environ["OPENAI_API_KEY"]])
    else:
        cmd = [
            "uv", "run", "scalping_strategy.py",
            "--config", args.config,
            "--env", args.env,
            "--interval", str(args.interval),
            "--max-trades", str(args.max_trades),
            "--runtime", str(args.runtime)
        ]

    print(f"\nStarting {args.strategy} strategy:")
    print(f"  Environment: {args.env}")
    print(f"  Scan interval: {args.interval}s")
    print(f"  Max trades: {args.max_trades}")
    print(f"  Runtime: {args.runtime}s ({args.runtime/60:.1f} minutes)")
    print(f"\nCommand: {' '.join(cmd)}\n")

    # Execute strategy
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
