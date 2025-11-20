import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, Activity, Target, AlertCircle } from 'lucide-react'
import { formatCurrency, formatPercent, formatPips, cn } from '../lib/utils'
import { getMetrics, getEquityData } from '../lib/api'
import { useState, useEffect } from 'react'

function MetricCard({ title, value, delta, icon: Icon, trend }) {
  const isPositive = delta >= 0

  return (
    <div className="metric-card animate-slide-up">
      <div className="flex items-start justify-between mb-3">
        <div className="text-xs uppercase tracking-wide text-gray-400">{title}</div>
        {Icon && <Icon className="w-4 h-4 text-gray-500" />}
      </div>
      <div className="flex items-baseline gap-3">
        <div className="text-3xl font-mono font-bold tabular-nums">{value}</div>
        {delta !== undefined && (
          <div className={cn(
            'flex items-center gap-1 text-sm font-medium',
            isPositive ? 'text-bullish' : 'text-bearish'
          )}>
            {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            {formatPercent(Math.abs(delta))}
          </div>
        )}
      </div>
      {trend && (
        <div className="mt-3 h-12">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={isPositive ? '#10b981' : '#ef4444'}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function PerformanceAnalytics() {
  const [data, setData] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [metricsData, equityData] = await Promise.all([
          getMetrics(),
          getEquityData(30)
        ])
        setMetrics(metricsData)
        setData(equityData)
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading || !metrics) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-400">Loading...</div></div>
  }

  const sparklineData = Array.from({ length: 10 }, (_, i) => ({
    value: 10000 + (Math.random() - 0.4) * 1000
  }))

  return (
    <div className="space-y-6">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total P&L"
          value={formatCurrency(metrics.totalProfit)}
          delta={12.4}
          icon={TrendingUp}
          trend={sparklineData}
        />
        <MetricCard
          title="Win Rate"
          value={formatPercent(metrics.winRate, 1)}
          delta={2.1}
          icon={Target}
        />
        <MetricCard
          title="Profit Factor"
          value={metrics.profitFactor.toFixed(2)}
          delta={5.8}
          icon={Activity}
        />
        <MetricCard
          title="Max Drawdown"
          value={formatPercent(metrics.maxDrawdown, 1)}
          delta={metrics.maxDrawdown}
          icon={AlertCircle}
        />
      </div>

      {/* Equity Curve */}
      <div className="card animate-slide-up" style={{ animationDelay: '100ms' }}>
        <h2 className="text-lg font-bold mb-4">Equity Curve</h2>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.1} />
              <XAxis
                dataKey="date"
                stroke="#6b7280"
                tick={{ fill: '#9ca3af', fontSize: 12 }}
              />
              <YAxis
                stroke="#6b7280"
                tick={{ fill: '#9ca3af', fontSize: 12, fontFamily: 'IBM Plex Mono' }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#151a21',
                  border: '1px solid rgba(99, 102, 241, 0.2)',
                  borderRadius: '8px',
                  fontFamily: 'IBM Plex Mono',
                }}
                labelStyle={{ color: '#9ca3af' }}
                itemStyle={{ color: '#f9fafb' }}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="#6366f1"
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Daily P&L and Trade Count */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card animate-slide-up" style={{ animationDelay: '200ms' }}>
          <h2 className="text-lg font-bold mb-4">Daily P&L</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.1} />
                <XAxis
                  dataKey="date"
                  stroke="#6b7280"
                  tick={{ fill: '#9ca3af', fontSize: 12 }}
                />
                <YAxis
                  stroke="#6b7280"
                  tick={{ fill: '#9ca3af', fontSize: 12, fontFamily: 'IBM Plex Mono' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#151a21',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    borderRadius: '8px',
                    fontFamily: 'IBM Plex Mono',
                  }}
                />
                <Bar
                  dataKey="profit"
                  fill="#6366f1"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card animate-slide-up" style={{ animationDelay: '300ms' }}>
          <h2 className="text-lg font-bold mb-4">Trade Distribution</h2>
          <div className="space-y-4 mt-8">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-400">Winning Trades</span>
                <span className="font-mono text-bullish">{Math.round(metrics.totalTrades * metrics.winRate / 100)}</span>
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-bullish rounded-full transition-all duration-500"
                  style={{ width: `${metrics.winRate}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-400">Losing Trades</span>
                <span className="font-mono text-bearish">{metrics.totalTrades - Math.round(metrics.totalTrades * metrics.winRate / 100)}</span>
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-bearish rounded-full transition-all duration-500"
                  style={{ width: `${100 - metrics.winRate}%` }}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-6 pt-6 border-t border-gray-700/30">
              <div>
                <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">Avg Win</div>
                <div className="text-xl font-mono font-bold text-bullish">{formatPips(metrics.avgWin)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">Avg Loss</div>
                <div className="text-xl font-mono font-bold text-bearish">{formatPips(metrics.avgLoss)}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Metrics Table */}
      <div className="card animate-slide-up" style={{ animationDelay: '400ms' }}>
        <h2 className="text-lg font-bold mb-4">Performance Metrics</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th className="text-right">Value</th>
              <th className="text-right">Benchmark</th>
              <th className="text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Total Trades</td>
              <td className="number">{metrics.totalTrades}</td>
              <td className="number text-gray-500">200</td>
              <td className="text-right"><span className="text-bullish">✓</span></td>
            </tr>
            <tr>
              <td>Win Rate</td>
              <td className="number">{formatPercent(metrics.winRate, 1)}</td>
              <td className="number text-gray-500">60%</td>
              <td className="text-right"><span className="text-bullish">✓</span></td>
            </tr>
            <tr>
              <td>Profit Factor</td>
              <td className="number">{metrics.profitFactor.toFixed(2)}</td>
              <td className="number text-gray-500">1.5</td>
              <td className="text-right"><span className="text-bullish">✓</span></td>
            </tr>
            <tr>
              <td>Sharpe Ratio</td>
              <td className="number">{metrics.sharpeRatio.toFixed(2)}</td>
              <td className="number text-gray-500">1.0</td>
              <td className="text-right"><span className="text-bullish">✓</span></td>
            </tr>
            <tr>
              <td>Best Trade</td>
              <td className="number text-bullish">{formatCurrency(metrics.bestTrade)}</td>
              <td className="number text-gray-500">-</td>
              <td className="text-right">-</td>
            </tr>
            <tr>
              <td>Worst Trade</td>
              <td className="number text-bearish">{formatCurrency(metrics.worstTrade)}</td>
              <td className="number text-gray-500">-</td>
              <td className="text-right">-</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default PerformanceAnalytics
