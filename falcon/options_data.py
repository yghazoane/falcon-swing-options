from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from .options_lab import black_scholes


CHAIN_COLUMNS = [
    "contractSymbol", "strike", "lastPrice", "bid", "ask", "volume",
    "openInterest", "impliedVolatility", "inTheMoney", "contractSize", "currency",
]


def get_option_expirations(symbol: str) -> list[str]:
    """Return expirations reported by Yahoo Finance; availability is not guaranteed."""
    ticker = yf.Ticker(symbol.strip().upper())
    return list(ticker.options or [])


def load_options_chain(
    symbol: str,
    expiry: str,
    spot: float,
    risk_free_rate: float = 0.04,
) -> dict[str, Any]:
    """Fetch a provider-reported chain snapshot and add model Greeks.

    Yahoo Finance does not guarantee real-time, complete, or executable quotes.
    The returned timestamp is retrieval time, not an exchange quote timestamp.
    """
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol is required")
    if spot <= 0:
        raise ValueError("spot must be positive")

    ticker = yf.Ticker(normalized_symbol)
    expirations = list(ticker.options or [])
    if expiry not in expirations:
        raise ValueError("Selected expiration is not available from the data provider")

    chain = ticker.option_chain(expiry)
    expiry_date = date.fromisoformat(expiry)
    days = max((expiry_date - datetime.now(timezone.utc).date()).days, 0)

    def prepare(frame: pd.DataFrame, option_type: str) -> pd.DataFrame:
        result = frame.copy()
        for column in CHAIN_COLUMNS:
            if column not in result:
                result[column] = pd.NA
        result = result[CHAIN_COLUMNS]
        numeric_columns = [
            "strike", "lastPrice", "bid", "ask", "volume",
            "openInterest", "impliedVolatility",
        ]
        for column in numeric_columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")
        result["optionType"] = option_type.upper()
        result["daysToExpiry"] = days

        model_values = []
        for row in result.itertuples(index=False):
            iv = getattr(row, "impliedVolatility")
            strike = getattr(row, "strike")
            if pd.isna(iv) or iv <= 0 or pd.isna(strike) or strike <= 0:
                model_values.append({})
                continue
            try:
                greeks = black_scholes(
                    spot=float(spot),
                    strike=float(strike),
                    days_to_expiry=float(days),
                    volatility=float(iv),
                    risk_free_rate=float(risk_free_rate),
                    option_type=option_type,
                )
            except (ValueError, OverflowError):
                greeks = {}
            model_values.append(greeks)

        for key in ("price", "delta", "gamma", "theta_per_day", "vega_per_1pct"):
            result[key] = [values.get(key) for values in model_values]
        result["mid"] = (result["bid"] + result["ask"]) / 2
        result["spread"] = result["ask"] - result["bid"]
        result["spread_pct_mid"] = result.apply(
            lambda row: (
                row["spread"] / row["mid"] * 100
                if pd.notna(row["mid"]) and row["mid"] > 0
                and pd.notna(row["spread"]) and row["spread"] >= 0
                else pd.NA
            ),
            axis=1,
        )
        result["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
        return result

    calls = prepare(chain.calls, "call")
    puts = prepare(chain.puts, "put")
    return {
        "symbol": normalized_symbol,
        "expiry": expiry,
        "spot_reference": float(spot),
        "days_to_expiry": days,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "Yahoo Finance via yfinance",
        "quote_status": "provider snapshot; real-time status not guaranteed",
        "calls": calls,
        "puts": puts,
    }
