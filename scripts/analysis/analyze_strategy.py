"""
Strategy Analysis Tool
Analyzes trading logs to identify patterns and suggest refinements
"""

import re
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import statistics


class StrategyAnalyzer:
    def __init__(self, log_path="scalping_strategy.log"):
        self.log_path = Path(log_path)
        self.signals = []
        self.skipped_reasons = []
        self.agent_costs = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "calls": 0})

    def parse_logs(self):
        """Parse all relevant data from logs"""
        if not self.log_path.exists():
            print(f"Log file not found: {self.log_path}")
            return

        with open(self.log_path, 'r') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]

            # Parse agent recommendations
            if "Agent recommendation:" in line:
                match = re.search(r'(\w+_\w+) - Agent recommendation: (\w+) \(confidence: ([\d.]+)\)', line)
                if match:
                    instrument = match.group(1)
                    action = match.group(2)
                    confidence = float(match.group(3))

                    # Get reasoning
                    reasoning = ""
                    if i + 1 < len(lines) and "Reasoning:" in lines[i + 1]:
                        reasoning_match = re.search(r'Reasoning: (.+)$', lines[i + 1])
                        if reasoning_match:
                            reasoning = reasoning_match.group(1).strip()

                    self.signals.append({
                        "instrument": instrument,
                        "action": action,
                        "confidence": confidence,
                        "reasoning": reasoning
                    })

            # Parse skip reasons
            if "skipping" in line.lower():
                if "Max trades" in line:
                    self.skipped_reasons.append("max_trades_reached")
                elif "confidence" in line.lower() and "below threshold" in line.lower():
                    self.skipped_reasons.append("low_confidence")
                elif "HOLD signal" in line:
                    self.skipped_reasons.append("hold_signal")

            # Parse cost data
            if "AICostTracker" in line and "tokens" in line:
                match = re.search(r'(\w+): (\d+) \+ (\d+) = (\d+) tokens \(\$([\d.]+)\)', line)
                if match:
                    agent = match.group(1)
                    total = int(match.group(4))
                    cost = float(match.group(5))

                    self.agent_costs[agent]["tokens"] += total
                    self.agent_costs[agent]["cost"] += cost
                    self.agent_costs[agent]["calls"] += 1

            i += 1

    def analyze_signal_distribution(self):
        """Analyze signal types and confidence patterns"""
        print("\n" + "="*80)
        print("SIGNAL DISTRIBUTION ANALYSIS")
        print("="*80)

        if not self.signals:
            print("No signals found in logs")
            return

        # Action distribution
        actions = Counter(s["action"] for s in self.signals)
        print(f"\nTotal Signals: {len(self.signals)}")
        print(f"\nAction Breakdown:")
        for action, count in actions.most_common():
            pct = (count / len(self.signals)) * 100
            print(f"  {action:8s}: {count:3d} ({pct:5.1f}%)")

        # Confidence analysis by action
        print(f"\nConfidence Scores by Action:")
        for action in ["BUY", "SELL", "HOLD"]:
            action_signals = [s for s in self.signals if s["action"] == action]
            if action_signals:
                confidences = [s["confidence"] for s in action_signals]
                avg_conf = statistics.mean(confidences)
                min_conf = min(confidences)
                max_conf = max(confidences)
                print(f"  {action:8s}: avg={avg_conf:.3f}, min={min_conf:.3f}, max={max_conf:.3f}")

        # High confidence signals
        high_conf = [s for s in self.signals if s["confidence"] >= 0.7]
        med_conf = [s for s in self.signals if 0.6 <= s["confidence"] < 0.7]
        low_conf = [s for s in self.signals if s["confidence"] < 0.6]

        print(f"\nConfidence Tiers:")
        print(f"  High (≥0.70): {len(high_conf):3d} ({len(high_conf)/len(self.signals)*100:5.1f}%)")
        print(f"  Med (0.60-0.69): {len(med_conf):3d} ({len(med_conf)/len(self.signals)*100:5.1f}%)")
        print(f"  Low (<0.60): {len(low_conf):3d} ({len(low_conf)/len(self.signals)*100:5.1f}%)")

        # Most common instruments
        instruments = Counter(s["instrument"] for s in self.signals)
        print(f"\nTop 10 Most Analyzed Pairs:")
        for inst, count in instruments.most_common(10):
            print(f"  {inst:10s}: {count:3d} signals")

    def analyze_agent_performance(self):
        """Analyze individual agent costs and efficiency"""
        print("\n" + "="*80)
        print("AGENT PERFORMANCE & COST ANALYSIS")
        print("="*80)

        if not self.agent_costs:
            print("No agent cost data found")
            return

        total_cost = sum(a["cost"] for a in self.agent_costs.values())
        total_tokens = sum(a["tokens"] for a in self.agent_costs.values())
        total_calls = sum(a["calls"] for a in self.agent_costs.values())

        print(f"\nOverall Statistics:")
        print(f"  Total Cost: ${total_cost:.4f}")
        print(f"  Total Tokens: {total_tokens:,}")
        print(f"  Total API Calls: {total_calls:,}")
        print(f"  Avg Cost per Call: ${total_cost/total_calls:.6f}")
        print(f"  Avg Tokens per Call: {total_tokens/total_calls:.1f}")

        print(f"\nAgent Breakdown:")
        print(f"  {'Agent':<20} {'Calls':>8} {'Tokens':>12} {'Cost':>10} {'$/Call':>10} {'Tok/Call':>10}")
        print(f"  {'-'*20} {'-'*8} {'-'*12} {'-'*10} {'-'*10} {'-'*10}")

        for agent in ["MarketIntelligence", "TechnicalAnalysis", "RiskAssessment", "Coordinator"]:
            if agent in self.agent_costs:
                data = self.agent_costs[agent]
                avg_cost = data["cost"] / data["calls"] if data["calls"] > 0 else 0
                avg_tokens = data["tokens"] / data["calls"] if data["calls"] > 0 else 0
                pct_cost = (data["cost"] / total_cost * 100) if total_cost > 0 else 0

                print(f"  {agent:<20} {data['calls']:8,} {data['tokens']:12,} ${data['cost']:9.4f} ${avg_cost:9.6f} {avg_tokens:10.1f}")
                print(f"  {'':>20} ({pct_cost:5.1f}% of total cost)")

        # Cost projections
        print(f"\nCost Projections (assuming 5-minute intervals during market hours):")
        checks_per_day = 288  # 24 hours * 12 checks/hour
        checks_per_month = checks_per_day * 30
        cost_per_check = total_cost / (total_calls / 4) if total_calls > 0 else 0  # Divide by 4 agents

        print(f"  Per Check (all 4 agents): ${cost_per_check:.6f}")
        print(f"  Daily (24h): ${cost_per_check * checks_per_day:.2f}")
        print(f"  Monthly: ${cost_per_check * checks_per_month:.2f}")
        print(f"  Annual: ${cost_per_check * checks_per_month * 12:.2f}")

    def analyze_skipped_trades(self):
        """Analyze why trades were skipped"""
        print("\n" + "="*80)
        print("SKIPPED TRADE ANALYSIS")
        print("="*80)

        if not self.skipped_reasons:
            print("No skipped trades found")
            return

        reasons = Counter(self.skipped_reasons)
        print(f"\nTotal Skipped: {len(self.skipped_reasons)}")
        print(f"\nSkip Reasons:")
        for reason, count in reasons.most_common():
            pct = (count / len(self.skipped_reasons)) * 100
            print(f"  {reason:25s}: {count:3d} ({pct:5.1f}%)")

    def generate_recommendations(self):
        """Generate strategy refinement recommendations"""
        print("\n" + "="*80)
        print("REFINEMENT RECOMMENDATIONS")
        print("="*80)

        recommendations = []

        # Analyze signal quality
        if self.signals:
            actions = Counter(s["action"] for s in self.signals)
            hold_pct = (actions.get("HOLD", 0) / len(self.signals)) * 100

            if hold_pct > 40:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Signal Quality",
                    "issue": f"{hold_pct:.1f}% of signals are HOLD",
                    "recommendation": "Lower confidence threshold from 0.6 to 0.55 to capture more actionable signals"
                })

            # Check confidence distribution
            high_conf = sum(1 for s in self.signals if s["confidence"] >= 0.7)
            high_conf_pct = (high_conf / len(self.signals)) * 100

            if high_conf_pct < 30:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "Confidence Tuning",
                    "issue": f"Only {high_conf_pct:.1f}% of signals are high confidence (≥0.7)",
                    "recommendation": "Review agent prompts to improve decision quality or adjust threshold to 0.65"
                })

        # Analyze cost efficiency
        if self.agent_costs:
            coordinator_cost = self.agent_costs.get("Coordinator", {}).get("cost", 0)
            total_cost = sum(a["cost"] for a in self.agent_costs.values())

            if coordinator_cost / total_cost > 0.4:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "Cost Optimization",
                    "issue": "Coordinator agent accounts for >40% of total cost",
                    "recommendation": "Simplify coordinator prompt or use cheaper model (gpt-4o-mini) for coordinator only"
                })

        # Analyze skip patterns
        if self.skipped_reasons:
            reasons = Counter(self.skipped_reasons)
            max_trades_pct = (reasons.get("max_trades_reached", 0) / len(self.skipped_reasons)) * 100

            if max_trades_pct > 50:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Trade Execution",
                    "issue": f"{max_trades_pct:.1f}% of skips due to max trades (3) reached",
                    "recommendation": "Increase max_trades to 5 to capture more opportunities, or implement priority queue"
                })

        # General recommendations
        recommendations.append({
            "priority": "LOW",
            "category": "Performance",
            "issue": "Running all agents in series adds latency",
            "recommendation": "Agents already run in parallel - confirm this is working correctly"
        })

        recommendations.append({
            "priority": "LOW",
            "category": "Data Quality",
            "issue": "No entry price captured in many signals",
            "recommendation": "Ensure price data is logged at time of analysis for better tracking"
        })

        # Print recommendations
        print("\n")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. [{rec['priority']}] {rec['category']}")
            print(f"   Issue: {rec['issue']}")
            print(f"   Recommendation: {rec['recommendation']}")
            print()

    def run_full_analysis(self):
        """Run complete analysis suite"""
        print("\n" + "="*80)
        print("FOREX SCALPING STRATEGY - LOG ANALYSIS")
        print("="*80)
        print(f"Log file: {self.log_path}")
        print(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.parse_logs()
        self.analyze_signal_distribution()
        self.analyze_agent_performance()
        self.analyze_skipped_trades()
        self.generate_recommendations()

        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80 + "\n")


if __name__ == "__main__":
    analyzer = StrategyAnalyzer()
    analyzer.run_full_analysis()
