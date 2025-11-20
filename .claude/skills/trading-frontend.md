# Trading Frontend Design Skill

Expert guidance for building professional, data-dense financial trading interfaces with clear hierarchy and purposeful aesthetics.

## Core Design Principles

### Typography
- **Primary font**: IBM Plex Mono (monospace for numbers, data tables, tickers)
- **Secondary font**: Inter Variable (UI labels, headings)
- **Scale**: Dramatic contrast - 48px headlines, 11px micro-labels, 14px body
- **Numbers**: Tabular figures, monospace, right-aligned in tables
- **Weight contrast**: 700 for gains/key metrics, 400 for labels, 300 for secondary data

### Color Palette (Dark Trading Theme)
**Background layers**:
- Base: `#0a0e14` (deep charcoal)
- Surface: `#151a21` (elevated panels)
- Overlay: `#1e2530` (modals, popovers)

**Accent colors**:
- Bullish/Profit: `#10b981` (emerald-500)
- Bearish/Loss: `#ef4444` (red-500)
- Warning: `#f59e0b` (amber-500)
- Neutral: `#6366f1` (indigo-500)
- Highlight: `#8b5cf6` (violet-500)

**Text hierarchy**:
- Primary: `#f9fafb` (gray-50)
- Secondary: `#9ca3af` (gray-400)
- Tertiary: `#6b7280` (gray-500)

### Motion & Reveals
**Page load orchestration**:
1. Header/nav: fade-in 200ms
2. Primary charts: slide-up 300ms, delay 100ms
3. Metrics cards: stagger 80ms each, slide-up 250ms
4. Side panels: slide-left 300ms, delay 200ms

**Interaction feedback**:
- Card hover: scale(1.01), border glow 150ms
- Button press: scale(0.98) 100ms
- Data updates: pulse 200ms on value change
- Alerts: slide-down 300ms with bounce easing

### Backgrounds & Atmosphere
**Dashboard base**:
- Radial gradient from `#0f172a` (top-left) to `#0a0e14` (bottom-right)
- Subtle noise texture overlay at 3% opacity
- Grid pattern (1px, #1e293b, 32px spacing) for depth

**Card backgrounds**:
- Semi-transparent `rgba(21, 26, 33, 0.6)` with backdrop-blur
- 1px border `rgba(99, 102, 241, 0.2)` (indigo glow on hover)

## Component Guidelines

### Data Visualization
**Charts**:
- Use Recharts or Lightweight Charts for performance
- Candlesticks: green wicks `#10b981`, red wicks `#ef4444`
- Grid lines: `#1e293b` at 10% opacity
- Crosshair: `#6366f1` with 50% opacity
- Tooltips: Dark surface with monospace numbers

**Metrics cards**:
- Title: 11px uppercase tracking-wide secondary color
- Value: 32px tabular mono, primary color
- Delta: 14px with ▲/▼ symbols, bullish/bearish colors
- Sparkline: Minimal 60px height, accent color stroke

### Tables
- Zebra striping: alternating `transparent` / `rgba(255,255,255,0.02)`
- Sticky headers with backdrop-blur
- Hover row: `rgba(99, 102, 241, 0.08)` background
- Cell padding: 12px vertical, 16px horizontal
- Right-align numbers, left-align text
- Sortable headers with subtle arrow indicators

### Forms & Configuration
- Input fields: Dark surface with subtle border, focus ring indigo
- Labels: 12px uppercase secondary color, 8px margin-bottom
- Sliders: Indigo track, white thumb with shadow
- Toggle switches: Indigo when active
- Dropdowns: Match card styling with smooth transitions
- Validation: Inline red-500 for errors, emerald-500 for success

### Navigation
- Sidebar: Fixed 240px, surface color, subtle right border
- Active route: Left border-l-4 indigo-500, background indigo-500/10
- Icons: 20px lucide-react, secondary color (primary on hover)
- Collapsed state: 64px width, icon-only

## Layout Patterns

### Dashboard Grid
```
┌─────────────────────────────────────────┐
│ Header (metrics summary)                │
├──────────┬──────────────────────────────┤
│          │                              │
│ Sidebar  │  Main Chart Area            │
│ (240px)  │  (Candlesticks/Indicators)  │
│          │                              │
│          ├──────────────┬───────────────┤
│          │ Strategy     │  Recent       │
│          │ Config       │  Trades       │
└──────────┴──────────────┴───────────────┘
```

### Responsive Breakpoints
- Desktop: 1440px+ (full layout)
- Laptop: 1024px (condensed sidebar)
- Tablet: 768px (drawer sidebar)
- Mobile: < 768px (stack vertically)

## Tech Stack Setup

**Dependencies**:
```bash
uv add vite react react-dom
uv add -D @vitejs/plugin-react tailwindcss postcss autoprefixer
uv add @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react
uv add recharts date-fns
```

**shadcn/ui components to install**:
```bash
npx shadcn@latest init
npx shadcn@latest add card button input label select slider switch table tabs tooltip
```

**Vite config for fast HMR**:
```js
// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  resolve: { alias: { '@': '/src' } }
})
```

## Anti-Patterns to Avoid

- Generic Inter everywhere (use IBM Plex Mono for data)
- Evenly-distributed colors (commit to dark theme with sharp accents)
- Static page loads (orchestrate reveals)
- Flat white backgrounds (layer gradients, add depth)
- Cluttered charts (minimize chrome, maximize data-ink ratio)
- Inconsistent number formatting (always tabular, 2 decimals for currency, 4 for FX)

## Performance Requirements

- Initial load: < 1.5s
- Chart re-render: < 16ms (60fps)
- WebSocket updates: < 100ms latency
- Bundle size: < 500kb gzipped
- Lighthouse score: > 90 performance

## Accessibility

- WCAG AA contrast ratios (4.5:1 for text)
- Keyboard navigation for all controls
- ARIA labels for data visualizations
- Focus indicators (2px indigo-500 ring)
- Screen reader announcements for trade updates
