from __future__ import annotations

from datetime import datetime, time
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from .options_lab import black_scholes


CHAIN_COLUMNS = [
    "contractSymbol", "strike", "lastPrice", "bid", "ask", "volume",
    "openInterest", "impliedVolatility", "inTheMoney", "contractSize", "currency",
]
NEW_YORK = ZoneInfo("America/New_York")


def get_option_expirations(symbol: str) -> list[str]:
    """Return expirations reported by Yahoo Finance; availability is not guaranteed."""
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol is required")
    ticker = yf.Ticker(normalized)
    return list(ticker.options or [])


def _finite_number(value: Any, label: str, *, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not isfinite(number) or (minimum is not None and number < minimum):
        raise ValueError(f"{label} must be a finite number" + (f" >= {minimum}" if minimum is not None else ""))
    return number


def _days_to_expiry(expiry: str, now: datetime | None = None) -> float:
    """Estimate time to the standard 16:00 New York expiration close."""
    try:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("expiry must use YYYY-MM-DD format") from exc
    current = now.astimezone(NEW_YORK) if now else datetime.now(NEW_YORK)
    expiry_close = datetime.combine(expiry_date, time(16, 0), tzinfo=NEW_YORK)
    return max((expiry_close - current).total_seconds() / 86400.0, 0.0)


def load_options_chain(
    symbol: str,
    expiry: str,
    spot: float,
    risk_free_rate: float = 0.04,
) -> dict[str, Any]:
    """Fetch a provider snapshot and add explicitly modelled European-option Greeks.

    The caller-supplied underlying spot is not guaranteed to be synchronized
    with the option-chain snapshot. Yahoo timestamps below are retrieval times.
    """
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol is required")
    spot_value = _finite_number(spot, "spot", minimum=0.0000001)
    rate = _finite_number(risk_free_rate, "risk_free_rate")
    if not -1.0 < rate < 1.0:
        raise ValueError("risk_free_rate must be between -1 and 1")

    ticker = yf.Ticker(normalized_symbol)
    expirations = list(ticker.options or [])
    if expiry not in expirations:
        raise ValueError("Selected expiration is not available from the data provider")

    chain = ticker.option_chain(expiry)
    days = _days_to_expiry(expiry)

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
            if pd.isna(iv) or not isfinite(float(iv)) or iv <= 0 or pd.isna(strike) or strike <= 0:
                model_values.append({})
                continue
            try:
                model_values.append(black_scholes(
                    spot=spot_value,
                    strike=float(strike),
                    days_to_expiry=days,
                    volatility=float(iv),
                    risk_free_rate=rate,
                    option_type=option_type,
                ))
            except (ValueError, OverflowError):
                model_values.append({})

        for key in ("price", "delta", "gamma", "theta_per_day", "vega_per_1pct"):
            result[key] = [values.get(key) for values in model_values]

        valid_market = (
            result["bid"].notna() & result["ask"].notna()
            & (result["bid"] >= 0) & (result["ask"] >= result["bid"])
        )
        result["mid"] = ((result["bid"] + result["ask"]) / 2).where(valid_market)
        result["spread"] = (result["ask"] - result["bid"]).where(valid_market)
        result["spread_pct_mid"] = (
            result["spread"] / result["mid"] * 100
        ).where(result["mid"] > 0)
        result["quote_validity"] = "غير مكتمل أو غير صالح"
        result.loc[valid_market, "quote_validity"] = "عرض وطلب صالحان حسابياً"
        result["retrieved_at_utc"] = datetime.now(ZoneInfo("UTC")).isoformat()
        return result

    calls = prepare(chain.calls, "call")
    puts = prepare(chain.puts, "put")
    retrieved = datetime.now(ZoneInfo("UTC")).isoformat()
    return {
        "symbol": normalized_symbol,
        "expiry": expiry,
        "spot_reference": spot_value,
        "days_to_expiry": days,
        "retrieved_at_utc": retrieved,
        "provider": "Yahoo Finance via yfinance",
        "quote_status": "provider snapshot; real-time status not guaranteed",
        "spot_reference_warning": (
            "Spot is supplied by the caller and may not be synchronized with the option-chain snapshot. "
            "Greeks are model estimates, not exchange-provided values."
        ),
        "model_assumptions": (
            "European Black-Scholes approximation; excludes dividends, early exercise, "
            "volatility skew, bid/ask execution, fees and contract-specific settlement."
        ),
        "calls": calls,
        "puts": puts,
    }
