from __future__ import annotations

from typing import Any

import pandas as pd

from .options_lab import black_scholes, expiration_value


def simulate_option_scenarios(
    *,
    spot: float,
    strike: float,
    days_to_expiry: int,
    volatility: float,
    risk_free_rate: float,
    option_type: str,
    premium_per_share: float,
    multiplier: int = 100,
    contracts: int = 1,
    spot_changes_pct: list[float] | None = None,
    volatility_changes_pct: list[float] | None = None,
    elapsed_days: list[int] | None = None,
) -> dict[str, Any]:
    """Generate hypothetical mark-to-model and expiry outcomes, never trade signals."""
    if spot <= 0 or strike <= 0 or premium_per_share < 0:
        raise ValueError("spot and strike must be positive; premium cannot be negative")
    if days_to_expiry < 0 or volatility <= 0 or multiplier < 1 or contracts < 1:
        raise ValueError("invalid time, volatility, multiplier, or contract count")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")

    spot_changes_pct = spot_changes_pct or [-20, -10, 0, 10, 20]
    volatility_changes_pct = volatility_changes_pct or [-30, 0, 30]
    elapsed_days = elapsed_days or [0, days_to_expiry // 2, days_to_expiry]
    if any(day < 0 or day > days_to_expiry for day in elapsed_days):
        raise ValueError("elapsed_days must be between zero and days_to_expiry")
    if any(volatility * (1 + change / 100) <= 0 for change in volatility_changes_pct):
        raise ValueError("volatility shock produces a non-positive volatility")

    rows: list[dict[str, float | int | str]] = []
    total_units = multiplier * contracts
    initial_cost = premium_per_share * total_units

    for spot_change in spot_changes_pct:
        scenario_spot = spot * (1 + spot_change / 100)
        if scenario_spot <= 0:
            continue
        for vol_change in volatility_changes_pct:
            scenario_vol = volatility * (1 + vol_change / 100)
            for elapsed in elapsed_days:
                remaining = max(days_to_expiry - elapsed, 0)
                mark = black_scholes(
                    spot=scenario_spot,
                    strike=strike,
                    days_to_expiry=remaining,
                    volatility=scenario_vol,
                    risk_free_rate=risk_free_rate,
                    option_type=option_type,
                )["price"]
                expiry_intrinsic = expiration_value(scenario_spot, strike, option_type)
                modeled_value = mark * total_units
                rows.append({
                    "spot_change_pct": float(spot_change),
                    "scenario_spot": float(scenario_spot),
                    "iv_change_pct": float(vol_change),
                    "scenario_iv_pct": float(scenario_vol * 100),
                    "elapsed_days": int(elapsed),
                    "remaining_days": int(remaining),
                    "model_value_per_share": float(mark),
                    "model_value_total": float(modeled_value),
                    "model_pnl_vs_assumed_premium": float(modeled_value - initial_cost),
                    "expiry_intrinsic_total": float(expiry_intrinsic * total_units),
                    "expiry_pnl_vs_assumed_premium": float(expiry_intrinsic * total_units - initial_cost),
                })

    frame = pd.DataFrame(rows)
    return {
        "scenarios": frame,
        "assumed_initial_cost": float(initial_cost),
        "scenario_count": len(frame),
        "note": (
            "All outcomes are hypothetical Black–Scholes estimates. "
            "Model P&L compares a scenario mark with the user-entered assumed premium; "
            "expiry P&L uses intrinsic value only. Fees, spread, slippage, dividends, "
            "early exercise, volatility skew and contract-specific settlement are excluded."
        ),
    }
