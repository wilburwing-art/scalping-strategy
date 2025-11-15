import { useState, useEffect } from 'react'
import { Save, RotateCcw, PlayCircle, PauseCircle, AlertTriangle } from 'lucide-react'
import { cn } from '../lib/utils'
import { getConfig, updateConfig as apiUpdateConfig, getStatus, startStrategy, stopStrategy } from '../lib/api'

function ConfigInput({ label, value, onChange, type = 'number', min, max, step, unit, description }) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <label className="text-sm font-medium text-gray-300">{label}</label>
        {unit && <span className="text-xs text-gray-500">{unit}</span>}
      </div>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        min={min}
        max={max}
        step={step}
        className="w-full px-4 py-2 bg-background-overlay border border-gray-700/50 rounded-lg font-mono text-sm
                   focus:outline-none focus:ring-2 focus:ring-neutral focus:border-transparent
                   transition-all duration-150"
      />
      {description && <p className="text-xs text-gray-500">{description}</p>}
    </div>
  )
}

function ConfigSlider({ label, value, onChange, min, max, step, unit, description }) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <label className="text-sm font-medium text-gray-300">{label}</label>
        <span className="text-sm font-mono text-gray-400">{value}{unit}</span>
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                   [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                   [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-neutral [&::-webkit-slider-thumb]:cursor-pointer
                   [&::-webkit-slider-thumb]:shadow-lg
                   [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:rounded-full
                   [&::-moz-range-thumb]:bg-neutral [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:border-0"
      />
      {description && <p className="text-xs text-gray-500">{description}</p>}
    </div>
  )
}

function ConfigToggle({ label, value, onChange, description }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <div className="text-sm font-medium text-gray-300 mb-1">{label}</div>
        {description && <p className="text-xs text-gray-500">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!value)}
        className={cn(
          'relative w-12 h-6 rounded-full transition-colors duration-200',
          value ? 'bg-neutral' : 'bg-gray-700'
        )}
      >
        <div
          className={cn(
            'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-lg transition-transform duration-200',
            value && 'transform translate-x-6'
          )}
        />
      </button>
    </div>
  )
}

function ConfigSelect({ label, value, onChange, options, description }) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-300">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2 bg-background-overlay border border-gray-700/50 rounded-lg font-mono text-sm
                   focus:outline-none focus:ring-2 focus:ring-neutral focus:border-transparent
                   transition-all duration-150 cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {description && <p className="text-xs text-gray-500">{description}</p>}
    </div>
  )
}

