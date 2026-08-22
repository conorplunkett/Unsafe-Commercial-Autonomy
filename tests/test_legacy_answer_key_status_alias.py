"""Read-time back-compat for the 2026-08 answer_key_status rename.

New code writes and asserts "survey_locked_70" / "provisional_answer" /
"excluded", but runs recorded before the rename stored these as "locked" /
"provisional" / "dropped". Loading such an archived run JSON must still
succeed, mapping the legacy value onto the new one (this is what crashed
`GET /api/runs/{run_id}` on stored runs predating the rename).
"""

from app.models import BenchmarkRun, EvaluationResult


def _legacy_result_row(**overrides) -> dict:
    base = dict(
        scenario_id="scn_v2_a1_trap",
        scenario_title="A1 trap",
        category="spend_limits",
        agent_id="openai:no_policy",
        agent_name="gpt / no policy",
        action={"action_type": "purchase", "rationale": "buy"},
        verdict="safe",
        answer_key_status="provisional",
    )
    base.update(overrides)
    return base


def test_legacy_evaluation_result_answer_key_status_aliases():
    assert EvaluationResult.model_validate(
        _legacy_result_row(answer_key_status="provisional")
    ).answer_key_status == "provisional_answer"
    assert EvaluationResult.model_validate(
        _legacy_result_row(answer_key_status="locked")
    ).answer_key_status == "survey_locked_70"
    assert EvaluationResult.model_validate(
        _legacy_result_row(answer_key_status="dropped")
    ).answer_key_status == "excluded"


def test_new_answer_key_status_values_still_load():
    for status in ("provisional_answer", "survey_locked_70", "excluded"):
        result = EvaluationResult.model_validate(
            _legacy_result_row(answer_key_status=status)
        )
        assert result.answer_key_status == status


def test_benchmark_run_answer_key_status_is_aliased():
    run = BenchmarkRun.model_validate(
        dict(
            run_id="run_legacy",
            created_at="2026-08-01T00:00:00Z",
            agent_ids=["openai:no_policy"],
            answer_key_status="provisional",
            scenario_ids=["scn_v2_a1_trap"],
            results=[_legacy_result_row()],
            events=[],
            metrics={},
        )
    )
    assert run.answer_key_status == "provisional_answer"


def test_benchmark_run_locked_answer_key_status_is_aliased():
    run = BenchmarkRun.model_validate(
        dict(
            run_id="run_legacy_locked",
            created_at="2026-08-01T00:00:00Z",
            agent_ids=["openai:no_policy"],
            answer_key_status="locked",
            scenario_ids=["scn_v2_a1_trap"],
            results=[_legacy_result_row(answer_key_status="locked")],
            events=[],
            metrics={},
        )
    )
    assert run.answer_key_status == "survey_locked_70"
