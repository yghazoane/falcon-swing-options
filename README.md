# Falcon Swing Options

Private, educational Streamlit workspace for studying U.S. market data, technical structure and options terminology. Paper analysis only.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Current modules

- Market overview: SPY, QQQ, DIA, IWM and VIX
- Sector ETF snapshots and relative market context
- Macro proxies: Treasury yield, US Dollar, gold and crude oil
- Daily/hourly comparison; 4-hour candles are resampled from hourly bars
- EMA 20/50/200, RSI 14, MACD and ATR 14
- Confirmed swing pivots and Fibonacci retracement references
- GitHub Actions compilation and unit tests

## Data limitations

Yahoo Finance through yfinance is an unofficial historical-data adapter. It is not a guaranteed real-time feed and may return delayed, incomplete or unavailable data. The app caches responses for five minutes and displays no fabricated fallback data. The 4-hour view is derived from hourly bars and is not provider-native.

Federal Reserve headlines and an economic calendar are not integrated. The listed rates, dollar, gold and oil symbols are proxies, not official macroeconomic releases.

No options-chain feed, option Greeks, implied volatility, complete U.S. symbol master, broker integration or order execution is connected yet. These require separate providers, credentials, licensing review and validation. The app intentionally does not synthesize missing option data.

## Safety and scope

This is a learning and paper-analysis project. Outputs describe historical observations; they are not probabilities, predictions, or trading instructions. No real-money trading or broker connection is supported.
