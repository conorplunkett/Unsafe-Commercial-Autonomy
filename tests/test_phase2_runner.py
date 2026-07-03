"""Runner, scripted agents, provider adapters, and constraints-integrity tests."""

from __future__ import annotations

import json
import sys

import pytest

from app.data import DATA_DIR, load_scenarios
from app.models import parse_model, BenchmarkRun
from app.phase2.providers import (
    BaseEpisodeProvider,
    EpisodeResult,
    OpenWeightsToolProvider,
    ToolLoopProvider,
    resolve_phase2_model_ids,
)
from app.phase2.runner import run_phase2_evaluation
from app.phase2.sandbox import evaluate_payment_policy
from app.storage import RunStorage

V2_SET = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"
PAIR_IDS = ["scn_v2_a1_trap", "scn_v2_a1_lookalike"]


def test_runner_cardinality_and_framing():
    run = run_phase2_evaluation(
        model_ids=["scripted_diligent"],
        control_conditions=["no_policy", "tool_constraints"],
        framings=["evaluation", "deployment"],
        scenario_ids=PAIR_IDS,
        seeds=[1, 2],
    )
    assert run.phase == "phase2"
    assert len(run.results) == 1 * 2 * 2 * 2 * 2
    assert {result.framing for result in run.results} == {"evaluation", "deployment"}
    assert set(run.metrics["phase2"]["by_framing"]) == {"evaluation", "deployment"}
    assert "no_policy/evaluation" in run.metrics["phase2"]["by_condition_and_framing"]


def test_live_run_aborts_up_front_when_provider_is_misconfigured(monkeypatch):
    # A misconfigured live provider must fail the run in preflight with one
    # clear error, not walk the whole episode grid recording per-episode
    # errors and saving a junk run.
    from app.providers import ProviderError

    monkeypatch.delenv("OPENWEIGHTS_BASE_URL", raising=False)
    monkeypatch.delenv("OPENWEIGHTS_MODEL", raising=False)
    with pytest.raises(ProviderError):
        run_phase2_evaluation(
            model_ids=["openweights"],
            control_conditions=["no_policy"],
            framings=["deployment"],
            scenario_ids=PAIR_IDS,
            seeds=[1],
            live=True,
        )


def test_naive_agent_unsafe_under_no_policy_blocked_under_tool_constraints():
    run = run_phase2_evaluation(
        model_ids=["scripted_naive"],
        control_conditions=["no_policy", "tool_constraints"],
        framings=["deployment"],
        scenario_ids=PAIR_IDS,
        seeds=[1],
    )
    by_key = {(r.control_condition, r.scenario_id): r for r in run.results}
    trap_no_policy = by_key[("no_policy", "scn_v2_a1_trap")]
    assert trap_no_policy.unsafe_payment
    assert "total_cost_constraint_violation" in trap_no_policy.failure_metrics
    trap_constrained = by_key[("tool_constraints", "scn_v2_a1_trap")]
    assert not trap_constrained.unsafe_payment
    assert trap_constrained.block_reasons == ["total_cost_constraint_violation"]
    assert trap_constrained.proposed_action.action_type == "purchase"
    look_constrained = by_key[("tool_constraints", "scn_v2_a1_lookalike")]
    assert look_constrained.action.action_type == "purchase"
    assert look_constrained.verdict == "safe"


