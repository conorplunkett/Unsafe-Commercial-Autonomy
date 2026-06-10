import os

import pytest

from app.providers import OpenAIResponsesProvider
from app.runner import run_phase1_evaluation

SMOKE_TEST_MODEL = "gpt-5.4-mini"


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_OPENAI_EVAL") != "1" or not os.environ.get("OPENAI_API_KEY"),
    reason="Set RUN_LIVE_OPENAI_EVAL=1 and OPENAI_API_KEY to run the live OpenAI smoke test.",
)
def test_live_openai_smoke():
    def _factory(model_id: str, live: bool):
        return OpenAIResponsesProvider(model_name=SMOKE_TEST_MODEL)

    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        live=True,
        provider_factory=_factory,
    )

    assert run.metrics["total_results"] == 1
    assert run.results[0].provider_id == "openai"
    assert run.results[0].error is None
    assert run.results[0].raw_model_output
