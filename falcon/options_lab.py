from __future__ import annotations

from math import erf, exp, log, pi, sqrt
from typing import Literal

OptionType = Literal["call", "put"]


def _normal_pdf(value: float) -> float:
    return exp(-0.5 * value * value) / sqrt(2 * pi)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def black_scholes(
    spot: float,
    strike: float,
    days_to_expiry: float,
    volatility: float,
    risk_free_rate: float = 0.04,
    option_type: OptionType = "call",
) -> dict[str, float]:
    """Educational European-option model; inputs are assumptions, not a live quote.

    Returns theoretical value, delta, gamma, theta per calendar day and vega
    per one volatility percentage point. Dividends, early exercise, discrete
    rates, bid/ask, fees and contract-specific settlement are not modeled.
    """
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if days_to_expiry < 0:
        raise ValueError("days_to_expiry cannot be negative")
    if volatility <= 0:
        raise ValueError("volatility must be positive")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")

    t = days_to_expiry / 365.0
    if t == 0:
        intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
        delta = (1.0 if spot > strike else 0.0) if option_type == "call" else (-1.0 if spot < strike else 0.0)
        return {"price": intrinsic, "delta": delta, "gamma": 0.0, "theta_per_day": 0.0, "vega_per_1pct": 0.0}

    root_t = sqrt(t)
    d1 = (log(spot / strike) + (risk_free_rate + 0.5 * volatility**2) * t) / (volatility * root_t)
    d2 = d1 - volatility * root_t
    discount = exp(-risk_free_rate * t)
    pdf = _normal_pdf(d1)

    if option_type == "call":
        price = spot * _normal_cdf(d1) - strike * discount * _normal_cdf(d2)
        delta = _normal_cdf(d1)
        theta_year = -(spot * pdf * volatility) / (2 * root_t) - risk_free_rate * strike * discount * _normal_cdf(d2)
    else:
        price = strike * discount * _normal_cdf(-d2) - spot * _normal_cdf(-d1)
        delta = _normal_cdf(d1) - 1.0
        theta_year = -(spot * pdf * volatility) / (2 * root_t) + risk_free_rate * strike * discount * _normal_cdf(-d2)

    gamma = pdf / (spot * volatility * root_t)
    vega_per_1pct = spot * pdf * root_t * 0.01
    return {
        "price": max(float(price), 0.0),
        "delta": float(delta),
        "gamma": float(gamma),
        "theta_per_day": float(theta_year / 365.0),
        "vega_per_1pct": float(vega_per_1pct),
    }


def expiration_value(spot_at_expiry: float, strike: float, option_type: OptionType) -> float:
    """Intrinsic value per share at expiration, before premium and costs."""
    if spot_at_expiry < 0 or strike <= 0:
        raise ValueError("spot_at_expiry must be non-negative and strike positive")
    if option_type == "call":
        return max(spot_at_expiry - strike, 0.0)
    if option_type == "put":
        return max(strike - spot_at_expiry, 0.0)
    raise ValueError("option_type must be 'call' or 'put'")
