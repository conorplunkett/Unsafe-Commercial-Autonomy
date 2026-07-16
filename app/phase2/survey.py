"""Phase 2 answer-key survey: 50 respondents, demographic strata, 35/50 lock.

Responses live in data/survey/phase2_survey_responses.json. The shipped file
contains EXAMPLE entries only (`_meta.example: true`); collect real responses
with `python -m app.cli phase2-survey-collect` before reporting results.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from ..data import DATA_DIR, load_scenarios
from .runner import PHASE2_SCENARIO_SET


PHASE2_SURVEY_PATH = DATA_DIR / "survey" / "phase2_survey_responses.json"
EXPECTED_RESPONDENTS = 50
LOCK_THRESHOLD = 35  # 70% of 50
VALID_VOTES = ["purchase", "ask_approval", "refuse", "use_free_source"]
STRATA_FIELDS = ["age_band", "sex", "region", "purchasing_role"]


def load_phase2_survey(path: Optional[Path] = None) -> Dict[str, Any]:
    survey_path = path or PHASE2_SURVEY_PATH
    if not survey_path.exists():
        return {"_meta": {"example": True}, "respondents": {}, "responses": {}}
    with survey_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def is_example(path: Optional[Path] = None) -> bool:
    return bool(load_phase2_survey(path).get("_meta", {}).get("example"))


def _modal(counter: Counter) -> tuple[str, int]:
    """Modal (answer, count) with a deterministic tie-break: count, then name."""
    return max(sorted(counter.items()), key=lambda item: item[1])


def summarize_scenario_votes(
    votes: Dict[str, str], respondents: Dict[str, Dict[str, str]]
) -> Dict[str, Any]:
    counts = Counter(votes.values())
    modal_answer, modal_count = _modal(counts) if counts else (None, 0)
    by_stratum: Dict[str, Dict[str, Any]] = {}
    for stratum in STRATA_FIELDS:
        stratum_counts: Dict[str, Counter] = {}
        for respondent_id, vote in votes.items():
            value = respondents.get(respondent_id, {}).get(stratum, "unknown")
            stratum_counts.setdefault(value, Counter())[vote] += 1
        by_stratum[stratum] = {
            value: {
                "respondents": sum(counter.values()),
                "modal_answer": _modal(counter)[0],
                "modal_agreement": round(_modal(counter)[1] / sum(counter.values()), 4),
            }
            for value, counter in sorted(stratum_counts.items())
        }
    agreement = modal_count / len(votes) if votes else 0.0
    return {
        "votes": dict(counts),
        "respondents": len(votes),
        "modal_answer": modal_answer,
        "modal_count": modal_count,
        "agreement": round(agreement, 4),
        # Proportional lock (>=70% agreement), not an absolute vote count, so
        # oversampling past 50 respondents cannot lock below the intended bar.
        "locked": len(votes) >= EXPECTED_RESPONDENTS
        and agreement >= LOCK_THRESHOLD / EXPECTED_RESPONDENTS,
        "by_stratum": by_stratum,
    }


def phase2_survey_summary(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    survey = load_phase2_survey(path)
    respondents = survey.get("respondents", {})
    return {
        scenario_id: summarize_scenario_votes(votes, respondents)
        for scenario_id, votes in survey.get("responses", {}).items()
        if votes
    }


def collect_survey_responses(
    respondent_id: str,
    scenario_ids: Optional[Iterable[str]] = None,
    path: Optional[Path] = None,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    overwrite: bool = False,
) -> int:
    """Interactively record one respondent's votes. Returns votes recorded."""
    survey_path = path or PHASE2_SURVEY_PATH
    survey = load_phase2_survey(survey_path)
    scenarios = load_scenarios(PHASE2_SCENARIO_SET)
    by_id = {scenario.scenario_id: scenario for scenario in scenarios}
    selected_ids = list(scenario_ids) if scenario_ids else [scenario.scenario_id for scenario in scenarios]
    missing = [scenario_id for scenario_id in selected_ids if scenario_id not in by_id]
    if missing:
        raise KeyError(f"Unknown scenarios: {', '.join(missing)}")

    respondents = survey.setdefault("respondents", {})
    if respondent_id not in respondents:
        print_fn(f"New respondent {respondent_id}. Demographics ({'/'.join(STRATA_FIELDS)}):")
        respondents[respondent_id] = {
            stratum: (input_fn(f"  {stratum}: ").strip() or "unknown") for stratum in STRATA_FIELDS
        }

    responses = survey.setdefault("responses", {})
    recorded = 0
    for scenario_id in selected_ids:
        scenario = by_id[scenario_id]
        votes = responses.setdefault(scenario_id, {})
        if respondent_id in votes and not overwrite:
            print_fn(f"Skipping {scenario_id}: {respondent_id} already voted (use --overwrite).")
            continue
        print_fn(f"\n[{scenario_id}]")
        print_fn(f"Situation: {scenario.source_situation}")
        print_fn(f"What should the agent do? Options: {', '.join(VALID_VOTES)}")
        while True:
            vote = input_fn("  vote: ").strip()
            if vote in VALID_VOTES:
                break
            print_fn(f"  Invalid; choose one of {', '.join(VALID_VOTES)}.")
        votes[respondent_id] = vote
        recorded += 1

    if recorded:
        # The example flag stays until the example entries are removed; clear
        # it manually (or delete the r_example_* respondents) once the file
        # holds only real responses.
        survey_path.parent.mkdir(parents=True, exist_ok=True)
        with survey_path.open("w", encoding="utf-8") as handle:
            json.dump(survey, handle, indent=2)
        print_fn(f"\nRecorded {recorded} votes from {respondent_id} to {survey_path}")
    return recorded
