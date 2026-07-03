from collections import Counter
from pathlib import Path

import pytest

from app.data import load_scenarios
from app.models import Scenario, parse_model


def test_default_source_contains_v1_fifty_scenarios():
    scenarios = load_scenarios()

    assert len(scenarios) == 50
    assert scenarios[0].scenario_id == "scn_v1_a1_trap"
    assert scenarios[0].pair_id == "v1_a1"
    assert scenarios[0].pair_role == "trap"
    assert scenarios[0].stakes == "low"
    assert scenarios[0].source_situation
    assert scenarios[0].right_answer
    assert scenarios[0].answer_key_status == "locked"
    assert scenarios[0].safe_to_act is False

    pair_counts = Counter(scenario.pair_id for scenario in scenarios)
    role_counts = Counter(scenario.pair_role for scenario in scenarios)
    category_counts = Counter(scenario.category for scenario in scenarios)

    assert set(pair_counts.values()) == {2}
    assert role_counts == {"trap": 25, "lookalike": 25}
    assert category_counts == {
        "spend_limits": 10,
        "authorization_scope": 10,
        "consent_and_escalation": 10,
        "privacy_and_disclosure": 10,
        "adversarial_robustness": 10,
    }

    assert {scenario.payment_mode for scenario in scenarios} == {"delegated_card"}
    assert all(scenario.payment_policy["allowed_payment_types"] == ["card"] for scenario in scenarios)
    # Team-keyed scenarios lock; the surveyed ones stay provisional while the
    # shipped survey file is synthetic placeholder data.
    assert Counter(scenario.answer_key_status for scenario in scenarios) == {
        "locked": 38,
        "provisional": 12,
    }
    assert all(scenario.safe_to_act is not None for scenario in scenarios)
    assert not any("USDC" in (scenario.source_situation or "") for scenario in scenarios)
    assert not any(scenario.payment_mode in {"stablecoin_wallet", "paid_tool_or_card"} for scenario in scenarios)


def test_v2_source_path_contains_250_versioned_scenarios():
    scenarios = load_scenarios(Path("data/scenario_sets/v2_250_scenarios.md"))

    assert len(scenarios) == 250
    assert scenarios[0].scenario_id == "scn_v2_a1_trap"
    assert scenarios[0].pair_id == "v2_a1"
    assert scenarios[0].phase == "phase2"
    assert scenarios[0].payment_policy["source_set"] == "v2_250_scenarios"
    assert scenarios[0].payment_policy["source_version"] == "v2"
    assert scenarios[0].payment_policy["source_format"] == "scenario_set_markdown"

    pair_counts = Counter(scenario.pair_id for scenario in scenarios)
    role_counts = Counter(scenario.pair_role for scenario in scenarios)
    category_counts = Counter(scenario.category for scenario in scenarios)

    assert set(pair_counts.values()) == {2}
    assert role_counts == {"trap": 125, "lookalike": 125}
    assert category_counts == {
        "spend_limits": 50,
        "authorization_scope": 50,
        "consent_and_escalation": 50,
        "privacy_and_disclosure": 50,
        "adversarial_robustness": 50,
    }


def test_malformed_scenario_fixture_is_rejected():
    malformed = {
        "scenario_id": "missing_required_fields",
        "title": "Invalid",
    }

    with pytest.raises(Exception):
        parse_model(Scenario, malformed)


def test_v1_constraints_are_merged_into_payment_policy():
    scenarios = {scenario.scenario_id: scenario for scenario in load_scenarios()}

    assert scenarios["scn_v1_a1_trap"].payment_policy["max_total_spend"] == 50.0
    assert scenarios["scn_v1_c1_trap"].payment_policy["approval_threshold"] == 100.0
    assert "costco_business" in scenarios["scn_v1_b1_trap"].payment_policy["allowed_merchants"]
    assert scenarios["scn_v1_e5_trap"].payment_policy["refundable_only"] is True
    assert all(
        "expected_action" in scenario.payment_policy for scenario in scenarios.values()
    )
