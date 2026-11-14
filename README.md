# Falcon Swing Options

Private, educational Streamlit workspace for studying U.S. market data, technical structure and options terminology. Paper analysis only.

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

## Optional hosted deployment

A Render Blueprint is included in `render.yaml`. To deploy it, connect this GitHub repository in Render and create the service from the Blueprint. During setup, set the private `FALCON_APP_PASSWORD` environment variable to a strong, unique password. Do not put the password in GitHub or in the YAML file. The service is configured for a free instance, which may sleep when idle and may have cold-start delays. Review the host's current limits before relying on it.

For Streamlit Community Cloud or another host, add `app_password` through the host's private Streamlit Secrets interface. The app fails closed when no password is configured.

## Current modules

- Direct S&P 500 and Nasdaq-100 index symbols alongside clearly labeled SPY/QQQ ETF proxies
- Market overview: DIA, IWM and VIX
- Searchable Nasdaq Trader symbol directory for Nasdaq and other listed exchanges (not OTC-complete)
- Sector ETF snapshots and macro proxy dashboard
- Daily/hourly comparison; 4-hour candles are resampled from hourly bars
- EMA 20/50/200, RSI 14, MACD, ATR 14 and VWAP
- Candle-level approximate volume-by-price profile (explicitly not trade-level volume-at-price)
- Confirmed swing pivots and Fibonacci retracement references
- Password gate, five-minute data cache, GitHub Actions compilation and unit tests

## Data limitations

Yahoo Finance through yfinance is an unofficial historical-data adapter. It is not a guaranteed real-time feed and may return delayed, incomplete or unavailable data. The app caches responses for five minutes and displays no fabricated fallback data. The 4-hour view is derived from hourly bars and is not provider-native.

Federal Reserve headlines and an economic calendar are not integrated. The listed rates, dollar, gold and oil symbols are proxies, not official macroeconomic releases.

No options-chain feed, option Greeks, implied volatility, complete U.S. symbol master, broker integration or order execution is connected yet. These require separate providers, credentials, licensing review and validation. The app intentionally does not synthesize missing option data.

## Safety and scope

This is a learning and paper-analysis project. Outputs describe historical observations; they are not probabilities, predictions, or trading instructions. No real-money trading or broker connection is supported.
