import copy
import json

import pytest

from app.data import DATA_DIR, load_scenarios
from app.merge import (
    MergeIncompatible,
    compatibility_report,
    episode_key,
    merge_runs,
    superseded_run_ids,
)
from app.metrics import compute_metrics
from app.models import AgentAction, BenchmarkRun, model_to_dict, parse_model
from app.policies import evaluate_phase1_action


V2_SET = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"
# A trap/lookalike pair, so merged metrics have both an unsafe denominator and
# a refused-when-safe one rather than an empty half.
SCENARIO_IDS = ["scn_v1_a1_trap", "scn_v1_a1_lookalike"]

PURCHASE = AgentAction(
    action_type="purchase",
    amount=53.98,
    merchant_id="simulated_merchant",
    sku="charger",
    payment_type="card",
    rationale="Buy.",
)
ASK = AgentAction(action_type="ask_approval", approval_requested=True, rationale="Ask.")


def _results(condition, *, model_name="gpt-5.5", seed=1, action=PURCHASE):
    from app.data import get_scenario

    return [
        evaluate_phase1_action(
            get_scenario(scenario_id),
            "openai",
            model_name,
            "openai",
            condition,
            seed,
            action,
            action,
            "{}",
            [],
        )
        for scenario_id in SCENARIO_IDS
    ]


def _run(run_id, condition, *, created_at, model_name="gpt-5.5", seed=1, **overrides):
    results = _results(condition, model_name=model_name, seed=seed)
    fields = {
        "run_id": run_id,
        "created_at": created_at,
        "phase": "phase1",
        "agent_ids": [f"openai:{condition}"],
        "model_ids": ["openai"],
        "model_names": [model_name],
        "control_conditions": [condition],
        "seeds": [seed],
        "temperature": 0.0,
        "live": True,
        "answer_key_status": "provisional_answer",
        "scenario_ids": list(SCENARIO_IDS),
        "results": results,
        "events": [{"run_id": run_id, "event_type": "episode"}],
        "metrics": compute_metrics(results),
    }
    fields.update(overrides)
    return BenchmarkRun(**fields)


def _two_runs():
    return [
        _run("run_a", "no_policy", created_at="2026-07-01T10:00:00+00:00"),
        _run("run_b", "structured_policy", created_at="2026-07-20T10:00:00+00:00"),
    ]


def test_merged_metrics_equal_one_run_over_the_union():
    """The whole point: pooled episodes, metrics computed — never averaged."""
    runs = _two_runs()
    merged = merge_runs(runs, run_id="merged_1")

    expected = compute_metrics([result for run in runs for result in run.results])

    assert len(merged.results) == sum(len(run.results) for run in runs)
    assert merged.metrics["unsafe_payment_ci"] == expected["unsafe_payment_ci"]
    assert merged.metrics["refused_when_safe_ci"] == expected["refused_when_safe_ci"]
    assert merged.metrics["verdict_counts"] == expected["verdict_counts"]
    # Both conditions in one breakdown is the thing four separate run files
    # cannot express.
    assert set(merged.metrics["by_control_condition"]) == {"no_policy", "structured_policy"}


def test_merged_run_records_its_sources():
    runs = _two_runs()
    merged = merge_runs(runs, run_id="merged_1")

    assert [source.run_id for source in merged.merged_from] == ["run_a", "run_b"]
    assert [source.episode_count for source in merged.merged_from] == [2, 2]
    assert [source.control_conditions for source in merged.merged_from] == [
        ["no_policy"],
        ["structured_policy"],
    ]
    assert all(source.dropped_overlaps == 0 for source in merged.merged_from)
    assert merged.merged_at


def test_created_at_defaults_to_the_newest_source():
    """Pooled data is no fresher than its newest episode."""
    merged = merge_runs(_two_runs(), run_id="merged_1")
    assert merged.created_at == "2026-07-20T10:00:00+00:00"

    pinned = merge_runs(_two_runs(), run_id="merged_1", created_at="2026-08-01T00:00:00+00:00")
    assert pinned.created_at == "2026-08-01T00:00:00+00:00"


def test_axes_are_unioned():
    merged = merge_runs(_two_runs(), run_id="merged_1")
    assert merged.control_conditions == ["no_policy", "structured_policy"]
    assert merged.agent_ids == ["openai:no_policy", "openai:structured_policy"]
    assert merged.model_names == ["gpt-5.5"]
    assert merged.scenario_ids == SCENARIO_IDS


def test_argument_order_does_not_change_the_merge():
    runs = _two_runs()
    forward = merge_runs(runs, run_id="merged_1", merged_at="2026-08-01T00:00:00+00:00")
    backward = merge_runs(
        list(reversed(runs)), run_id="merged_1", merged_at="2026-08-01T00:00:00+00:00"
    )
    assert model_to_dict(forward) == model_to_dict(backward)


def test_overlapping_episodes_are_refused_by_default():
    """Same cell run twice is not extra data; pooling it would count it twice."""
    runs = [
        _run("run_a", "no_policy", created_at="2026-07-01T10:00:00+00:00"),
        _run("run_b", "no_policy", created_at="2026-07-20T10:00:00+00:00"),
    ]
    report = compatibility_report(runs)
    assert report["overlap_count"] == 2
    assert any("covered by more than one source" in reason for reason in report["blocking"])

    with pytest.raises(MergeIncompatible):
        merge_runs(runs, run_id="merged_1")


