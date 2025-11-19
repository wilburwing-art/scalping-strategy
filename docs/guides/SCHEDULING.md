# Scheduling Guide: Running Strategy During Market Hours

## Overview

This guide explains how to schedule the trading strategy to run automatically during forex market hours using macOS launchd.

**Forex Market Hours:** Sunday 5:00 PM ET - Friday 5:00 PM ET (24/5)

## Quick Start

### 1. Make the scheduler script executable

```bash
chmod +x run_during_market_hours.py
```

### 2. Create logs directory

```bash
mkdir -p logs
```

### 3. Test the scheduler manually

```bash
# Test with practice account
./run_during_market_hours.py --strategy enhanced --env practice

# Test if market hours check works (will exit if market closed)
./run_during_market_hours.py --strategy enhanced --env practice --runtime 60
```

### 4. Install launchd service

```bash
# Copy plist to LaunchAgents directory
cp com.trading.scalping.plist ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.trading.scalping.plist

# Check status
launchctl list | grep com.trading.scalping
```

### 5. View logs

```bash
# Scheduler logs
tail -f logs/scheduler.log

# Strategy logs
tail -f enhanced_scalping_strategy.log

# Error logs
tail -f logs/scheduler.error.log
```

## Configuration

### Scheduler Script Options

The `run_during_market_hours.py` script accepts these arguments:

```bash
--strategy {basic,enhanced}   # Which strategy to run (default: enhanced)
--config PATH                 # Config file (default: v20.conf)
--env {practice,live}         # Trading environment (default: practice)
--interval SECONDS            # Scan interval (default: 300)
--max-trades N                # Max concurrent trades (default: 3)
--runtime SECONDS             # How long to run (default: 3600 = 1 hour)
--force                       # Force run even if market closed
```

### Customizing the Schedule

Edit `com.trading.scalping.plist` to customize:

**Schedule frequency:**
The default runs every 6 hours during market hours. To run more frequently, add more `StartCalendarInterval` entries:

```xml
<!-- Example: Run every 2 hours on Monday -->
<dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>0</integer>
</dict>
<dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>2</integer>
</dict>
<dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>4</integer>
</dict>
<!-- ... and so on -->
```

**Strategy parameters:**
Modify the `ProgramArguments` array:

```xml
<key>ProgramArguments</key>
<array>
    <string>/Users/wilburpyn/repos/scalping-strategy/run_during_market_hours.py</string>
    <string>--strategy</string>
    <string>enhanced</string>
    <string>--env</string>
    <string>practice</string>  <!-- Change to 'live' for real trading -->
    <string>--runtime</string>
    <string>7200</string>       <!-- 2 hours instead of 1 -->
</array>
```

**Environment variables:**
Add API keys and other env vars:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/Users/wilburpyn/.local/bin</string>
    <key>OPENAI_API_KEY</key>
    <string>sk-your-key-here</string>
</dict>
```

## Managing the Service

### Start/Stop

```bash
# Stop the service
launchctl unload ~/Library/LaunchAgents/com.trading.scalping.plist

# Start the service
launchctl load ~/Library/LaunchAgents/com.trading.scalping.plist

# Restart after editing plist
launchctl unload ~/Library/LaunchAgents/com.trading.scalping.plist
cp com.trading.scalping.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.trading.scalping.plist
```

### Check Status

```bash
# Check if service is loaded
launchctl list | grep com.trading.scalping

# View recent log entries
tail -20 logs/scheduler.log

# Check for errors
tail -20 logs/scheduler.error.log

# Monitor in real-time
tail -f logs/scheduler.log
```

### Manual Testing

```bash
# Test scheduler (will check market hours)
./run_during_market_hours.py --env practice --runtime 60

# Force run regardless of market hours
./run_during_market_hours.py --env practice --runtime 60 --force

# Run basic strategy instead of enhanced
./run_during_market_hours.py --strategy basic --env practice
```

## Security Considerations

### Storing API Keys

**Option 1: Environment variables in plist (less secure)**
```xml
<key>EnvironmentVariables</key>
<dict>
    <key>OPENAI_API_KEY</key>
    <string>sk-...</string>
</dict>
```

**Option 2: macOS Keychain (more secure)**
```bash
# Store in keychain
security add-generic-password -a "$USER" -s "OPENAI_API_KEY" -w "sk-..."

# Retrieve in script
security find-generic-password -a "$USER" -s "OPENAI_API_KEY" -w
```

**Option 3: Separate env file (not in git)**
Create `.env` file:
```bash
export OPENAI_API_KEY="sk-..."
export OANDA_TOKEN="..."
```

Source it in the script or plist.

### Protecting v20.conf

```bash
# Ensure config file has restrictive permissions
chmod 600 v20.conf

# Never commit to git
echo "v20.conf" >> .gitignore
```

## Monitoring and Alerts

### Check Strategy Performance

```bash
# View today's trading activity
grep "$(date +%Y-%m-%d)" enhanced_scalping_strategy.log

# Count trades executed today
grep "$(date +%Y-%m-%d)" enhanced_scalping_strategy.log | grep "Trade executed" | wc -l

# Check for errors
grep "ERROR" enhanced_scalping_strategy.log | tail -20
```

### Set Up Notifications

Enable email/SMS alerts in `v20.conf`:

```ini
[alerts]
email_enabled = true
smtp_username = your.email@gmail.com
smtp_password = your-app-password
to_emails = alerts@example.com

sms_enabled = true
twilio_account_sid = ACxxxxx
twilio_auth_token = xxxxx
twilio_to_numbers = +1234567890
```

## Troubleshooting

### Service not running

```bash
# Check if loaded
launchctl list | grep com.trading.scalping

# Check system logs
log show --predicate 'subsystem == "com.apple.launchd"' --last 1h | grep scalping

# Verify plist syntax
plutil -lint ~/Library/LaunchAgents/com.trading.scalping.plist
```

### Script fails to execute

```bash
# Check permissions
ls -l run_during_market_hours.py

# Make executable
chmod +x run_during_market_hours.py

# Test manually
./run_during_market_hours.py --force --runtime 10
```

### No logs generated

```bash
# Ensure logs directory exists
mkdir -p logs

# Check write permissions
touch logs/test.log
rm logs/test.log

# Verify paths in plist match actual filesystem
grep StandardOutPath ~/Library/LaunchAgents/com.trading.scalping.plist
```

### Market hours check failing

```bash
# Test market hours detection
python3 -c "
from run_during_market_hours import is_forex_market_open
print(is_forex_market_open())
"

# Force run to bypass check
./run_during_market_hours.py --force
```

## Switching to Live Trading

**CAUTION:** Only switch to live trading after extensive testing in practice mode.

1. Update plist to use live environment:
```xml
<string>--env</string>
<string>live</string>
```

2. Reload service:
```bash
launchctl unload ~/Library/LaunchAgents/com.trading.scalping.plist
cp com.trading.scalping.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.trading.scalping.plist
```

3. Monitor closely:
```bash
tail -f enhanced_scalping_strategy.log
```

## Advanced: Cron Alternative

If you prefer cron over launchd:

```bash
# Edit crontab
crontab -e

# Add entry (runs every hour during market hours)
0 * * * * cd /Users/wilburpyn/repos/scalping-strategy && ./run_during_market_hours.py --runtime 3600 >> logs/cron.log 2>&1
```

Note: launchd is preferred on macOS as it's more reliable and handles system sleep/wake better.
