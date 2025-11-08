# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Forex Scalping Strategy Project

This is a Python-based automated forex scalping trading strategy that uses the OANDA v20 REST API for executing trades. The strategy performs technical analysis on currency pairs and executes short-term trades based on indicators like RSI, moving averages, and ATR.

## Project Structure

- `scalping-strategy.py`: Main trading strategy implementation containing the `ScalpingStrategy` class
- `v20.conf`: Configuration file for OANDA API credentials (not included in repo - user must create)
- `scalping_strategy.log`: Log file generated during strategy execution

## Core Architecture

### ScalpingStrategy Class
Main class implementing the trading algorithm with key methods:

- **Configuration Management**: `_load_config()` loads OANDA credentials from config file
- **Data Analysis**: `calculate_indicators()` computes RSI, ATR, moving averages from price data
- **Opportunity Detection**: `scan_for_opportunities()` analyzes instruments for trading criteria
- **Risk Management**: `calculate_position_size()` determines trade size based on account balance and risk parameters
- **Trade Execution**: `execute_trade()` places market orders with stop loss and take profit
- **Trade Monitoring**: `monitor_active_trades()` tracks open positions and P&L

### Trading Logic Flow
1. Scan major forex pairs for volatility and volume criteria
2. Calculate technical indicators (RSI, ATR, moving averages)
3. Check news impact (placeholder implementation)
4. Determine entry/exit levels and position sizing
5. Execute trades with automatic stop loss and take profit
6. Monitor active trades and manage positions

## Common Commands

### Running the Strategy
```bash
# Run with default settings (practice environment, 300s intervals)
uv run scalping-strategy.py

# Run with custom parameters
uv run scalping-strategy.py --config v20.conf --env practice --interval 120 --max-trades 5 --runtime 7200

# Run in live environment (requires live OANDA account)
uv run scalping-strategy.py --env live
```

### Dependencies
The script requires these Python packages:
- `pandas`, `numpy`: Data analysis and calculations
- `requests`: HTTP requests
- `v20`: OANDA v20 API client
- `configparser`: Configuration file parsing
- `dateutil`: Date parsing utilities

Install dependencies:
```bash
uv add pandas numpy requests v20-python python-dateutil
```

## Configuration Requirements

### OANDA Configuration File (v20.conf)
Must create a configuration file with OANDA API credentials:

```ini
[practice]
hostname = api-fxpractice.oanda.com
token = YOUR_PRACTICE_TOKEN
account_id = YOUR_PRACTICE_ACCOUNT_ID

[live]
hostname = api-fxtrade.oanda.com  
token = YOUR_LIVE_TOKEN
account_id = YOUR_LIVE_ACCOUNT_ID
```

**Security Note**: The v20.conf file contains API credentials and should never be committed to version control.

## Strategy Parameters

Key configurable parameters in the `ScalpingStrategy` class:
- `volume_threshold`: Minimum volume for trade consideration (default: 1000)
- `volatility_window`: ATR calculation period (default: 14)
- `rsi_period`: RSI calculation period (default: 14)
- `risk_percent`: Risk per trade as % of account (default: 1.0%)
- `reward_risk_ratio`: Take profit to stop loss ratio (default: 1.5)

## Risk Management Features

- **Position Sizing**: Calculated based on account balance and risk percentage
- **Stop Loss**: Automatically set at 1.5x ATR from entry price
- **Take Profit**: Set at stop loss distance × reward/risk ratio
- **Maximum Concurrent Trades**: Configurable limit (default: 3)
- **News Impact Filtering**: Placeholder for avoiding high-impact news periods

## Logging and Monitoring

All strategy activities are logged to both console and `scalping_strategy.log` file, including:
- Trade executions and closures
- Technical indicator calculations
- Error handling and API responses
- Performance metrics and account status

# Python & environment rules

## Core philosophy
- Use `uv` for everything: project init, dependency management, script execution, tools, and Python installation management.
- Avoid `python -m venv`, `pip install`, `pipx`, Poetry, and Conda unless explicitly requested.

## Creating projects
- **New project in current dir:** `uv init` (or `uv init --python 3.X` for specific version)
- **New project in subdirectory:** `uv init myproj`
- **Application project:** `uv init --app --package ...`
- **Library project:** `uv init --lib --package ...`
- **Specify Python version:** `uv init --python 3.X` (common pattern across commands)

## Working with scripts
- **Run a script in isolated environment:** `uv run myscript.py`
- **Run script with extra dependencies:** `uv run myscript.py ... --with click`
- **Add script metadata for inline dependencies:** `uv init --script myscript.py` (sets up PEP 723 metadata)
- **Add dependency to script metadata:** `uv add --script myscript.py click`

## Managing dependencies
- **Add dependencies:** `uv add requests` (can list multiple: `uv add pkg1 pkg2`)
- **Remove dependencies:** `uv remove requests` (also removes transitive deps automatically)
- **Add dev dependencies:** `uv add --dev pytest`
- **Add from requirements.txt:** `uv add -r requirements.txt`
- **View dependency tree:** `uv tree`
- **Upgrade dependencies:** `uv lock --upgrade`
- **Run installed package:** `uv run pytest`

## Python version management
- **List available Python versions:** `uv python list`
- **Install specific Python:** `uv python install 3.13`
- **Upgrade managed Pythons:** `uv python upgrade`
- **Pin Python version:** `uv python pin 3.X`
- **Run with specific Python:** `uv run python` or `uv run --python 3.X python`

