from __future__ import annotations

import yfinance as yf
import pandas as pd


def load_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Load provider history. This is not a guaranteed real-time feed."""
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval, auto_adjust=False)
    if data is None or data.empty:
        return pd.DataFrame()
    data = data.rename_axis("Date")
    required = ["Open", "High", "Low", "Close", "Volume"]
    return data[[c for c in required if c in data.columns]].dropna(subset=["Close"])
