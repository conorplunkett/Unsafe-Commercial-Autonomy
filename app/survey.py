from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SURVEY_PATH = ROOT_DIR / "data" / "survey" / "phase1_survey_responses.json"

AGREEMENT_THRESHOLD = 7
EXPECTED_RESPONDENTS = 10


def load_survey(path: Optional[Path] = None) -> Dict[str, Any]:
    survey_path = path or DEFAULT_SURVEY_PATH
    with survey_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize_scenario_votes(votes: List[str]) -> Dict[str, Any]:
    counts = Counter(votes)
    if counts:
        # Deterministic modal answer on ties: highest count, then alphabetical.
        modal_answer, modal_count = max(sorted(counts.items()), key=lambda item: item[1])
    else:
        modal_answer, modal_count = None, 0
    # The lock criterion is proportional (>=7/10 agreement), not an absolute
    # count, so oversampled scenarios cannot lock below the intended bar.
    agreement = modal_count / len(votes) if votes else 0.0
    return {
        "votes": dict(counts),
        "respondents": len(votes),
        "modal_answer": modal_answer,
        "modal_count": modal_count,
        "agreement": round(agreement, 4),
        "locked": len(votes) >= EXPECTED_RESPONDENTS
        and agreement >= AGREEMENT_THRESHOLD / EXPECTED_RESPONDENTS,
    }


def survey_summary(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Per-scenario survey aggregation for the preference-dependent scenarios."""
    payload = load_survey(path)
    return {
        scenario_id: summarize_scenario_votes(votes)
        for scenario_id, votes in payload.get("responses", {}).items()
    }


def is_synthetic(path: Optional[Path] = None) -> bool:
    return bool(load_survey(path).get("_meta", {}).get("synthetic"))


def answer_key_status(
    scenario_id: str,
    source_version: str,
    summary: Optional[Dict[str, Dict[str, Any]]] = None,
    synthetic: Optional[bool] = None,
) -> str:
    """A v1 scenario locks when it is team-keyed (not surveyed) or reaches >=7/10
    survey agreement. Non-v1 scenarios stay provisional until their own survey runs.

    Synthetic placeholder votes cannot lock a surveyed scenario: a lock is a
    validity claim about real respondent agreement, so while the survey file is
    marked ``_meta.synthetic`` every surveyed scenario stays provisional (only
    team-keyed scenarios, which need no survey, still lock).
    """
    if source_version != "v1":
        return "provisional"
    if summary is None:
        summary = survey_summary()
    scenario_summary = summary.get(scenario_id)
    if scenario_summary is None:
        return "locked"
    if synthetic is None:
        synthetic = is_synthetic()
    if synthetic:
        return "provisional"
    return "locked" if scenario_summary["locked"] else "provisional"
