import pytest

from falcon.scenario_simulator import simulate_option_scenarios


def test_simulator_builds_cartesian_scenarios():
    result = simulate_option_scenarios(
        spot=100, strike=100, days_to_expiry=30, volatility=0.3,
        risk_free_rate=0.04, option_type="call", premium_per_share=3,
        multiplier=100, contracts=2,
        spot_changes_pct=[-10, 0, 10],
        volatility_changes_pct=[-20, 20],
        elapsed_days=[0, 15, 30],
    )
    frame = result["scenarios"]
    assert len(frame) == 18
    assert result["assumed_initial_cost"] == pytest.approx(600)
    assert set(frame["elapsed_days"]) == {0, 15, 30}
    assert frame["model_pnl_vs_assumed_premium"].notna().all()


def test_expiry_scenario_has_intrinsic_value():
    result = simulate_option_scenarios(
        spot=100, strike=100, days_to_expiry=10, volatility=0.25,
        risk_free_rate=0.04, option_type="put", premium_per_share=2,
        spot_changes_pct=[-20], volatility_changes_pct=[0],
        elapsed_days=[10],
    )
    row = result["scenarios"].iloc[0]
    assert row["remaining_days"] == 0
    assert row["model_value_per_share"] == pytest.approx(20)
    assert row["expiry_intrinsic_total"] == pytest.approx(2000)


def test_invalid_elapsed_days_are_rejected():
    with pytest.raises(ValueError, match="elapsed_days"):
        simulate_option_scenarios(
            spot=100, strike=100, days_to_expiry=10, volatility=0.2,
            risk_free_rate=0.04, option_type="call", premium_per_share=1,
            elapsed_days=[11],
        )


def test_invalid_volatility_shock_is_rejected():
    with pytest.raises(ValueError, match="non-positive volatility"):
        simulate_option_scenarios(
            spot=100, strike=100, days_to_expiry=10, volatility=0.2,
            risk_free_rate=0.04, option_type="call", premium_per_share=1,
            volatility_changes_pct=[-100],
        )
