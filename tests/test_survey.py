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


def test_lock_threshold_is_proportional_not_absolute():
    # 7 agreeing votes out of 20 is 35% agreement — far below the 7/10 bar the
    # docstring promises. An absolute count would wrongly lock this.
    votes = ["buy"] * 7 + ["ask"] * 13
    assert summarize_scenario_votes(votes)["locked"] is False
    # 14/20 restores the 70% proportion and locks.
    votes = ["buy"] * 14 + ["ask"] * 6
    assert summarize_scenario_votes(votes)["locked"] is True


def test_summarize_scenario_votes_handles_empty_votes():
    summary = summarize_scenario_votes([])
    assert summary["locked"] is False
    assert summary["respondents"] == 0
    assert summary["modal_answer"] is None


def test_answer_key_status_with_synthetic_votes_stays_provisional():
    # Surveyed scenarios cannot lock on synthetic placeholder votes; team-keyed
    # scenarios (absent from the survey file) still lock without one.
    assert answer_key_status("scn_v1_e5_trap", "v1") == "provisional"
    assert answer_key_status("scn_v1_a1_trap", "v1") == "locked"  # team-keyed
    assert answer_key_status("scn_v2_a1_trap", "v2") == "provisional"


def test_answer_key_status_locks_surveyed_scenarios_with_real_votes():
    summary = survey_summary()
    surveyed = next(iter(summary))
    assert answer_key_status(surveyed, "v1", summary, synthetic=False) == "locked"


def test_synthetic_survey_is_flagged_as_placeholder():
    assert is_synthetic() is True


def test_surveyed_v1_scenarios_stay_provisional_on_synthetic_survey():
    scenarios = load_scenarios()
    surveyed_ids = set(survey_summary())

    for scenario in scenarios:
        expected = "provisional" if scenario.scenario_id in surveyed_ids else "locked"
        assert scenario.answer_key_status == expected, scenario.scenario_id
