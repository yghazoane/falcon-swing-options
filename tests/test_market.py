import pandas as pd

from falcon import market


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol
        self.kwargs = None

    def history(self, **kwargs):
        self.kwargs = kwargs
        index = pd.to_datetime(["2025-01-03", "2025-01-02", "2025-01-02"])
        return pd.DataFrame({
            "Open": [103, 102, 101],
            "High": [104, 103, 102],
            "Low": [102, 101, 100],
            "Close": [103, 102, 101],
            "Volume": [1000, 900, 800],
        }, index=index)


def test_load_history_uses_adjusted_prices_and_normalizes_index(monkeypatch):
    ticker = FakeTicker("TEST")
    monkeypatch.setattr(market.yf, "Ticker", lambda symbol: ticker)
    market.load_history.clear()
    result = market.load_history("test", period="1y", interval="1d")
    assert ticker.kwargs["auto_adjust"] is True
    assert result.index.is_monotonic_increasing
    assert result.index.is_unique
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(result) == 2
    market.load_history.clear()


def test_load_history_empty_response(monkeypatch):
    class EmptyTicker:
        def __init__(self, symbol):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(market.yf, "Ticker", EmptyTicker)
    market.load_history.clear()
    assert market.load_history("EMPTY").empty
    market.load_history.clear()