def test_diligent_agent_safe_on_enforceable_pair_and_uses_free_source():
    run = run_phase2_evaluation(
        model_ids=["scripted_diligent"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap", "scn_v2_a1_lookalike", "scn_v2_a4_trap"],
        seeds=[1],
    )
    by_id = {result.scenario_id: result for result in run.results}
    assert by_id["scn_v2_a1_trap"].verdict == "safe"
    assert by_id["scn_v2_a1_trap"].action.action_type == "ask_approval"
    assert by_id["scn_v2_a1_lookalike"].verdict == "safe"
    assert by_id["scn_v2_a1_lookalike"].action.action_type == "purchase"
    free_source = by_id["scn_v2_a4_trap"]
    assert free_source.action.action_type == "defer" and free_source.action.completed
    assert free_source.verdict == "safe"


def test_transcript_recorded_in_audit_events():
    run = run_phase2_evaluation(
        model_ids=["scripted_naive"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1],
    )
    tool_events = [event for event in run.results[0].audit_events if event["event_type"] == "tool_call"]
    assert {event["code"] for event in tool_events} >= {"search_offers", "pay", "finish"}


def test_run_round_trips_through_storage(tmp_path):
    run = run_phase2_evaluation(
        model_ids=["scripted_diligent"],
        control_conditions=["approval_gate"],
        framings=["evaluation"],
        scenario_ids=PAIR_IDS,
        seeds=[1],
    )
    storage = RunStorage(root=tmp_path)
    storage.save(run)
    loaded = storage.read(run.run_id)
    assert isinstance(loaded, BenchmarkRun)
    assert loaded.phase == "phase2"
    assert loaded.framings == ["evaluation"]


def test_provider_error_becomes_defer_with_error():
    class ExplodingProvider(BaseEpisodeProvider):
        provider_id = "exploding"
        model_name = "exploding"

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            return EpisodeResult(error="simulated provider failure")

    run = run_phase2_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1],
        provider_factory=lambda model_id, live: ExplodingProvider(),
    )
    result = run.results[0]
    assert result.error == "simulated provider failure"
    assert result.action.action_type == "defer"
    assert run.metrics["error_count"] == 1


def test_unknown_inputs_rejected():
    with pytest.raises(KeyError):
        run_phase2_evaluation(model_ids=["gpt-12"])
    with pytest.raises(KeyError):
        run_phase2_evaluation(control_conditions=["super_policy"], scenario_ids=PAIR_IDS)
    with pytest.raises(KeyError):
        run_phase2_evaluation(framings=["covert"], scenario_ids=PAIR_IDS)
    assert resolve_phase2_model_ids(["all"]) == [
        "openai",
        "anthropic",
        "openweights",
        "scripted_diligent",
        "scripted_naive",
    ]


def test_tool_loop_provider_drives_world_via_stub_transport():
    """The shared live loop translates tool calls into world updates."""

    class StubProvider(ToolLoopProvider):
        provider_id = "stub"
        model_name = "stub"

        def __init__(self):
            self.turn = 0

        def start_conversation(self, system_prompt, user_prompt, tools, temperature):
            self.tools = tools
            assert any(tool["name"] == "pay" for tool in tools)

        def step(self, tool_results):
            self.turn += 1
            if self.turn == 1:
                return "", [{"id": "c1", "name": "search_offers", "arguments": {}}]
            if self.turn == 2:
                assert tool_results and "offers" in tool_results[0]["content"]
                return "", [{"id": "c2", "name": "pay", "arguments": {"offer_id": "off_1"}}]
            return "", [
                {"id": "c3", "name": "finish", "arguments": {"summary": "done", "action_taken": "purchased"}}
            ]

    run = run_phase2_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_lookalike"],
        seeds=[1],
        live=True,
        provider_factory=lambda model_id, live: StubProvider(),
    )
    result = run.results[0]
    assert result.action.action_type == "purchase"
    assert result.verdict == "safe"


def test_openweights_adapter_message_translation(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {"name": "request_approval", "arguments": '{"reason": "checking"}'},
                                }
                            ],
                        }
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["body"] = json
        return FakeResponse()

    monkeypatch.setattr("app.phase2.providers.httpx.post", fake_post)
    provider = OpenWeightsToolProvider(model_name="local-model", base_url="http://127.0.0.1:9")
    provider.start_conversation("sys", "user", [{"name": "request_approval", "description": "d", "parameters": {"type": "object", "properties": {}}}], 0.5)
    text, tool_calls = provider.step(None)
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["body"]["tools"][0]["function"]["name"] == "request_approval"
    assert tool_calls == [{"id": "call_1", "name": "request_approval", "arguments": {"reason": "checking"}}]


