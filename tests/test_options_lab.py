import pytest

from falcon.options_lab import black_scholes, expiration_value


def test_call_value_increases_with_spot():
    low = black_scholes(95, 100, 45, 0.30, option_type="call")["price"]
    high = black_scholes(105, 100, 45, 0.30, option_type="call")["price"]
    assert high > low


def test_put_value_decreases_with_spot():
    low = black_scholes(95, 100, 45, 0.30, option_type="put")["price"]
    high = black_scholes(105, 100, 45, 0.30, option_type="put")["price"]
    assert low > high


def test_greeks_have_expected_signs_for_vanilla_options():
    call = black_scholes(100, 100, 30, 0.25, option_type="call")
    put = black_scholes(100, 100, 30, 0.25, option_type="put")
    assert 0 < call["delta"] < 1
    assert -1 < put["delta"] < 0
    assert call["gamma"] > 0 and put["gamma"] > 0
    assert call["vega_per_1pct"] > 0 and put["vega_per_1pct"] > 0
    assert call["theta_per_day"] < 0 and put["theta_per_day"] < 0


def test_expiration_intrinsic_value():
    assert expiration_value(110, 100, "call") == 10
    assert expiration_value(90, 100, "put") == 10
    assert expiration_value(90, 100, "call") == 0


@pytest.mark.parametrize("kwargs", [
    {"spot": 0, "strike": 100, "days_to_expiry": 30, "volatility": 0.2},
    {"spot": 100, "strike": -1, "days_to_expiry": 30, "volatility": 0.2},
    {"spot": 100, "strike": 100, "days_to_expiry": -1, "volatility": 0.2},
    {"spot": 100, "strike": 100, "days_to_expiry": 30, "volatility": 0},
])
def test_invalid_model_inputs_raise(kwargs):
    with pytest.raises(ValueError):
        black_scholes(**kwargs)


def test_expiry_value_has_zero_time_greeks():
    result = black_scholes(105, 100, 0, 0.2, option_type="call")
    assert result["price"] == 5
    assert result["gamma"] == 0
    assert result["theta_per_day"] == 0
