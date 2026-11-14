import numpy as np
import pandas as pd
import pytest

from falcon.backtesting import build_historical_observations, walk_forward_validate


def history(rows: int = 500) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=rows, freq="B")
    close = 100 + np.linspace(0, 25, rows) + np.sin(np.arange(rows) / 8) * 2
    return pd.DataFrame({
        "Open": close - 0.1, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": 100_000 + np.arange(rows) * 10,
    }, index=index)


def test_observations_enter_after_signal_and_exit_at_horizon():
    frame = history()
    horizon = 5
    observations = build_historical_observations(frame, horizon=horizon)
    first = observations.iloc[0]
    signal_position = frame.index.get_loc(first["signal_time"])
    assert first["entry_time"] == frame.index[signal_position + 1]
    assert first["exit_time"] == frame.index[signal_position + horizon]
    assert observations["exit_time"].max() <= frame.index[-1]


def test_walk_forward_is_chronological_and_purges_boundary_overlap():
    observations = build_historical_observations(history())
    report = walk_forward_validate(observations, train_fraction=0.7)
    test_start = report["test"]["signal_time"].min()
    assert report["train"]["signal_time"].max() < test_start
    assert (report["train"]["exit_time"] < test_start).all()
    assert report["purged_training_observations"] >= 0
    assert report["train_metrics"]["observations"] + report["test_metrics"]["observations"] == len(report["train"]) + len(report["test"])
    assert report["test_metrics"]["observations"] > 0


def test_rejects_invalid_horizon_and_fraction():
    with pytest.raises(ValueError, match="horizon"):
        build_historical_observations(history(), horizon=0)
    with pytest.raises(ValueError, match="train_fraction"):
        walk_forward_validate(pd.DataFrame({"signal_time": [], "strategy_return": [], "exit_time": []}), train_fraction=0.4)


def test_short_history_is_rejected():
    with pytest.raises(ValueError, match="202"):
        build_historical_observations(history(150))
