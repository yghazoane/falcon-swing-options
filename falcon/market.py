from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=300, show_spinner=False)
def load_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Load chronologically ordered, split/dividend-adjusted OHLCV history.

    Yahoo Finance data may be delayed, incomplete, revised or unavailable.
    Adjusted OHLC prices are used consistently for indicator research.
    """
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol is required")
    ticker = yf.Ticker(normalized)
    data = ticker.history(
        period=period,
        interval=interval,
        auto_adjust=True,
        actions=False,
    )
    if data is None or data.empty:
        return pd.DataFrame()
    data = data.rename_axis("Date").copy()
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        return pd.DataFrame()
    data = data[required]
    for column in required:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data[~data.index.isna()]
    data = data[~data.index.duplicated(keep="last")].sort_index(kind="stable")
    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    return data
