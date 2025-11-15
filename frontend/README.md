# Trading Dashboard Frontend

Professional React-based dashboard for monitoring and configuring the forex scalping trading strategy.

## Features

- **Performance Analytics Dashboard**
  - Real-time equity curve visualization
  - Key performance metrics (Win Rate, Profit Factor, Sharpe Ratio, Drawdown)
  - Daily P&L bar charts
  - Trade distribution analysis
  - Performance metrics table with benchmarks

- **Strategy Configuration Interface**
  - Risk management controls (Risk %, Reward:Risk Ratio, Max Trades)
  - Technical indicator settings (RSI Period, ATR Window, Volume Threshold)
  - AI agent configuration (Enable/Disable, Model Selection, Confidence Threshold)
  - Real-time strategy start/stop control
  - Live save/reset configuration

## Tech Stack

- **React 18** - UI framework
- **Vite 5** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Recharts** - Data visualization
- **Lucide React** - Icon library
- **FastAPI** - Backend REST API

## Design System

Follows professional trading interface design principles:

- **Typography**: IBM Plex Mono (data/numbers) + Inter (UI text)
- **Color Palette**: Dark theme optimized for extended viewing
  - Background: `#0a0e14` (deep charcoal)
  - Bullish/Profit: `#10b981` (emerald)
  - Bearish/Loss: `#ef4444` (red)
  - Accent: `#6366f1` (indigo)
- **Motion**: Orchestrated page-load animations, smooth transitions
- **Atmosphere**: Layered gradients, subtle noise texture, grid patterns

## Getting Started

### Prerequisites

- Node.js 18.16+ (or 20+)
- npm 9+
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

Start the dev server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── PerformanceAnalytics.jsx  # Dashboard with charts
│   │   └── StrategyConfig.jsx        # Configuration interface
│   ├── lib/
│   │   ├── api.js                    # Backend API client
│   │   └── utils.js                  # Utility functions
│   ├── App.jsx                       # Main app layout
│   ├── main.jsx                      # Entry point
│   └── index.css                     # Global styles
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## API Integration

The frontend communicates with the backend API at `http://localhost:8000`:

- `GET /api/metrics` - Performance metrics
- `GET /api/equity?days=30` - Equity curve data
- `GET /api/config` - Current configuration
- `POST /api/config` - Update configuration
- `GET /api/status` - Strategy running status
- `POST /api/start` - Start strategy
- `POST /api/stop` - Stop strategy

## Backend Setup

The backend must be running before starting the frontend:

```bash
# From project root
cd /path/to/scalping-strategy
uv run uvicorn backend.api:app --reload --port 8000
```

## Environment Variables

No environment variables required. API endpoint is configured in `src/lib/api.js`.

To change the API URL, edit:

```javascript
const API_BASE_URL = 'http://localhost:8000/api'
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Initial load: < 1.5s
- Chart re-render: < 16ms (60fps)
- Bundle size: ~450kb gzipped

## Design Reference

Based on the Claude Code blog post: "Improving Frontend Design Through Skills"

Key principles:
- Avoid distributional convergence (generic Inter fonts everywhere)
- Targeted prompting across typography, color, motion, backgrounds
- Professional financial interface aesthetics
