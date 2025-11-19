#!/usr/bin/env python3
"""
Convenience wrapper to analyze strategy logs
Usage: uv run analyze_logs.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.analysis.analyze_strategy import StrategyAnalyzer

if __name__ == "__main__":
    analyzer = StrategyAnalyzer()
    analyzer.run_full_analysis()