def test_phase1_cli_does_not_import_phase2(tmp_path):
    import subprocess

    code = (
        "import sys, app.cli; "
        "assert not any(name.startswith('app.phase2') for name in sys.modules), sys.modules.keys(); "
        "print('clean')"
    )
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert "clean" in completed.stdout


# ---------------------------------------------------------------------------
# v2 constraints data integrity
# ---------------------------------------------------------------------------

def test_v2_constraints_cover_all_scenarios_and_are_consistent():
    constraints = json.loads((DATA_DIR / "answer_keys" / "v2_constraints.json").read_text())
    constraints.pop("_meta")
    scenarios = {scenario.scenario_id: scenario for scenario in load_scenarios(V2_SET)}
    assert set(constraints) == set(scenarios), (
        f"constraint keys don't match scenario ids: "
        f"extra={set(constraints)-set(scenarios)}, missing={set(scenarios)-set(constraints)}"
    )
    assert len(constraints) == 250

    policy_fields = [
        "max_total_spend", "approval_threshold", "allowed_merchants",
        "allow_subscriptions", "allowed_payment_types", "privacy_allowed_fields",
        "refundable_only", "prohibited_categories", "prohibit_unclear_ingredients",
    ]
    for scenario_id, entry in constraints.items():
        assert "expected_action" in entry, scenario_id
        assert "acceptable_actions" in entry, scenario_id
        assert isinstance(entry["acceptable_actions"], list), scenario_id
        assert len(entry["acceptable_actions"]) >= 1, scenario_id
        assert "safe_to_act" in entry, scenario_id

        # Every v2 scenario now carries an authored sandbox environment.
        environment = entry["environment"]
        offers = environment["offers"]
        assert offers, scenario_id
        required_fields = environment["checkout_required_fields"]
        policy = {key: entry[key] for key in policy_fields if key in entry}
        scenario = scenarios[scenario_id]

        for offer in offers:
            computed = round(
                offer["price"] + offer["shipping"] + offer["tax"]
                + sum(fee["amount"] for fee in offer["fees"]), 2,
            )
            assert abs(offer["total"] - computed) < 0.005, (scenario_id, offer["offer_id"])
            assert offer["page_text"] == scenario.source_situation, (scenario_id, offer["offer_id"])

        # Required checkout fields never leak past a configured allowlist:
        # the default pay path must not be a privacy trap by construction.
        allowed = set(policy.get("privacy_allowed_fields") or [])
        if allowed:
            assert set(required_fields) <= allowed or scenario.pair_role == "trap", scenario_id

        decisions = {
            offer["offer_id"]: evaluate_payment_policy(
                policy, offer, disclosed_fields=list(required_fields)
            ).decision
            for offer in offers
        }

        if "purchase" in entry["acceptable_actions"] and not (
            scenario.pair_role == "trap" and environment.get("semantic_only")
        ):
            assert "allow" in decisions.values(), (scenario_id, decisions)

        if scenario.pair_role == "trap" and not environment.get("semantic_only"):
            assert any(d != "allow" for d in decisions.values()), (scenario_id, decisions)

        if scenario.pair_role == "lookalike":
            assert "allow" in decisions.values() or "purchase" not in entry["acceptable_actions"], (
                scenario_id, decisions,
            )

        # Privacy traps: disclosing the flagged fields must trip the engine.
        for field_name in environment.get("unsafe_disclosure", []):
            worst = evaluate_payment_policy(
                policy, offers[0], disclosed_fields=list(required_fields) + [field_name]
            )
            assert worst.decision == "block", (scenario_id, field_name)
            assert "privacy_leakage" in worst.reasons, (scenario_id, field_name)
