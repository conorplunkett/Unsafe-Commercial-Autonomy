from app.data import load_scenarios
from app.survey import answer_key_status, is_synthetic, summarize_scenario_votes, survey_summary


def test_survey_summary_aggregates_votes_with_agreement():
    summary = survey_summary()

    assert summary, "survey responses should not be empty"
    for scenario_id, votes in summary.items():
        assert scenario_id.startswith("scn_v1_")
        assert votes["respondents"] == 10
        assert votes["modal_count"] >= 7
        assert votes["locked"] is True


def test_summarize_scenario_votes_below_threshold_does_not_lock():
    votes = ["buy"] * 6 + ["ask"] * 4

    summary = summarize_scenario_votes(votes)

    assert summary["modal_answer"] == "buy"
    assert summary["modal_count"] == 6
    assert summary["locked"] is False


def test_answer_key_status_locks_v1_and_keeps_v2_provisional():
    assert answer_key_status("scn_v1_e5_trap", "v1") == "locked"
    assert answer_key_status("scn_v1_a1_trap", "v1") == "locked"  # team-keyed
    assert answer_key_status("scn_v2_a1_trap", "v2") == "provisional"


def test_synthetic_survey_is_flagged_as_placeholder():
    assert is_synthetic() is True


def test_all_v1_scenarios_lock_with_synthetic_survey():
    scenarios = load_scenarios()

    assert all(scenario.answer_key_status == "locked" for scenario in scenarios)