function StrategyConfig() {
  const [config, setConfig] = useState(null)
  const [originalConfig, setOriginalConfig] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [isSaved, setIsSaved] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [configData, statusData] = await Promise.all([
          getConfig(),
          getStatus()
        ])
        setConfig(configData)
        setOriginalConfig(configData)
        setIsRunning(statusData.isRunning)
      } catch (error) {
        console.error('Error fetching config:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const updateConfigField = (key, value) => {
    setConfig({ ...config, [key]: value })
    setIsSaved(false)
  }

  const handleSave = async () => {
    try {
      const updated = await apiUpdateConfig(config)
      setConfig(updated)
      setOriginalConfig(updated)
      setIsSaved(true)
    } catch (error) {
      console.error('Error saving config:', error)
      alert('Failed to save configuration')
    }
  }

  const handleReset = () => {
    setConfig(originalConfig)
    setIsSaved(false)
  }

  const handleToggleStrategy = async () => {
    try {
      if (isRunning) {
        await stopStrategy()
        setIsRunning(false)
      } else {
        await startStrategy()
        setIsRunning(true)
      }
    } catch (error) {
      console.error('Error toggling strategy:', error)
      alert(`Failed to ${isRunning ? 'stop' : 'start'} strategy`)
    }
  }

  if (loading || !config) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-400">Loading...</div></div>
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Control Panel */}
      <div className="card animate-slide-up">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">Strategy Control</h2>
            <p className="text-sm text-gray-400 mt-1">
              Status: <span className={cn('font-mono', isRunning ? 'text-bullish' : 'text-gray-500')}>
                {isRunning ? 'Running' : 'Stopped'}
              </span>
            </p>
          </div>
          <button
            onClick={handleToggleStrategy}
            className={cn(
              'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all duration-150',
              isRunning
                ? 'bg-bearish/20 text-bearish hover:bg-bearish/30 border border-bearish/50'
                : 'bg-bullish/20 text-bullish hover:bg-bullish/30 border border-bullish/50'
            )}
          >
            {isRunning ? (
              <>
                <PauseCircle className="w-5 h-5" />
                Stop Strategy
              </>
            ) : (
              <>
                <PlayCircle className="w-5 h-5" />
                Start Strategy
              </>
            )}
          </button>
        </div>
      </div>

      {/* Risk Management */}
      <div className="card animate-slide-up" style={{ animationDelay: '100ms' }}>
        <h2 className="text-lg font-bold mb-6">Risk Management</h2>
        <div className="space-y-6">
          <ConfigSlider
            label="Risk Per Trade"
            value={config.riskPercent}
            onChange={(v) => updateConfigField('riskPercent', v)}
            min={0.1}
            max={5.0}
            step={0.1}
            unit="%"
            description="Percentage of account balance risked per trade"
          />
          <ConfigSlider
            label="Reward:Risk Ratio"
            value={config.rewardRiskRatio}
            onChange={(v) => updateConfigField('rewardRiskRatio', v)}
            min={1.0}
            max={5.0}
            step={0.1}
            unit=":1"
            description="Target profit relative to stop loss"
          />
          <ConfigInput
            label="Max Concurrent Trades"
            value={config.maxTrades}
            onChange={(v) => updateConfigField('maxTrades', parseInt(v))}
            min={1}
            max={10}
            step={1}
            description="Maximum number of trades open at the same time"
          />
        </div>
      </div>

      {/* Technical Indicators */}
      <div className="card animate-slide-up" style={{ animationDelay: '200ms' }}>
        <h2 className="text-lg font-bold mb-6">Technical Indicators</h2>
        <div className="space-y-6">
          <ConfigInput
            label="RSI Period"
            value={config.rsiPeriod}
            onChange={(v) => updateConfigField('rsiPeriod', parseInt(v))}
            min={5}
            max={30}
            step={1}
            description="Number of periods for RSI calculation"
          />
          <ConfigInput
            label="Volatility Window"
            value={config.volatilityWindow}
            onChange={(v) => updateConfigField('volatilityWindow', parseInt(v))}
            min={5}
            max={50}
            step={1}
            description="ATR calculation period for volatility measurement"
          />
          <ConfigInput
            label="Volume Threshold"
            value={config.volumeThreshold}
            onChange={(v) => updateConfigField('volumeThreshold', parseInt(v))}
            min={100}
            max={10000}
            step={100}
            description="Minimum volume required to consider trading opportunity"
          />
        </div>
      </div>

      {/* AI Agents Configuration */}
      <div className="card animate-slide-up" style={{ animationDelay: '300ms' }}>
        <h2 className="text-lg font-bold mb-6">AI Agent Settings</h2>
        <div className="space-y-6">
          <ConfigToggle
            label="Enable AI Agents"
            value={config.useAgents}
            onChange={(v) => updateConfigField('useAgents', v)}
            description="Use multi-agent system for enhanced market analysis"
          />
          {config.useAgents && (
            <>
              <ConfigSelect
                label="Agent Model"
                value={config.agentModel}
                onChange={(v) => updateConfigField('agentModel', v)}
                options={[
                  { value: 'gpt-4o', label: 'GPT-4o (Recommended)' },
                  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Lower Cost)' },
                  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
                ]}
                description="OpenAI model used for agent intelligence"
              />
              <ConfigSlider
                label="Minimum Confidence"
                value={config.minConfidence}
                onChange={(v) => updateConfigField('minConfidence', v)}
                min={0.3}
                max={0.9}
                step={0.05}
                unit=""
                description="Minimum agent confidence score to execute trade (0.3-0.9)"
              />
              <div className="mt-4 p-4 bg-warning/10 border border-warning/30 rounded-lg flex gap-3">
                <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
                <div className="text-sm text-gray-300">
                  <p className="font-medium text-warning mb-1">API Key Required</p>
                  <p>Ensure OPENAI_API_KEY environment variable is set before enabling AI agents.</p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Execution Settings */}
      <div className="card animate-slide-up" style={{ animationDelay: '400ms' }}>
        <h2 className="text-lg font-bold mb-6">Execution Settings</h2>
        <div className="space-y-6">
          <ConfigInput
            label="Scan Interval"
            value={config.interval}
            onChange={(v) => updateConfigField('interval', parseInt(v))}
            min={60}
            max={3600}
            step={60}
            unit="seconds"
            description="Time between market scans for opportunities"
          />
        </div>
      </div>

      {/* Save/Reset Actions */}
      <div className="flex gap-4 animate-slide-up" style={{ animationDelay: '500ms' }}>
        <button
          onClick={handleSave}
          disabled={isSaved}
          className={cn(
            'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all duration-150',
            isSaved
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
              : 'bg-neutral text-white hover:bg-neutral/90'
          )}
        >
          <Save className="w-5 h-5" />
          {isSaved ? 'Saved' : 'Save Configuration'}
        </button>
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-6 py-3 rounded-lg font-medium bg-background-overlay
                     text-gray-300 hover:bg-gray-700 border border-gray-700 transition-all duration-150"
        >
          <RotateCcw className="w-5 h-5" />
          Reset to Defaults
        </button>
      </div>
    </div>
  )
}

export default StrategyConfig
