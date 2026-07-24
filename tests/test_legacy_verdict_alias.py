"""Read-time back-compat for the false_refusal -> refused_when_safe rename.

New code writes and asserts `refused_when_safe`, but runs recorded before the
2026-07 rename stored the verdict as `false_refusal` and a boolean field of the
same name. Loading such an archived run (or the pre-rename Supabase payload)
must still succeed, mapping the legacy tokens onto the new field/verdict.
"""

from app.models import EvaluationResult


def _legacy_row(**overrides) -> dict:
    base = dict(
        scenario_id="scn_v1_a1_lookalike",
        scenario_title="A1 lookalike",
        category="spend_limits",
        agent_id="openai:no_policy",
        agent_name="gpt / no policy",
        action={"action_type": "ask_approval", "approval_requested": True, "rationale": "ask"},
        verdict="false_refusal",
        false_refusal=True,
    )
    base.update(overrides)
    return base


def test_legacy_false_refusal_verdict_loads_as_refused_when_safe():
    result = EvaluationResult.model_validate(_legacy_row())
    assert result.verdict == "refused_when_safe"
    assert result.refused_when_safe is True
    # And it re-serializes under the new name only.
    dumped = result.model_dump()
    assert dumped["verdict"] == "refused_when_safe"
    assert "false_refusal" not in dumped
    assert dumped["refused_when_safe"] is True


def test_new_name_still_loads_and_is_canonical():
    result = EvaluationResult.model_validate(
        _legacy_row(verdict="refused_when_safe", refused_when_safe=True)
    )
    assert result.verdict == "refused_when_safe"
    assert result.refused_when_safe is True


def test_legacy_simulated_outcome_is_aliased():
    from app.models import AgentAction

    action = AgentAction.model_validate(
        {"action_type": "ask_approval", "simulated_outcome": "false_refusal"}
    )
    assert action.simulated_outcome == "refused_when_safe"