def test_prefer_newest_keeps_one_copy_and_records_the_drop():
    older = _run("run_a", "no_policy", created_at="2026-07-01T10:00:00+00:00")
    newer = _run("run_b", "no_policy", created_at="2026-07-20T10:00:00+00:00")
    merged = merge_runs([older, newer], run_id="merged_1", on_overlap="prefer-newest")

    assert len(merged.results) == 2
    by_source = {source.run_id: source for source in merged.merged_from}
    assert by_source["run_b"].episode_count == 2
    assert by_source["run_b"].dropped_overlaps == 0
    assert by_source["run_a"].episode_count == 0
    assert by_source["run_a"].dropped_overlaps == 2

    oldest_first = merge_runs([older, newer], run_id="merged_1", on_overlap="prefer-oldest")
    by_source = {source.run_id: source for source in oldest_first.merged_from}
    assert by_source["run_a"].episode_count == 2
    assert by_source["run_b"].dropped_overlaps == 2


def test_different_scenario_sets_are_refused():
    runs = _two_runs()
    runs[1].scenario_ids = [SCENARIO_IDS[0]]
    report = compatibility_report(runs)
    assert any("different scenario sets" in reason for reason in report["blocking"])


def test_different_models_are_refused():
    runs = [
        _run("run_a", "no_policy", created_at="2026-07-01T10:00:00+00:00"),
        _run(
            "run_b",
            "structured_policy",
            created_at="2026-07-20T10:00:00+00:00",
            model_name="claude-4.6",
        ),
    ]
    report = compatibility_report(runs)
    assert any("not the same model" in reason for reason in report["blocking"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("temperature", 0.7),
        ("reasoning_effort", "high"),
        ("gemini_thinking_level", "high"),
        ("live", False),
        ("phase", "phase2"),
        ("answer_key_status", "survey_locked_70"),
        # A scoped enforced arm and a full-sweep one are two designs; pooling
        # them would put both in one tool_constraints denominator.
        ("enforcement_scope", "all"),
    ],
)
def test_sampling_config_must_agree(field, value):
    runs = _two_runs()
    setattr(runs[1], field, value)
    report = compatibility_report(runs)
    assert any(f"disagree on {field}" in reason for reason in report["blocking"])


def test_merged_run_pools_the_per_condition_scenario_axes():
    """Each source ran one arm, so the pooled run has to say what each covered."""
    runs = [
        _run(
            "run_a",
            "no_policy",
            created_at="2026-07-01T10:00:00+00:00",
            enforcement_scope="rail_reachable",
            condition_scenario_ids={"no_policy": list(SCENARIO_IDS)},
        ),
        _run(
            "run_b",
            "structured_policy",
            created_at="2026-07-20T10:00:00+00:00",
            enforcement_scope="rail_reachable",
            condition_scenario_ids={"structured_policy": [SCENARIO_IDS[0]]},
        ),
    ]
    merged = merge_runs(runs, run_id="merged_scope")
    assert merged.enforcement_scope == "rail_reachable"
    assert merged.condition_scenario_ids == {
        "no_policy": list(SCENARIO_IDS),
        "structured_policy": [SCENARIO_IDS[0]],
    }


def test_one_run_is_not_a_merge():
    report = compatibility_report([_run("run_a", "no_policy", created_at="2026-07-01T10:00:00+00:00")])
    assert report["blocking"]


def test_wide_date_spread_warns_but_does_not_block():
    runs = [
        _run("run_a", "no_policy", created_at="2026-01-01T10:00:00+00:00"),
        _run("run_b", "structured_policy", created_at="2026-07-20T10:00:00+00:00"),
    ]
    report = compatibility_report(runs)
    assert not report["blocking"]
    assert any("days" in warning for warning in report["warnings"])


def test_sources_are_not_modified():
    runs = _two_runs()
    before = [model_to_dict(run) for run in runs]
    merge_runs(runs, run_id="merged_1")
    assert [model_to_dict(run) for run in runs] == before


def test_episode_key_separates_every_axis():
    result = _results("no_policy")[0]
    other = copy.deepcopy(result)
    other.seed = 2
    assert episode_key(result) != episode_key(other)

    same = copy.deepcopy(result)
    assert episode_key(result) == episode_key(same)


def test_superseded_run_ids_maps_sources_to_the_merged_run():
    runs = _two_runs()
    merged = merge_runs(runs, run_id="merged_1")
    mapping = superseded_run_ids([*runs, merged])
    assert mapping == {"run_a": "merged_1", "run_b": "merged_1"}


def test_a_run_stored_before_merging_existed_still_parses():
    payload = model_to_dict(_run("run_a", "no_policy", created_at="2026-07-01T10:00:00+00:00"))
    payload.pop("merged_from")
    payload.pop("merged_at")
    run = parse_model(BenchmarkRun, json.loads(json.dumps(payload)))
    assert run.merged_from == []
    assert run.merged_at is None


def test_phase2_block_is_rebuilt_from_the_pooled_episodes():
    """A Phase 2 merge must get its ablation breakdowns, not just the summary."""
    scenarios = [scenario.scenario_id for scenario in load_scenarios(V2_SET)][:1]
    runs = []
    for index, (run_id, condition) in enumerate(
        [("run_a", "no_policy"), ("run_b", "tool_constraints")]
    ):
        run = _run(
            run_id,
            condition,
            created_at=f"2026-07-0{index + 1}T10:00:00+00:00",
            phase="phase2",
        )
        for result in run.results:
            result.framing = "deployment"
            result.urgency = "none"
            result.user_availability = "none"
        run.framings = ["deployment"]
        run.urgencies = ["none"]
        run.user_availabilities = ["none"]
        runs.append(run)
    assert scenarios  # the v2 set loaded

    merged = merge_runs(runs, run_id="merged_1")
    phase2 = merged.metrics["phase2"]
    assert set(phase2["by_condition_and_framing"]) == {
        "no_policy/deployment",
        "tool_constraints/deployment",
    }
