"""Phase 1 -> Phase 2 transfer check.

Reruns the v1 trap scenarios through the Phase 2 sandbox and correlates
per-scenario unsafe rates against a stored Phase 1 run. Strong correlation
validates the cheap single-shot simulation; weak correlation is itself a
finding. Caveat: v1 scenarios have no authored sandbox environments, so the
sandbox uses synthetic single-offer worlds derived from the situation text.
"""

from __future__ import annotations

from math import sqrt
from typing import Any, Dict, Iterable, List, Optional

from ..data import DEFAULT_SCENARIO_SET, load_scenarios
from ..storage import RunStorage
from .runner import DEFAULT_PHASE2_SEEDS, run_phase2_evaluation


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return round(cov / sqrt(var_x * var_y), 4)


def _per_scenario_unsafe_rates(results: Iterable[Any], scenario_ids: List[str]) -> Dict[str, float]:
    grouped: Dict[str, List[bool]] = {scenario_id: [] for scenario_id in scenario_ids}
    for result in results:
        scenario_id = result.scenario_id if hasattr(result, "scenario_id") else result["scenario_id"]
        if scenario_id in grouped:
            unsafe = result.unsafe_payment if hasattr(result, "unsafe_payment") else result["unsafe_payment"]
            grouped[scenario_id].append(bool(unsafe))
    return {
        scenario_id: round(sum(flags) / len(flags), 4)
        for scenario_id, flags in grouped.items()
        if flags
    }


def run_transfer_check(
    phase1_run_id: str,
    model_id: str = "openai",
    control_condition: str = "prompt_policy",
    seeds: Optional[List[int]] = None,
    live: bool = False,
    storage: Optional[RunStorage] = None,
) -> Dict[str, Any]:
    storage = storage or RunStorage()
    phase1_run = storage.read(phase1_run_id)

    v1_scenarios = load_scenarios(DEFAULT_SCENARIO_SET)
    trap_ids = [scenario.scenario_id for scenario in v1_scenarios if scenario.pair_role == "trap"]

    phase1_results = [
        result
        for result in phase1_run.results
        if result.model_id == model_id
        and result.control_condition == control_condition
        and result.scenario_id in trap_ids
    ]
    if not phase1_results:
        raise KeyError(
            f"Run {phase1_run_id} has no results for model={model_id}, "
            f"condition={control_condition} on the v1 trap scenarios."
        )
    phase1_rates = _per_scenario_unsafe_rates(phase1_results, trap_ids)
    covered_ids = sorted(phase1_rates)

    sandbox_run = run_phase2_evaluation(
        model_ids=[model_id],
        control_conditions=[control_condition],
        framings=["deployment"],
        scenario_ids=covered_ids,
        scenario_set_path=DEFAULT_SCENARIO_SET,
        seeds=seeds or DEFAULT_PHASE2_SEEDS,
        live=live,
    )
    sandbox_rates = _per_scenario_unsafe_rates(sandbox_run.results, covered_ids)

    rows = [
        {
            "scenario_id": scenario_id,
            "phase1_unsafe_rate": phase1_rates[scenario_id],
            "sandbox_unsafe_rate": sandbox_rates.get(scenario_id, 0.0),
        }
        for scenario_id in covered_ids
    ]
    xs = [row["phase1_unsafe_rate"] for row in rows]
    ys = [row["sandbox_unsafe_rate"] for row in rows]
    return {
        "phase1_run_id": phase1_run_id,
        "sandbox_run_id": sandbox_run.run_id,
        "model_id": model_id,
        "control_condition": control_condition,
        "live": live,
        "scenario_count": len(rows),
        "pearson_r": pearson(xs, ys),
        "rows": rows,
        "caveat": (
            "v1 scenarios run on synthetic single-offer sandbox worlds derived "
            "from the situation text; authored environments exist only for v2 A/B."
        ),
    }
