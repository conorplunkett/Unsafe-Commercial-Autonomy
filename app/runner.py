from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional
from uuid import uuid4

from .agents import AGENT_IDS, AGENT_PROFILES, get_agent_action
from .data import load_scenarios
from .metrics import compute_metrics
from .models import BenchmarkRun, EvaluationResult, Scenario
from .policies import evaluate_action


def _select_scenarios(scenario_ids: Optional[Iterable[str]]) -> List[Scenario]:
    scenarios = load_scenarios()
    if not scenario_ids:
        return scenarios
    selected_ids = set(scenario_ids)
    selected = [scenario for scenario in scenarios if scenario.scenario_id in selected_ids]
    missing = selected_ids - {scenario.scenario_id for scenario in selected}
    if missing:
        raise KeyError(f"Unknown scenarios: {', '.join(sorted(missing))}")
    return selected


def _select_agents(agent_ids: Optional[Iterable[str]]) -> List[str]:
    if not agent_ids:
        return AGENT_IDS
    selected = list(agent_ids)
    missing = set(selected) - set(AGENT_IDS)
    if missing:
        raise KeyError(f"Unknown agents: {', '.join(sorted(missing))}")
    return selected


def run_benchmark(
    agent_ids: Optional[Iterable[str]] = None,
    scenario_ids: Optional[Iterable[str]] = None,
) -> BenchmarkRun:
    selected_agents = _select_agents(agent_ids)
    selected_scenarios = _select_scenarios(scenario_ids)
    results: List[EvaluationResult] = []
    events = []
    run_id = f"run_{uuid4().hex[:12]}"

    for scenario in selected_scenarios:
        for agent_id in selected_agents:
            profile = AGENT_PROFILES[agent_id]
            action = get_agent_action(agent_id, scenario)
            result = evaluate_action(scenario, agent_id, profile["name"], action)
            results.append(result)
            for index, event in enumerate(result.audit_events):
                events.append(
                    {
                        "event_id": f"{run_id}_{scenario.scenario_id}_{agent_id}_{index}",
                        "run_id": run_id,
                        "scenario_id": scenario.scenario_id,
                        "agent_id": agent_id,
                        **event,
                    }
                )

    return BenchmarkRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        agent_ids=selected_agents,
        scenario_ids=[scenario.scenario_id for scenario in selected_scenarios],
        results=results,
        events=events,
        metrics=compute_metrics(results),
    )

