from __future__ import annotations

import pandas as pd


def add_indicators(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    close = df["Close"]
    for length in (20, 50, 200):
        df[f"EMA{length}"] = close.ewm(span=length, adjust=False, min_periods=length).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((gain == 0) & (loss > 0), 0)
    df["RSI14"] = rsi

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACDSignal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    previous_close = close.shift(1)
    true_range = pd.concat(
        [(df["High"] - df["Low"]), (df["High"] - previous_close).abs(),
         (df["Low"] - previous_close).abs()], axis=1
    ).max(axis=1)
    df["ATR14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    typical_price = (df["High"] + df["Low"] + close) / 3
    volume = df["Volume"].fillna(0)
    is_intraday = False
    if isinstance(df.index, pd.DatetimeIndex) and len(df.index) > 1:
        deltas = df.index.to_series().diff().dropna()
        is_intraday = not deltas.empty and deltas.median() < pd.Timedelta(days=1)
    if is_intraday:
        sessions = pd.Series(df.index.date, index=df.index)
        cumulative_pv = (typical_price * volume).groupby(sessions).cumsum()
        cumulative_volume = volume.groupby(sessions).cumsum()
    else:
        cumulative_pv = (typical_price * volume).cumsum()
        cumulative_volume = volume.cumsum()
    df["VWAP"] = cumulative_pv / cumulative_volume.replace(0, float("nan"))
    return df
