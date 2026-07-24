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
    # Real v1_web_r6 survey data: 38 team-keyed + 5 survey-locked + 3
    # objective-verdict traps lock; the 4 lookalikes that failed the
    # pre-registered lock rule are dropped from the key (2026-07-16 amendment
    # in data/survey/PHASE1_WEB_SURVEY.md).
    assert Counter(scenario.answer_key_status for scenario in scenarios) == {
        "locked": 46,
        "dropped": 4,
    }
    assert all(scenario.safe_to_act is not None for scenario in scenarios)
    assert not any("USDC" in (scenario.source_situation or "") for scenario in scenarios)
    assert not any(scenario.payment_mode in {"stablecoin_wallet", "paid_tool_or_card"} for scenario in scenarios)


def test_v2_source_path_contains_228_versioned_scenarios():
    # 250 - 22 (11 trivially-easy pairs cut 2026-07-24, concentrated in category
    # B; see the scenario-set file header and CHANGELOG for the per-pair
    # reasoning). The file keeps its v2_250 name as a stable identifier.
    scenarios = load_scenarios(Path("data/scenario_sets/v2_250_scenarios.md"))

    assert len(scenarios) == 228
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
    assert role_counts == {"trap": 114, "lookalike": 114}
    assert category_counts == {
        "spend_limits": 50,
        "authorization_scope": 30,
        "consent_and_escalation": 48,
        "privacy_and_disclosure": 50,
        "adversarial_robustness": 50,
    }
    cut_pairs = {"v2_b2", "v2_b6", "v2_b7", "v2_b9", "v2_b12", "v2_b14", "v2_b15", "v2_b16", "v2_b21", "v2_b24", "v2_c19"}
    assert cut_pairs.isdisjoint(pair_counts)


def test_semantic_only_flag_marks_exactly_the_survey_dependent_traps():
    # Regression test for the current ~18% ambiguous/objective split (see
    # CHANGELOG): a future change that raises the semantic_only share must
    # update these counts deliberately rather than drift silently.
    v2_scenarios = {
        s.scenario_id: s for s in load_scenarios(Path("data/scenario_sets/v2_250_scenarios.md"))
    }
    assert v2_scenarios["scn_v2_a25_trap"].semantic_only is True
    assert v2_scenarios["scn_v2_a25_lookalike"].semantic_only is False
    assert v2_scenarios["scn_v2_a1_trap"].semantic_only is False
    assert sum(1 for s in v2_scenarios.values() if s.semantic_only) == 44

    v1_scenarios = {s.scenario_id: s for s in load_scenarios()}
    assert sum(1 for s in v1_scenarios.values() if s.semantic_only) == 9


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
