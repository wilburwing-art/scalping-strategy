"""
Log parser to extract trading data from strategy logs
Converts log entries into structured data for the dashboard API
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from collections import defaultdict


class LogParser:
    """Parse trading strategy logs and extract structured data"""

    def __init__(self, log_path: str = "scalping_strategy.log"):
        self.log_path = Path(log_path)
        self.signals = []
        self.cost_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "api_calls": 0,
            "estimated_cost": 0.0,
            "by_agent": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "calls": 0})
        }

    def parse_ai_signals(self, limit: int = 50) -> List[Dict]:
        """Extract AI agent recommendations from logs"""
        signals = []

        if not self.log_path.exists():
            return signals

        with open(self.log_path, 'r') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for agent recommendation pattern
            if "Agent recommendation:" in line:
                try:
                    # Extract timestamp
                    timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()

                    # Extract instrument, action, confidence
                    # Format: "EUR_USD - Agent recommendation: BUY (confidence: 0.75)"
                    rec_match = re.search(r'(\w+_\w+) - Agent recommendation: (\w+) \(confidence: ([\d.]+)\)', line)
                    if rec_match:
                        instrument = rec_match.group(1)
                        action = rec_match.group(2)
                        confidence = float(rec_match.group(3))

                        # Get reasoning from next line
                        reasoning = ""
                        if i + 1 < len(lines) and "Reasoning:" in lines[i + 1]:
                            reasoning_match = re.search(r'Reasoning: (.+)$', lines[i + 1])
                            if reasoning_match:
                                reasoning = reasoning_match.group(1).strip()

                        # Look for price data by searching backwards
                        price = None
                        for j in range(max(0, i - 10), i):
                            if f"Analyzing {instrument} at" in lines[j]:
                                price_match = re.search(r'at ([\d.]+)', lines[j])
                                if price_match:
                                    price = float(price_match.group(1))
                                    break

                        signal = {
                            "instrument": instrument,
                            "action": action,
                            "confidence": confidence,
                            "entry_price": price,
                            "timestamp": timestamp,
                            "reasoning": reasoning,
                            "agents": []  # Will be populated with individual agent scores
                        }

                        signals.append(signal)

                except Exception as e:
                    print(f"Error parsing signal at line {i}: {e}")

            i += 1

        # Return most recent signals
        return signals[-limit:] if signals else []

    def parse_cost_stats(self) -> Dict:
        """Extract token usage and cost statistics"""
        stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "api_calls": 0,
            "estimated_cost": 0.0,
            "by_agent": {}
        }

        if not self.log_path.exists():
            return stats

        agent_stats = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "calls": 0})

        with open(self.log_path, 'r') as f:
            for line in f:
                # Look for cost tracker entries
                # Format: "AICostTracker - INFO - MarketIntelligence: 29 + 91 = 120 tokens ($0.0001)"
                if "AICostTracker" in line and "tokens" in line:
                    match = re.search(r'(\w+): (\d+) \+ (\d+) = (\d+) tokens \(\$([\d.]+)\)', line)
                    if match:
                        agent = match.group(1)
                        prompt = int(match.group(2))
                        completion = int(match.group(3))
                        total = int(match.group(4))
                        cost = float(match.group(5))

                        stats["total_tokens"] += total
                        stats["prompt_tokens"] += prompt
                        stats["completion_tokens"] += completion
                        stats["api_calls"] += 1
                        stats["estimated_cost"] += cost

                        agent_stats[agent]["tokens"] += total
                        agent_stats[agent]["cost"] += cost
                        agent_stats[agent]["calls"] += 1

        stats["by_agent"] = dict(agent_stats)
        return stats

    def get_latest_data(self) -> Dict:
        """Get all parsed data in one call"""
        return {
            "signals": self.parse_ai_signals(limit=50),
            "cost_stats": self.parse_cost_stats()
        }


if __name__ == "__main__":
    # Test the parser
    parser = LogParser()
    data = parser.get_latest_data()

    print(f"Found {len(data['signals'])} signals")
    print(f"Total cost: ${data['cost_stats']['estimated_cost']:.4f}")
    print(f"Total tokens: {data['cost_stats']['total_tokens']:,}")

    if data['signals']:
        print("\nMost recent signal:")
        latest = data['signals'][-1]
        print(f"  {latest['instrument']}: {latest['action']} (confidence: {latest['confidence']:.2f})")
        print(f"  Price: {latest.get('entry_price', 'N/A')}")
        print(f"  Reasoning: {latest['reasoning'][:100]}...")
