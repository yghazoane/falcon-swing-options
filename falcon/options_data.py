from __future__ import annotations

from typing import Literal
import pandas as pd
import streamlit as st
import yfinance as yf

OPTION_COLUMNS = [
    "contractSymbol", "strike", "lastPrice", "bid", "ask", "change",
    "percentChange", "volume", "openInterest", "impliedVolatility",
    "inTheMoney", "contractSize", "currency",
]


def normalize_option_chain(frame: pd.DataFrame, side: Literal["CALL", "PUT"]) -> pd.DataFrame:
    """Normalize a provider chain without inventing unavailable fields."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["side", *OPTION_COLUMNS])
    result = frame.copy()
    for column in OPTION_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    result = result[OPTION_COLUMNS]
    result.insert(0, "side", side)
    return result.reset_index(drop=True)


@st.cache_data(ttl=180, show_spinner=False)
def load_option_expirations(symbol: str) -> list[str]:
    """Retrieve available expirations from Yahoo Finance; availability is not guaranteed."""
    expirations = yf.Ticker(symbol).options
    return list(expirations or [])


@st.cache_data(ttl=90, show_spinner=False)
def load_option_chain(symbol: str, expiration: str) -> pd.DataFrame:
    """Retrieve the selected expiry's calls and puts, preserving provider blanks."""
    chain = yf.Ticker(symbol).option_chain(expiration)
    calls = normalize_option_chain(chain.calls, "CALL")
    puts = normalize_option_chain(chain.puts, "PUT")
    combined = pd.concat([calls, puts], ignore_index=True)
    if not combined.empty:
        combined["expiration"] = expiration
        combined["dte"] = (
            pd.Timestamp(expiration).normalize() - pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
        ).days
    return combined
