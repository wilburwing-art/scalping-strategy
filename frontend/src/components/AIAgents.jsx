import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'
import { Brain, TrendingUp, Shield, Activity, AlertTriangle, CheckCircle, XCircle, Minus } from 'lucide-react'
import { formatPercent, cn } from '../lib/utils'
import { getAISignals, getAgentStatus } from '../lib/api'
import { useState, useEffect } from 'react'

function ConfidenceBadge({ confidence }) {
  let color = 'text-gray-400'
  let bgColor = 'bg-gray-800'
  let label = 'Low'

  if (confidence >= 0.7) {
    color = 'text-bullish'
    bgColor = 'bg-bullish/10'
    label = 'High'
  } else if (confidence >= 0.5) {
    color = 'text-yellow-400'
    bgColor = 'bg-yellow-400/10'
    label = 'Medium'
  }

  return (
    <div className={cn('inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium', bgColor, color)}>
      <span>{label}</span>
      <span className="font-mono">{formatPercent(confidence, 0)}</span>
    </div>
  )
}

function ActionBadge({ action }) {
  const actionMap = {
    'BUY': { icon: TrendingUp, color: 'text-bullish', bg: 'bg-bullish/10' },
    'SELL': { icon: TrendingUp, color: 'text-bearish', bg: 'bg-bearish/10', rotate: 'rotate-180' },
    'HOLD': { icon: Minus, color: 'text-gray-400', bg: 'bg-gray-800' }
  }

  const config = actionMap[action] || actionMap['HOLD']
  const Icon = config.icon

  return (
    <div className={cn('inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold', config.bg, config.color)}>
      <Icon className={cn('w-4 h-4', config.rotate)} />
      {action}
    </div>
  )
}

