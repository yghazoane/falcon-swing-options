# Falcon Market Compass

Build a polished responsive full-stack web application named "Falcon Market Intelligence" for educational market monitoring and historical analysis of the U.S. equity market. The user is a solo founder. This is a market intelligence dashboard, not a brokerage or trade execution app: do not provide personalized buy/sell/option-contract recommendations, order placement, or promises of predictive accuracy.

PRODUCT AND UX
- Arabic is the default language with full RTL layout; add a working Arabic/English language toggle (English LTR).
- Professional dark institutional-finance visual design, restrained blue/violet accents, excellent desktop and mobile responsiveness.
- Main dashboard for S&P 500 and Nasdaq 100, with clear distinction between index values and ETF proxies (SPY/QQQ). Never label proxy data as the index itself.
- Top bar: product name, market session/status, last refresh timestamp, data connection/status indicator, language toggle.
- Overview cards: S&P 500, Nasdaq 100, VIX, US 10Y yield, US 2Y yield, DXY. If live providers are not configured, show clearly marked demo/sample values and never imply they are live.
- Dashboard sections/tabs: Market Overview, Breadth & Sectors, Macro & Fed, News Intelligence, Historical Analysis, Data Sources / Settings.
- Charts for index/proxy history, volume, moving averages (20/50/200), RSI, MACD, volatility; use sensible loading/empty/error states.
- Breadth panels: advance/decline, up/down volume, new highs/lows, percentage above 50/200-day averages, sector performance. If no reliable feed exists, show unavailable rather than fabricated readings.
- Macro calendar and cards for CPI, Core CPI, PCE, Core PCE, PPI, NFP, unemployment, GDP, retail sales, ISM, Fed/FOMC decisions and minutes; show actual/forecast/previous and release timestamps only when sourced.
- Rates/markets context: Treasury 2Y/10Y and spread, DXY, VIX, oil, major global market context.
- News Intelligence: sourced headlines with publisher, published time, source link, category, importance and neutral impact summary. Do not invent headlines or sources.
- Historical Analysis: selectable date range and instrument; show historical chart and descriptive metrics. Include transparent methodology and a validation section for historical signal testing; avoid claims of guaranteed or 80% accuracy.
- Data Sources / Settings: provider status, timestamps, stale-data warnings, source attribution, and secure server-side environment variable configuration guidance. Never expose API keys in client code or browser UI.

IMPLEMENTATION
- Use the platform's supported full-stack TypeScript stack and reusable components.
- Build a clean modular architecture for market data, macro data, news, and analytics.
- Start with a functional dashboard using conspicuously labeled demo data only where necessary. Create provider adapter interfaces/placeholders so licensed APIs can be connected later; do not fabricate real-time feeds.
- Add a clear banner explaining that live and historical coverage depends on configured data providers, subscriptions, and data licensing.
- Include graceful empty states and robust error handling.
- Seed the UI with plausible illustrative demo values only if every such value is labeled "Demo / Illustrative" and cannot be mistaken for a live quote.
- Add a README or in-app setup guide listing required provider credentials as server-side secrets, without requesting secrets in chat.
Deliver a working first version with polished dashboard UI and responsive navigation.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/4dd15bb3-6282-4827-bf68-1fec3c89c919).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