## Tools
- **One-off tool execution:** `uvx ty` (ephemeral, doesn't install)
- **Run tool from package:** `uvx textual-demo --from textual`
- **Install tool globally:** `uv tool install ruff` (makes it available on PATH)
- **Install tool with dependencies:** `uv tool install --with dep ...`
- **Install editable tool:** `uv tool install -e .`
- **List installed tools:** `uv tool list`
- **Upgrade all tools:** `uv tool upgrade --all`

## Project lifecycle
- **Check version:** `uv version`
- **Bump major version:** `... --bump major` (0.8.3 → 1.0.0)
- **Bump minor version:** `... --bump minor` (1.0.0 → 1.1.0)
- **Bump patch version:** `... --bump alpha` (1.1.0+1 → 1.1.0a2)
- **Make alpha version:** `... --bump alpha` (1.1.0+1 → 1.1.0a2)
- **Make beta version:** `... --bump beta` (can be "beta" or "rc")
- **Make stable version:** `... --bump stable` (1.1.0 → stable)
- **Build project:** `uv build`
- **Publish project:** `uv publish`

## Meta commands
- **Get help:** `uv help python pin`
- **Check uv version:** `uv self version`
- **Update uv:** `uv self update`

## Formatting
- **Format code with Ruff:** `uv format` (uses Ruff from uv's CLI)

## Default command patterns
- **Add deps:** `uv add pkg1 pkg2`
- **Run code:** `uv run -m module` or `uv run script.py`
- **One-off tool:** `uvx <tool>`
- **Pin/sync:** `uv lock` / `uv sync --frozen`

# Response Preferences
- Minimize use of Emojis, only use when words won't suffice

## Never take credit or attribute work
**NEVER add attribution lines, credit markers, or "generated by" statements to any work.**

When creating commits, PRs, documentation, or any deliverable:
- **DON'T add**: "Generated with Claude Code", "Co-Authored-By: Claude", or any similar attribution
- **DON'T include**: Footer signatures, tool credits, or AI-generated markers
- **DO present work**: As if written directly by the user
- **Exception**: Only add attribution if the user explicitly requests it

**Examples of banned patterns:**
- Commit message footers: "🤖 Generated with [Claude Code]..."
- PR descriptions: "Generated with Claude Code" or similar
- Code comments: "# Generated by AI" or "# Claude Code"
- Documentation footers: "This document was created with..."

**Rationale**: The user owns the work. Attribution to tools is unnecessary and unprofessional in most contexts.

## No fake data policy
**NEVER generate placeholder, mock, or fake data to make code execute.**

When something fails (API call, query, data fetch):
- **Let it fail visibly** — this reveals the actual problem
- **Show the real error** — don't mask failures with synthetic data
- **Stop and report** — explain what failed and why

**Examples of banned behavior:**
- Query returns empty → DON'T create fake rows to test downstream code
- API fails → DON'T return mock responses to keep execution going
- File missing → DON'T generate placeholder content

**Correct approach:**
1. Run the code as-is
2. If it fails, report the failure
3. Diagnose the root cause
4. Fix the actual issue

**Exception:** Test fixtures and unit test mocks are fine when explicitly building tests.

## “Glazing” terms & patterns to avoid (banlist)
**Sycophancy & fluff**  
- “Great question!”, “Happy to help!”, “Of course!”, “Absolutely!”, “Delighted to assist”, "You're absolutely right!", "Perfect!"

**Identity disclaimers**  
- “As an AI…”, “As a large language model…”

**Hedging without value**  
- “It seems like…”, “I think…”, “Probably…”

**Lecturey disclaimers**  
- “Please note…”, “It should be noted…”, “Keep in mind…”, “Kindly…”

**Buzzword glaze**  
- “robust”, “seamless”, “scalable”, “state-of-the-art”, “next-gen”, “world-class”, “frictionless”, “intuitive”, “leverage”, “utilize”

**Process filler**  
- “Let’s dive in…”, “At a high level…”, “In conclusion…”, “Moving forward…”

**Empty admonitions**  
- “Always follow best practices.”, “Be sure to check the docs.”

**Placeholder nags**  
- “Remember to replace `<YOUR_API_KEY>`…”

**Condescending minimizers**  
- “Just…”, “Simply…”, “Obviously…”

**Non-answers**  
- “It depends.” *(alone)* → map `if A → X / if B → Y`.

**Over-apology**  
- “I apologize for the inconvenience/confusion.”

**Enforcement**: If any banned phrasing appears, strip and rewrite before returning.

# Code Hygiene & Cleanup

## Remove obsolete code immediately
**NEVER keep legacy code, files, or cruft "just in case" or for backwards compatibility.**

When refactoring or replacing functionality:
1. **Implement the new solution** completely
2. **Test that it works** (run it, verify output)
3. **Delete the old code immediately** - no deprecation period, no commenting out, no renaming to `.old`
4. **Remove unused imports, functions, and files** as soon as they're no longer referenced

**Examples of what to remove:**
- Old files replaced by new ones (e.g., USAGE.md → README.md)
- Deprecated functions/classes after migration is complete
- Unused imports after refactoring
- Commented-out code blocks
- Backup files created during refactoring
- Dead code paths that are no longer reachable

**When NOT to remove:**
- Code that is currently in use (even if planned for deprecation)
- Test fixtures and test utilities (unless tests are also removed)
- Documentation that provides historical context (e.g., design decisions)

**Process:**
1. Make the change
2. Verify it works
3. Identify what's now obsolete
4. Remove it in the same session
5. Commit once with both addition and removal

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
