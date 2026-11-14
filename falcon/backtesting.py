from __future__ import annotations

from typing import Any

import pandas as pd

from .indicators import add_indicators


def _clean_history(data: pd.DataFrame) -> pd.DataFrame:
    """Return chronologically ordered, unique OHLCV observations."""
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = sorted(set(required).difference(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    frame = data.copy()
    frame = frame[~frame.index.isna()]
    frame = frame[~frame.index.duplicated(keep="last")].sort_index(kind="stable")
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
    return frame


def build_historical_observations(
    data: pd.DataFrame,
    horizon: int = 5,
    transaction_cost_bps: float = 10.0,
) -> pd.DataFrame:
    """Build directional underlying-price observations for research.

    Entry is the next bar open and exit is the close at signal bar + horizon.
    transaction_cost_bps represents the total round-trip cost assumption.
    These are not option-contract returns.
    """
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps cannot be negative")
    frame = _clean_history(data)
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
    cost = transaction_cost_bps / 10_000
    strategy_return = signal * gross_return - signal.abs() * cost
    observations = pd.DataFrame({
        "signal_time": frame.index,
        "signal": signal,
        "entry_time": pd.Series(frame.index, index=frame.index).shift(-1),
        "entry_price": entry,
        "exit_time": pd.Series(frame.index, index=frame.index).shift(-horizon),
        "exit_price": exit_price,
        "underlying_return": gross_return,
        "estimated_round_trip_cost_bps": transaction_cost_bps,
        "strategy_return": strategy_return,
    }, index=frame.index)
    observations = observations.iloc[:-horizon].dropna(subset=["entry_price", "exit_price"])
    observations = observations[observations["signal"] != 0]
    return observations[
        (observations["entry_price"] > 0) & (observations["exit_price"] > 0)
    ].copy()


def _select_non_overlapping(observations: pd.DataFrame) -> pd.DataFrame:
    """Select a chronological, single-position sequence of observations."""
    if observations.empty:
        return observations.copy()
    ordered = observations.sort_values(["entry_time", "exit_time", "signal_time"]).copy()
    selected_indices = []
    last_exit = None
    for index, row in ordered.iterrows():
        if last_exit is None or row["entry_time"] > last_exit:
            selected_indices.append(index)
            last_exit = row["exit_time"]
    return ordered.loc[selected_indices].sort_values("signal_time").copy()


def _observation_metrics(returns: pd.Series) -> dict[str, Any]:
    """Per-signal descriptive statistics; intentionally no portfolio curve."""
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return {
            "observations": 0, "win_rate_pct": None, "mean_return_pct": None,
            "median_return_pct": None, "profit_factor": None,
        }
    gains = values[values > 0].sum()
    losses = abs(values[values < 0].sum())
    factor = float(gains / losses) if losses > 0 else (None if gains == 0 else float("inf"))
    return {
        "observations": int(len(values)),
        "win_rate_pct": float((values > 0).mean() * 100),
        "mean_return_pct": float(values.mean() * 100),
        "median_return_pct": float(values.median() * 100),
        "profit_factor": factor,
    }


def _metrics(returns: pd.Series) -> dict[str, Any]:
    """Sequential fixed-notional trade metrics; no compounding or reinvestment assumption."""
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return {
            "observations": 0, "win_rate_pct": None, "mean_return_pct": None,
            "median_return_pct": None, "cumulative_return_pct": None,
            "max_drawdown_pct": None, "profit_factor": None,
        }
    pnl_curve = values.cumsum()
    running_peak = pnl_curve.cummax().clip(lower=0)
    drawdown = pnl_curve - running_peak
    gains = values[values > 0].sum()
    losses = abs(values[values < 0].sum())
    factor = float(gains / losses) if losses > 0 else (None if gains == 0 else float("inf"))
    return {
        "observations": int(len(values)),
        "win_rate_pct": float((values > 0).mean() * 100),
        "mean_return_pct": float(values.mean() * 100),
        "median_return_pct": float(values.median() * 100),
        "cumulative_return_pct": float(pnl_curve.iloc[-1] * 100),
        "max_drawdown_pct": float(drawdown.min() * 100),
        "profit_factor": factor,
    }


def walk_forward_validate(observations: pd.DataFrame, train_fraction: float = 0.7) -> dict[str, Any]:
    """Chronological holdout with boundary purge and non-overlapping trade metrics."""
    if not 0.5 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    required = {"signal_time", "strategy_return", "exit_time", "entry_time"}
    if not required.issubset(observations.columns):
        raise ValueError("observations must contain signal_time, entry_time, exit_time and strategy_return")
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

    train_portfolio = _select_non_overlapping(train)
    test_portfolio = _select_non_overlapping(test)
    return {
        "train": train,
        "test": test,
        "train_non_overlapping": train_portfolio,
        "test_non_overlapping": test_portfolio,
        "split_time": str(test_start),
        "purged_training_observations": int(raw_split - len(train)),
        "train_signal_metrics": _observation_metrics(train["strategy_return"]),
        "test_signal_metrics": _observation_metrics(test["strategy_return"]),
        "train_metrics": _metrics(train_portfolio["strategy_return"]),
        "test_metrics": _metrics(test_portfolio["strategy_return"]),
        "method_note": (
            "Chronological holdout; training labels crossing the test boundary are purged. "
            "Signals use data available at the signal close, enter at the next bar open, "
            "and exit at the close of the fixed horizon. Portfolio metrics use a "
            "single-position, non-overlapping sequence. Signal-level statistics are "
            "reported separately. Cost is an assumed total round-trip underlying cost. "
            "These are underlying-price proxies, not option-contract returns."
        ),
    }
