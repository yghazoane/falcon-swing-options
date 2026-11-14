from __future__ import annotations

from typing import Any

import pandas as pd

from .indicators import add_indicators


def build_historical_observations(
    data: pd.DataFrame,
    horizon: int = 5,
    transaction_cost_bps: float = 5.0,
) -> pd.DataFrame:
    """Create next-bar-entry, fixed-horizon underlying-price observations."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps cannot be negative")
    frame = data.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    if len(frame) <= horizon + 200:
        raise ValueError("At least 202 + horizon usable bars are required")
    frame = add_indicators(frame)
    close = frame["Close"]
    signal = pd.Series(0, index=frame.index, dtype="int64")
    bullish = (
        (close > frame["EMA20"]) & (frame["EMA20"] > frame["EMA50"])
        & (frame["RSI14"] >= 50) & (frame["MACD"] > frame["MACDSignal"])
    )
    bearish = (
        (close < frame["EMA20"]) & (frame["EMA20"] < frame["EMA50"])
        & (frame["RSI14"] <= 50) & (frame["MACD"] < frame["MACDSignal"])
    )
    signal.loc[bullish.fillna(False)] = 1
    signal.loc[bearish.fillna(False)] = -1
    entry = frame["Open"].shift(-1)
    exit_price = frame["Close"].shift(-horizon)
    gross_return = (exit_price / entry) - 1
    strategy_return = signal * gross_return - signal.abs() * (transaction_cost_bps / 10_000)
    observations = pd.DataFrame({
        "signal_time": frame.index,
        "signal": signal,
        "entry_time": pd.Series(frame.index, index=frame.index).shift(-1),
        "entry_price": entry,
        "exit_time": pd.Series(frame.index, index=frame.index).shift(-horizon),
        "exit_price": exit_price,
        "underlying_return": gross_return,
        "strategy_return": strategy_return,
    }, index=frame.index)
    observations = observations.iloc[:-horizon].dropna(subset=["entry_price", "exit_price"])
    observations = observations[observations["signal"] != 0]
    return observations[(observations["entry_price"] > 0) & (observations["exit_price"] > 0)]


def _metrics(returns: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return {"observations": 0, "win_rate_pct": None, "mean_return_pct": None,
                "median_return_pct": None, "cumulative_return_pct": None,
                "max_drawdown_pct": None, "profit_factor": None}
    equity = (1 + values).cumprod()
    drawdown = equity / equity.cummax() - 1
    gains, losses = values[values > 0].sum(), abs(values[values < 0].sum())
    factor = float(gains / losses) if losses > 0 else (None if gains == 0 else float("inf"))
    return {
        "observations": int(len(values)),
        "win_rate_pct": float((values > 0).mean() * 100),
        "mean_return_pct": float(values.mean() * 100),
        "median_return_pct": float(values.median() * 100),
        "cumulative_return_pct": float((equity.iloc[-1] - 1) * 100),
        "max_drawdown_pct": float(drawdown.min() * 100),
        "profit_factor": factor,
    }


def walk_forward_validate(observations: pd.DataFrame, train_fraction: float = 0.7) -> dict[str, Any]:
    """Chronological holdout with purge of training labels crossing the test boundary."""
    if not 0.5 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    required = {"signal_time", "strategy_return", "exit_time"}
    if not required.issubset(observations.columns):
        raise ValueError("observations must contain signal_time, exit_time and strategy_return")
    ordered = observations.sort_values("signal_time").copy()
    if len(ordered) < 20:
        raise ValueError("At least 20 eligible observations are required")
    raw_split = int(len(ordered) * train_fraction)
    test = ordered.iloc[raw_split:].copy()
    if test.empty:
        raise ValueError("Insufficient observations in test period")
    test_start = test["signal_time"].iloc[0]
    train = ordered.iloc[:raw_split].copy()
    train = train[train["exit_time"] < test_start]
    if len(train) < 10 or len(test) < 5:
        raise ValueError("Insufficient observations after purging the train/test boundary")
    return {
        "train": train,
        "test": test,
        "split_time": str(test_start),
        "purged_training_observations": int(raw_split - len(train)),
        "train_metrics": _metrics(train["strategy_return"]),
        "test_metrics": _metrics(test["strategy_return"]),
        "method_note": (
            "Chronological holdout, not randomized. Training observations whose "
            "holding windows overlap the test boundary are purged. Indicators use "
            "current/past bars; signal at t is paired with entry at t+1 Open and exit "
            "at t+horizon Close. Final incomplete horizon is removed. Remaining "
            "holding periods may overlap within each partition, so observations are "
            "not independent. These are underlying-price proxies, not option-contract "
            "returns, and do not establish future performance."
        ),
    }
