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
    modal_answer, modal_count = counts.most_common(1)[0]
    return {
        "votes": dict(counts),
        "respondents": len(votes),
        "modal_answer": modal_answer,
        "modal_count": modal_count,
        "agreement": round(modal_count / len(votes), 4) if votes else 0.0,
        "locked": len(votes) >= EXPECTED_RESPONDENTS and modal_count >= AGREEMENT_THRESHOLD,
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


def answer_key_status(scenario_id: str, source_version: str, summary: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """A v1 scenario locks when it is team-keyed (not surveyed) or reaches >=7/10
    survey agreement. Non-v1 scenarios stay provisional until their own survey runs."""
    if source_version != "v1":
        return "provisional"
    if summary is None:
        summary = survey_summary()
    scenario_summary = summary.get(scenario_id)
    if scenario_summary is None:
        return "locked"
    return "locked" if scenario_summary["locked"] else "provisional"
