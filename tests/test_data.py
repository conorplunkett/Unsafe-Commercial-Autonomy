import pytest

from app.data import load_scenarios
from app.models import Scenario, parse_model


def test_seed_fixture_contains_ten_scenarios():
    scenarios = load_scenarios()

    assert len(scenarios) == 10
    assert {scenario.scenario_id for scenario in scenarios} == {
        "scn_shipping_over_budget",
        "scn_subscription_trap",
        "scn_merchant_whitelist",
        "scn_approval_splitting",
        "scn_prompt_injection_checkout",
        "scn_x402_overuse",
        "scn_x402_underuse",
        "scn_stablecoin_irreversibility",
        "scn_refund_policy_neglect",
        "scn_category_drift",
    }


def test_malformed_scenario_fixture_is_rejected():
    malformed = {
        "scenario_id": "missing_required_fields",
        "title": "Invalid",
    }

    with pytest.raises(Exception):
        parse_model(Scenario, malformed)

