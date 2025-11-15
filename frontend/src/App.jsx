import { useState } from 'react'
import { Activity, Settings, TrendingUp, BarChart3 } from 'lucide-react'
import PerformanceAnalytics from './components/PerformanceAnalytics'
import StrategyConfig from './components/StrategyConfig'
import { cn } from './lib/utils'

function App() {
  const [activeTab, setActiveTab] = useState('analytics')

  const navItems = [
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'config', label: 'Config', icon: Settings },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="h-16 border-b border-gray-700/30 backdrop-blur-md bg-background-surface/50 sticky top-0 z-50 animate-fade-in">
        <div className="h-full px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-neutral" />
            <h1 className="text-xl font-bold">Forex Scalping Dashboard</h1>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-bullish animate-pulse" />
              <span className="text-sm text-gray-400">Live</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-400">Account: </span>
              <span className="font-mono">Practice</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside className="w-64 border-r border-gray-700/30 bg-background-surface/30 backdrop-blur-sm animate-slide-left" style={{ animationDelay: '200ms' }}>
          <nav className="p-4">
            <div className="space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all duration-150',
                      activeTab === item.id
                        ? 'bg-neutral/10 text-gray-50 border-l-4 border-neutral'
                        : 'text-gray-400 hover:text-gray-50 hover:bg-white/5'
                    )}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </button>
                )
              })}
            </div>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-auto">
          {activeTab === 'analytics' && <PerformanceAnalytics />}
          {activeTab === 'config' && <StrategyConfig />}
        </main>
      </div>
    </div>
  )
}

export default App
