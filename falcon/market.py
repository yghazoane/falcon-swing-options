from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

@st.cache_data(ttl=300, show_spinner=False)
def load_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Load provider history; cache briefly to reduce repeated network requests.

    The provider does not guarantee a real-time feed, complete coverage, or
    stable availability. Empty results stay empty rather than being fabricated.
    """
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval, auto_adjust=False)
    if data is None or data.empty:
        return pd.DataFrame()
    data = data.rename_axis("Date")
    required = ["Open", "High", "Low", "Close", "Volume"]
    return data[[c for c in required if c in data.columns]].dropna(subset=["Close"])
