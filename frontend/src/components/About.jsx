import { Brain, TrendingUp, Shield, Activity, Zap, BarChart3, AlertTriangle, CheckCircle2, Code, DollarSign } from 'lucide-react'

function FeatureCard({ icon: Icon, title, description }) {
  return (
    <div className="card animate-slide-up hover:border-neutral/50 transition-colors">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-lg bg-neutral/10 flex items-center justify-center flex-shrink-0">
          <Icon className="w-6 h-6 text-neutral" />
        </div>
        <div>
          <h3 className="font-bold mb-2">{title}</h3>
          <p className="text-sm text-gray-400 leading-relaxed">{description}</p>
        </div>
      </div>
    </div>
  )
}

function StatItem({ label, value, color = 'text-gray-200' }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-700/30 last:border-0">
      <span className="text-sm text-gray-400">{label}</span>
      <span className={`font-mono font-medium ${color}`}>{value}</span>
    </div>
  )
}

function About() {
  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div className="animate-slide-up">
        <h1 className="text-4xl font-bold mb-3">Forex Scalping Strategy</h1>
        <p className="text-xl text-gray-400">
          AI-powered automated trading system combining technical analysis with multi-agent intelligence
        </p>
      </div>

      {/* Overview */}
      <div className="card animate-slide-up" style={{ animationDelay: '100ms' }}>
        <h2 className="text-2xl font-bold mb-4">What This Is</h2>
        <div className="space-y-4 text-gray-300 leading-relaxed">
          <p>
            This is a Python-based automated forex scalping strategy that integrates traditional technical analysis
            with a sophisticated multi-agent AI system powered by <span className="font-mono text-neutral">pydantic_ai</span> and
            OpenAI's GPT models.
          </p>
          <p>
            The system analyzes forex markets in real-time, generates high-confidence trading signals, and provides
            comprehensive reasoning for every decision. This dashboard visualizes the AI's thought process, tracks
            performance metrics, and monitors costs.
          </p>
        </div>
      </div>

      {/* Multi-Agent Architecture */}
      <div className="animate-slide-up" style={{ animationDelay: '200ms' }}>
        <h2 className="text-2xl font-bold mb-4">Multi-Agent Intelligence System</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <FeatureCard
            icon={Activity}
            title="Market Intelligence Agent"
            description="Analyzes real-time news, sentiment, economic events, and geopolitical factors. Provides context about market conditions and identifies potential catalysts."
          />
          <FeatureCard
            icon={TrendingUp}
            title="Technical Analysis Agent"
            description="Performs multi-timeframe analysis with indicator confluence and pattern recognition. Evaluates RSI, ATR, moving averages, and trend strength."
          />
          <FeatureCard
            icon={Shield}
            title="Risk Assessment Agent"
            description="Handles position sizing, correlation analysis, and portfolio risk management. Calculates optimal trade sizes and risk/reward ratios."
          />
          <FeatureCard
            icon={Brain}
            title="Coordinator Agent"
            description="Orchestrates all agents, resolves conflicts, and makes final trading decisions. Weighs each agent's input and ensures consensus before executing trades."
          />
        </div>
      </div>

      {/* Decision Framework */}
      <div className="card animate-slide-up" style={{ animationDelay: '300ms' }}>
        <h2 className="text-2xl font-bold mb-4">Decision Framework</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-bold mb-3 text-neutral">Agent Weighting</h3>
            <div className="space-y-1">
              <StatItem label="Market Intelligence" value="30%" color="text-blue-400" />
              <StatItem label="Technical Analysis" value="40%" color="text-violet-400" />
              <StatItem label="Risk Assessment" value="30%" color="text-emerald-400" />
            </div>
          </div>
          <div>
            <h3 className="font-bold mb-3 text-neutral">Trading Parameters</h3>
            <div className="space-y-1">
              <StatItem label="Min Confidence Threshold" value="0.60" />
              <StatItem label="Max Concurrent Trades" value="3" />
              <StatItem label="Risk Per Trade" value="1.0%" />
              <StatItem label="Reward/Risk Ratio" value="1.5:1" />
            </div>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="card animate-slide-up" style={{ animationDelay: '400ms' }}>
        <h2 className="text-2xl font-bold mb-4">How It Works</h2>
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-neutral/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-sm font-bold text-neutral">1</span>
            </div>
            <div>
              <h4 className="font-bold mb-1">Market Scanning</h4>
              <p className="text-sm text-gray-400">
                Strategy scans major forex pairs every 5 minutes, filtering for volume and volatility criteria.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-neutral/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-sm font-bold text-neutral">2</span>
            </div>
            <div>
              <h4 className="font-bold mb-1">AI Agent Analysis</h4>
              <p className="text-sm text-gray-400">
                Three specialized agents analyze each opportunity in parallel, providing independent assessments within seconds.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-neutral/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-sm font-bold text-neutral">3</span>
            </div>
            <div>
              <h4 className="font-bold mb-1">Coordinator Decision</h4>
              <p className="text-sm text-gray-400">
                Coordinator agent weighs all inputs, checks for conflicts, and generates a final recommendation with confidence score.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-neutral/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-sm font-bold text-neutral">4</span>
            </div>
            <div>
              <h4 className="font-bold mb-1">Trade Execution</h4>
              <p className="text-sm text-gray-400">
                If confidence exceeds threshold and risk checks pass, trade is executed via OANDA API with automatic stop loss and take profit.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-neutral/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-sm font-bold text-neutral">5</span>
            </div>
            <div>
              <h4 className="font-bold mb-1">Monitoring & Logging</h4>
              <p className="text-sm text-gray-400">
                All signals, reasoning, and token usage are logged. Dashboard parses logs to provide real-time visualization.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Dashboard Features */}
      <div className="animate-slide-up" style={{ animationDelay: '500ms' }}>
        <h2 className="text-2xl font-bold mb-4">Dashboard Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FeatureCard
            icon={BarChart3}
            title="Performance Analytics"
            description="Track equity curves, win rates, profit factors, and trade statistics over time."
          />
          <FeatureCard
            icon={Brain}
            title="AI Agent Insights"
            description="View real-time agent recommendations, confidence scores, and detailed reasoning for each signal."
          />
          <FeatureCard
            icon={DollarSign}
            title="Cost Monitoring"
            description="Track OpenAI API usage, token consumption, and estimated monthly costs by agent."
          />
        </div>
      </div>

      {/* Technical Stack */}
      <div className="card animate-slide-up" style={{ animationDelay: '600ms' }}>
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <Code className="w-6 h-6 text-neutral" />
          Technical Stack
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-bold mb-3 text-neutral">Backend</h3>
            <div className="space-y-1">
              <StatItem label="Strategy Engine" value="Python 3.11+" />
              <StatItem label="AI Framework" value="pydantic_ai" />
              <StatItem label="LLM Provider" value="OpenAI GPT-4o" />
              <StatItem label="Broker API" value="OANDA v20" />
              <StatItem label="API Server" value="FastAPI + Uvicorn" />
            </div>
          </div>
          <div>
            <h3 className="font-bold mb-3 text-neutral">Frontend</h3>
            <div className="space-y-1">
              <StatItem label="Framework" value="React 18 + Vite" />
              <StatItem label="Styling" value="Tailwind CSS" />
              <StatItem label="Charts" value="Recharts" />
              <StatItem label="UI Components" value="shadcn/ui" />
              <StatItem label="Build Tool" value="Vite HMR" />
            </div>
          </div>
        </div>
      </div>

      {/* Cost Analysis */}
      <div className="card animate-slide-up" style={{ animationDelay: '700ms' }}>
        <h2 className="text-2xl font-bold mb-4">Cost Analysis</h2>
        <div className="space-y-4 text-gray-300">
          <p className="text-sm leading-relaxed">
            Running on OpenAI's free tier with GPT-4o-mini, the system costs approximately <span className="font-mono text-bullish">$1-2/month</span> for
            5-minute interval checks during market hours. Each analysis uses ~1,200 tokens across 4 agents.
          </p>
          <div className="bg-background-surface/50 rounded-lg p-4 border border-gray-700/30">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-gray-400 mb-1">Per Check</div>
                <div className="font-mono font-bold">~$0.0001</div>
              </div>
              <div>
                <div className="text-gray-400 mb-1">Daily (24h)</div>
                <div className="font-mono font-bold">~$0.03</div>
              </div>
              <div>
                <div className="text-gray-400 mb-1">Monthly Estimate</div>
                <div className="font-mono font-bold text-bullish">~$1.00</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Disclosure */}
      <div className="card animate-slide-up bg-yellow-500/5 border-yellow-500/20" style={{ animationDelay: '800ms' }}>
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-yellow-400 flex-shrink-0 mt-1" />
          <div>
            <h2 className="text-xl font-bold mb-3 text-yellow-400">Risk Disclosure</h2>
            <div className="space-y-2 text-sm text-gray-300 leading-relaxed">
              <p>
                <strong>Forex trading involves substantial risk of loss.</strong> This automated trading system is
                provided for educational and research purposes. Past performance does not guarantee future results.
              </p>
              <p>
                AI-generated signals may contain errors or biases. Always practice proper risk management, use stop
                losses, and never risk more than you can afford to lose.
              </p>
              <p>
                Test thoroughly in a practice/paper trading environment before deploying with real capital.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="card animate-slide-up bg-neutral/5 border-neutral/20" style={{ animationDelay: '900ms' }}>
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-6 h-6 text-neutral flex-shrink-0 mt-1" />
          <div>
            <h3 className="font-bold mb-2 text-neutral">Current Status</h3>
            <p className="text-sm text-gray-400">
              System is running in <span className="font-mono text-gray-200">practice mode</span> with OANDA's
              fxPractice environment. All trades use simulated capital. Data on this dashboard is parsed from
              live strategy logs and updates in real-time.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default About
