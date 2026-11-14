from __future__ import annotations

import numpy as np
import pandas as pd


def volume_by_price(data: pd.DataFrame, bins: int = 24) -> pd.DataFrame:
    """Approximate volume-at-price using each candle's typical price.

    This is a candle-level proxy, not an exchange trade-by-trade volume profile.
    """
    if bins < 2:
        raise ValueError("bins must be at least 2")
    if data.empty:
        return pd.DataFrame(columns=["price_level", "volume"])
    prices = ((data["High"] + data["Low"] + data["Close"]) / 3).astype(float)
    volumes = data["Volume"].fillna(0).astype(float)
    valid = prices.notna() & volumes.notna() & (volumes >= 0)
    prices, volumes = prices[valid], volumes[valid]
    if prices.empty:
        return pd.DataFrame(columns=["price_level", "volume"])
    low, high = float(prices.min()), float(prices.max())
    if low == high:
        return pd.DataFrame([{"price_level": low, "volume": float(volumes.sum())}])
    edges = np.linspace(low, high, bins + 1)
    totals, _ = np.histogram(prices.to_numpy(), bins=edges, weights=volumes.to_numpy())
    centers = (edges[:-1] + edges[1:]) / 2
    return pd.DataFrame({"price_level": centers, "volume": totals})
