from __future__ import annotations

from io import StringIO
import pandas as pd
import requests
import streamlit as st

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

def _read_directory(text: str) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(text), sep="|", dtype=str)
    return frame.loc[~frame.iloc[:, 0].astype(str).str.startswith("File Creation Time")].copy()

def parse_symbol_directories(nasdaq_text: str, other_text: str) -> pd.DataFrame:
    """Parse Nasdaq Trader symbol-directory exports into a normalized listed universe."""
    nasdaq = _read_directory(nasdaq_text)
    other = _read_directory(other_text)
    n = pd.DataFrame({
        "symbol": nasdaq.get("Symbol"),
        "security_name": nasdaq.get("Security Name"),
        "exchange": "NASDAQ",
        "etf": nasdaq.get("ETF", "N").fillna("N"),
        "test_issue": nasdaq.get("Test Issue", "N").fillna("N"),
    })
    o = pd.DataFrame({
        "symbol": other.get("ACT Symbol"),
        "security_name": other.get("Security Name"),
        "exchange": other.get("Exchange", "Other").fillna("Other"),
        "etf": other.get("ETF", "N").fillna("N"),
        "test_issue": other.get("Test Issue", "N").fillna("N"),
    })
    result = pd.concat([n, o], ignore_index=True)
    result["symbol"] = result["symbol"].astype(str).str.strip().str.replace(".", "-", regex=False)
    result["security_name"] = result["security_name"].fillna("").astype(str).str.strip()
    result = result[(result["symbol"] != "") & (result["symbol"].str.lower() != "nan")]
    result = result[result["test_issue"].str.upper() != "Y"]
    result = result[result["symbol"].str.match(r"^[A-Z0-9-]+$", na=False)]
    result = result.drop_duplicates(subset=["symbol"]).sort_values("symbol")
    return result[["symbol", "security_name", "exchange", "etf"]].reset_index(drop=True)

@st.cache_data(ttl=21600, show_spinner=False)
def load_us_equity_universe() -> pd.DataFrame:
    """Load Nasdaq-listed and other-exchange symbol directories; not OTC coverage."""
    headers = {"User-Agent": "FalconSwingOptions educational research app"}
    n_response = requests.get(NASDAQ_LISTED_URL, headers=headers, timeout=20)
    o_response = requests.get(OTHER_LISTED_URL, headers=headers, timeout=20)
    n_response.raise_for_status()
    o_response.raise_for_status()
    return parse_symbol_directories(n_response.text, o_response.text)