function AgentCard({ name, score, icon: Icon, details, status = 'active' }) {
  const isGood = score >= 0.6

  return (
    <div className="card animate-slide-up">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            isGood ? 'bg-bullish/10' : 'bg-gray-800'
          )}>
            <Icon className={cn('w-5 h-5', isGood ? 'text-bullish' : 'text-gray-400')} />
          </div>
          <div>
            <h3 className="font-bold text-sm">{name}</h3>
            <div className="text-xs text-gray-400 mt-0.5">
              {status === 'active' ? '● Active' : '○ Inactive'}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-mono font-bold">{formatPercent(score, 0)}</div>
          <div className="text-xs text-gray-400 mt-0.5">Confidence</div>
        </div>
      </div>

      {details && (
        <div className="space-y-2 text-sm">
          {Object.entries(details).map(([key, value]) => (
            <div key={key} className="flex justify-between items-center">
              <span className="text-gray-400">{key}</span>
              <span className="font-mono text-gray-200">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SignalCard({ signal }) {
  return (
    <div className="card animate-slide-up hover:border-neutral/50 transition-colors cursor-pointer">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold font-mono">{signal.instrument}</h3>
            <ActionBadge action={signal.action} />
          </div>
          <div className="text-xs text-gray-400 mt-1">{signal.timestamp}</div>
        </div>
        <ConfidenceBadge confidence={signal.confidence} />
      </div>

      {signal.entry_price && (
        <div className="grid grid-cols-3 gap-4 mb-4 pb-4 border-b border-gray-700/30">
          <div>
            <div className="text-xs text-gray-400 mb-1">Entry</div>
            <div className="font-mono text-sm font-bold">{signal.entry_price.toFixed(5)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Stop Loss</div>
            <div className="font-mono text-sm font-bold text-bearish">{signal.stop_loss.toFixed(5)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Take Profit</div>
            <div className="font-mono text-sm font-bold text-bullish">{signal.take_profit.toFixed(5)}</div>
          </div>
        </div>
      )}

      {signal.reasoning && (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-wide text-gray-400">Reasoning</div>
          <div className="text-sm text-gray-300 leading-relaxed bg-background-surface/50 p-3 rounded-lg">
            {signal.reasoning}
          </div>
        </div>
      )}

      {signal.agents && (
        <div className="mt-4 pt-4 border-t border-gray-700/30">
          <div className="text-xs uppercase tracking-wide text-gray-400 mb-3">Agent Breakdown</div>
          <div className="space-y-2">
            {signal.agents.map((agent) => (
              <div key={agent.name} className="flex items-center justify-between text-sm">
                <span className="text-gray-300">{agent.name}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all',
                        agent.score >= 0.6 ? 'bg-bullish' : 'bg-gray-600'
                      )}
                      style={{ width: `${agent.score * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs w-12 text-right">{formatPercent(agent.score, 0)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function AIAgents() {
  const [signals, setSignals] = useState([])
  const [agentStatus, setAgentStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const [signalsData, statusData] = await Promise.all([
          getAISignals(),
          getAgentStatus()
        ])
        setSignals(signalsData || [])
        setAgentStatus(statusData)
        setError(null)
      } catch (error) {
        console.error('Error fetching AI data:', error)
        setError(error.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-3">
          <Brain className="w-12 h-12 text-neutral animate-pulse mx-auto" />
          <div className="text-gray-400">Loading AI agents...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-3">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto" />
          <div className="text-gray-400">Error loading AI data</div>
          <div className="text-sm text-gray-500">{error}</div>
        </div>
      </div>
    )
  }

  const agentData = [
    {
      name: 'Market Intelligence',
      score: agentStatus?.market_intelligence?.confidence || 0,
      icon: Activity,
      details: agentStatus?.market_intelligence ? {
        'Sentiment': agentStatus.market_intelligence.sentiment || 'N/A',
        'News Impact': agentStatus.market_intelligence.news_impact || 'N/A',
      } : null
    },
    {
      name: 'Technical Analysis',
      score: agentStatus?.technical_analysis?.confidence || 0,
      icon: TrendingUp,
      details: agentStatus?.technical_analysis ? {
        'Trend': agentStatus.technical_analysis.trend || 'N/A',
        'Strength': agentStatus.technical_analysis.strength || 'N/A',
      } : null
    },
    {
      name: 'Risk Assessment',
      score: agentStatus?.risk_assessment?.confidence || 0,
      icon: Shield,
      details: agentStatus?.risk_assessment ? {
        'Risk Level': agentStatus.risk_assessment.risk_level || 'N/A',
        'Position Size': agentStatus.risk_assessment.position_size || 'N/A',
      } : null
    }
  ]

  const radarData = agentData.map(agent => ({
    agent: agent.name.split(' ')[0],
    score: agent.score * 100
  }))

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="metric-card animate-slide-up">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs uppercase tracking-wide text-gray-400">Active Signals</div>
            <Activity className="w-4 h-4 text-gray-500" />
          </div>
          <div className="text-3xl font-mono font-bold">{signals.length}</div>
        </div>

        <div className="metric-card animate-slide-up" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs uppercase tracking-wide text-gray-400">Avg Confidence</div>
            <Brain className="w-4 h-4 text-gray-500" />
          </div>
          <div className="text-3xl font-mono font-bold">
            {signals.length > 0
              ? formatPercent(signals.reduce((sum, s) => sum + s.confidence, 0) / signals.length, 0)
              : '0%'
            }
          </div>
        </div>

        <div className="metric-card animate-slide-up" style={{ animationDelay: '200ms' }}>
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs uppercase tracking-wide text-gray-400">High Confidence</div>
            <CheckCircle className="w-4 h-4 text-gray-500" />
          </div>
          <div className="text-3xl font-mono font-bold text-bullish">
            {signals.filter(s => s.confidence >= 0.7).length}
          </div>
        </div>
      </div>

      {/* Agent Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card animate-slide-up" style={{ animationDelay: '300ms' }}>
          <h2 className="text-lg font-bold mb-4">Agent Performance</h2>
          <div className="h-80 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#1e293b" />
                <PolarAngleAxis
                  dataKey="agent"
                  tick={{ fill: '#9ca3af', fontSize: 12 }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fill: '#9ca3af', fontSize: 10 }}
                />
                <Radar
                  name="Confidence"
                  dataKey="score"
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.5}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-4 animate-slide-up" style={{ animationDelay: '400ms' }}>
          {agentData.map((agent, idx) => (
            <AgentCard key={idx} {...agent} />
          ))}
        </div>
      </div>

      {/* Recent Signals */}
      <div className="animate-slide-up" style={{ animationDelay: '500ms' }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Recent Signals</h2>
          <div className="text-sm text-gray-400">
            Last updated: {new Date().toLocaleTimeString()}
          </div>
        </div>

        {signals.length === 0 ? (
          <div className="card text-center py-12">
            <XCircle className="w-12 h-12 text-gray-500 mx-auto mb-3" />
            <div className="text-gray-400">No signals available</div>
            <div className="text-sm text-gray-500 mt-1">AI agents are analyzing markets...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {signals.map((signal, idx) => (
              <SignalCard key={idx} signal={signal} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default AIAgents
