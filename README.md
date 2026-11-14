# Falcon Swing Options

Private educational Streamlit workspace for studying U.S. market structure, historical price data, options concepts and hypothetical scenarios. Research and paper analysis only; no broker connection or order execution.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and replace the sample value with a strong, unique password. Never commit that file or share the password. Then start the app:

```bash
streamlit run app.py
```

## Private access and deployment

The main app and every Streamlit multipage entry point must call the shared `require_password()` gate. The app fails closed if no password is configured.

Configure one of the following in the hosting provider's private settings:

- Environment variable: `FALCON_APP_PASSWORD`
- Streamlit Secrets: `app_password = "your-strong-unique-password"`

Do not put passwords, API keys or private credentials in GitHub, source files, screenshots or chat messages. If a password was ever committed, rotate it in the hosting provider immediately; deleting it from the latest commit alone does not invalidate the exposed value.

A Render Blueprint is included in `render.yaml`. Connect the repository in Render and set `FALCON_APP_PASSWORD` as a private environment variable during setup. Free instances may sleep and have cold-start delays; check the host's current limits. For Streamlit Community Cloud, add `app_password` through the app's private Secrets settings.

## Application pages

- Main dashboard: broad-market context, S&P 500 and Nasdaq-100 index readings, ETF proxies, sector funds, macro proxy symbols, and Federal Reserve headlines.
- Options concepts: glossary of calls, puts, strike, expiry, premium, Greeks, implied volatility, open interest and bid/ask.
- Federal Reserve news: official Fed headlines with a rule-based, descriptive impact classification. The classification is not a forecast.
- Options lab and scenario simulation: hypothetical European-option calculations using a simplified Black–Scholes model and user-entered assumptions.
- Advanced technical analysis: EMA 20/50/200, RSI, ATR, confirmed swing structure, Fibonacci reference levels and multi-timeframe comparison.
- Options-chain snapshot: provider-reported Yahoo Finance calls/puts when available, including bid/ask, volume, open interest and implied volatility; locally calculated model Greeks are clearly distinct from exchange-published Greeks.
- Scenario simulator: hypothetical changes in underlying price, time and assumed volatility; not a contract-selection tool.
- Historical validation: time-ordered research tests on the underlying asset, not historical option contracts.

## Market-regime methodology

The broad-market descriptive regime uses the direct S&P 500 (`^GSPC`) and Nasdaq-100 (`^NDX`) index series when available. SPY and QQQ are used only as fallbacks if the corresponding direct index data is unavailable; an index and its ETF proxy are never counted twice as independent confirmations. The selected benchmark readings are compared with EMA50 and contextualized with VIX. VIX thresholds are rough descriptive conventions, not predictive boundaries. Missing one of the two benchmark readings results in an unresolved regime rather than a confident classification.

Sector ETF performance is compared with SPY as a relative-strength reference. It is not a complete market-breadth measure. Treasury, dollar, gold and oil tickers are market proxies, not official macroeconomic releases.

## Data limitations

Yahoo Finance through `yfinance` is an unofficial data adapter. It does not guarantee real-time quotes, complete coverage, quote timestamps, stable availability or executable prices. The app's five-minute cache is a local retrieval cache, not a promise that provider data is five minutes old or fresh. Each page should be interpreted using its displayed source and latest available bar/retrieval time.

The options-chain page may return provider snapshots. The retrieval timestamp is not the exchange quote timestamp. Bid/ask, volume, open interest and implied volatility may be delayed, stale, incomplete or unavailable. The app does not label these as guaranteed real-time data.

Greeks and theoretical values are calculated locally with a simplified Black–Scholes model. They are not official exchange Greeks and omit important contract-specific features such as early exercise, dividends, settlement details, volatility skew/surface, fees and execution costs. The scenario simulator uses assumptions and does not represent an executable quote.

The four-hour view is derived from hourly bars rather than supplied as a native provider interval. The volume-by-price display is an approximation from candle-level data, not trade-level volume-at-price.

Federal Reserve headlines are fetched from the Fed's public news feed and classified using simple text rules. This is not a complete economic calendar and does not measure the market's priced-in expectations or causal impact.

## Testing

GitHub Actions compiles the Python application and runs the unit tests on pull requests to `main` and pushes to `main`.

```bash
python -m compileall -q app.py falcon pages tests
pytest -q
```

## Scope

This is an educational research and hypothetical-simulation project. Outputs describe observations and assumptions; they are not probabilities, predictions, recommendations or instructions to trade. No real-money trading, broker integration or order execution is supported.
