"""Read-time back-compat for the preflight_check -> required_check rename.

New code writes and asserts `required_check`, but runs recorded before the
2026-08 rename stored the condition as `preflight_check`. Loading such an
archived run JSON, checkpoint row, or pre-rename Supabase payload must still
succeed, mapping the legacy key onto the new one.
"""

from app.models import BenchmarkRun, EvaluationResult, RunRequest


def _legacy_result_row(**overrides) -> dict:
    base = dict(
        scenario_id="scn_v2_a1_trap",
        scenario_title="A1 trap",
        category="spend_limits",
        agent_id="openai:preflight_check",
        agent_name="gpt / preflight check",
        action={"action_type": "ask_approval", "approval_requested": True, "rationale": "ask"},
        verdict="safe",
        control_condition="preflight_check",
    )
    base.update(overrides)
    return base


def test_legacy_preflight_check_loads_as_required_check():
    result = EvaluationResult.model_validate(_legacy_result_row())
    assert result.control_condition == "required_check"
    # And it re-serializes under the new name only.
    assert EvaluationResult.model_validate(_legacy_result_row()).model_dump()[
        "control_condition"
    ] == "required_check"


def test_new_condition_name_still_loads():
    result = EvaluationResult.model_validate(
        _legacy_result_row(control_condition="required_check")
    )
    assert result.control_condition == "required_check"


def test_benchmark_run_condition_list_is_aliased():
    run = BenchmarkRun.model_validate(
        dict(
            run_id="run_legacy",
            created_at="2026-08-01T00:00:00Z",
            agent_ids=["openai:preflight_check"],
            control_conditions=["no_policy", "preflight_check"],
            scenario_ids=["scn_v2_a1_trap"],
            results=[_legacy_result_row()],
            events=[],
            metrics={},
        )
    )
    assert run.control_conditions == ["no_policy", "required_check"]
    assert run.results[0].control_condition == "required_check"


def test_run_request_condition_list_is_aliased():
    request = RunRequest.model_validate({"control_conditions": ["preflight_check"]})
    assert request.control_conditions == ["required_check"]
