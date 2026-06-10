import os

import pytest

from app.providers import OpenAIResponsesProvider
from app.runner import run_phase1_evaluation

_SMOKE_MODEL = "gpt-5.4-mini"


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_OPENAI_EVAL") != "1" or not os.environ.get("OPENAI_API_KEY"),
    reason="Set RUN_LIVE_OPENAI_EVAL=1 and OPENAI_API_KEY to run the live OpenAI smoke test.",
)
def test_smoketest_openai():
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        live=True,
        provider_factory=lambda model_id, live: OpenAIResponsesProvider(model_name=_SMOKE_MODEL),
    )

    assert run.metrics["total_results"] == 1
    assert run.results[0].provider_id == "openai"
    assert run.results[0].error is None
    assert run.results[0].raw_model_output


_MULTI_SCENARIO_IDS = [
    "scn_v1_a1_trap",
    "scn_v1_a2_lookalike",
    "scn_v1_b1_trap",
    "scn_v1_b2_lookalike",
    "scn_v1_a5_trap",
]


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_OPENAI_EVAL") != "1" or not os.environ.get("OPENAI_API_KEY"),
    reason="Set RUN_LIVE_OPENAI_EVAL=1 and OPENAI_API_KEY to run the live OpenAI smoke test.",
)
def test_smoketest_openai_5_scenarios():
    """Verify gpt-5.4-mini produces valid output across 5 different scenarios."""
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=_MULTI_SCENARIO_IDS,
        seeds=[1],
        live=True,
        provider_factory=lambda model_id, live: OpenAIResponsesProvider(model_name=_SMOKE_MODEL),
    )

    assert run.metrics["total_results"] == 5
    for result in run.results:
        assert result.provider_id == "openai"
        assert result.error is None
        assert result.raw_model_output
        assert result.action is not None

    scenario_ids_returned = {r.scenario_id for r in run.results}
    assert scenario_ids_returned == set(_MULTI_SCENARIO_IDS)
