"""Score the Phase 2 web survey export against the pre-registered rules.

Reads a raw response export (the JSON array of ``phase2_survey_responses``
rows downloaded from the admin dashboard / Supabase — it contains PII and must
NEVER be committed) and writes the two committed artifacts:

- ``data/survey/phase2_results_v2_web_r3.json`` — anonymized aggregates:
  per-scenario vote counts on raw slot keys, lock state, key agreement,
  the cal_1 reflexive-ask floor, demographics, exclusion counts.
- ``data/survey/phase2_survey_responses.json`` — anonymized per-respondent
  votes (slot keys preserved verbatim, per the pre-registration's import
  rule), which is the file ``answer_key_status`` reads to lock scenarios.

The rules implemented here are the binding ones in
``data/survey/PHASE2_WEB_SURVEY.md`` (exclusions, lock, acceptability); the
JS in ``web/public/admin.html`` mirrors them for live monitoring. The
instrument itself is parsed out of ``web/public/survey.html`` rather than
re-declared, so this module cannot drift from the ballot respondents saw.

Run: ``python scripts/analyze_phase2_survey.py <raw_export.json>``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..data import DATA_DIR, ROOT_DIR, load_scenarios
from .runner import PHASE2_SCENARIO_SET
from .survey import (
    ACCEPT_THRESHOLD,
    EXPECTED_RESPONDENTS,
    LOCK_THRESHOLD,
    PHASE2_SURVEY_PATH,
    STRATA_FIELDS,
    crowd_answer_agrees_with_key,
)

SURVEY_HTML_PATH = ROOT_DIR / "web" / "public" / "survey.html"
DEFAULT_OUT_PATH = DATA_DIR / "survey" / "phase2_results_v2_web_r3.json"
# Committed record of every key the survey moved: what the team had authored,
# what the crowd locked, and the vote that did it. The re-key is applied at load
# time and v2_constraints.json keeps the pre-registered guess, so this file is
# where the divergence stays auditable.
DEFAULT_REKEY_LEDGER_PATH = DATA_DIR / "survey" / "phase2_rekey_ledger.json"

LAUNCH_VERSION = "v2_web_r3"
# Phase 1's 120 s floor for 14 items, scaled to 49 answered items and rounded
# down (pre-registered).
MIN_DURATION_SECONDS = 390
ATTENTION_IDS = ["att_1", "att_2", "att_3", "att_4", "att_5"]
# One instructed-response miss is tolerated as a stray tap; two or more exclude.
MAX_TOLERATED_ATTENTION_MISSES = 1
CALIBRATION_ID = "cal_1"
DEMOGRAPHIC_FIELDS = STRATA_FIELDS + ["industry", "agent_purchase_comfort"]

# Keys that must never appear in a committed artifact. "email" is checked as a
# dict key (not a substring) because the word appears in instrument prose.
FORBIDDEN_KEYS = {"respondent_name", "email", "created_at", "user_agent", "question_order"}

# Exclusion rule 3 (PHASE2_WEB_SURVEY.md): responses from project team members
# are excluded entirely. Emails are matched as SHA-256 digests of the
# lowercased, trimmed address, so the rule is verifiable in the open repo
# without committing an address. The admin dashboard mirrors this check.
TEAM_EMAIL_SHA256 = frozenset(
    {
        "eee28b31061efde1f7e21967f0ca8e50560430ba00074d3f279ea70148fbf561",
        "ac32a773f4e18242157fedef960c29280b3d7cca6ae198dfb76116e7dcc27add",
    }
)


def is_team_member(row: Dict[str, Any]) -> bool:
    email = str(row.get("email") or "").strip().lower()
    if not email:
        return False
    return hashlib.sha256(email.encode("utf-8")).hexdigest() in TEAM_EMAIL_SHA256


def load_instrument(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """The QUESTIONS array as shipped in survey.html — the single source of
    truth for item ids, option keys, and labels."""
    html = (path or SURVEY_HTML_PATH).read_text(encoding="utf-8")
    match = re.search(r"^const QUESTIONS = (\[.*?^\]);", html, re.S | re.M)
    if not match:
        raise SystemExit(f"Could not find QUESTIONS in {path or SURVEY_HTML_PATH}")
    return json.loads(match.group(1))


def scenario_questions(instrument: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [q for q in instrument if not q.get("attention") and not q.get("calibration")]


def attention_fail_count(row: Dict[str, Any]) -> int:
    attention = row.get("attention") or {}
    return sum(1 for att in ATTENTION_IDS if not (attention.get(att) or {}).get("passed"))


def exclusion_reasons(row: Dict[str, Any]) -> List[str]:
    reasons = []
    if (row.get("meta") or {}).get("test"):
        reasons.append("test_run")
    if is_team_member(row):
        reasons.append("team_member")
    fails = attention_fail_count(row)
    if fails > MAX_TOLERATED_ATTENTION_MISSES:
        reasons.append("failed_attention_checks")
    if (row.get("duration_seconds") or 0) < MIN_DURATION_SECONDS:
        reasons.append("too_fast")
    if (row.get("meta") or {}).get("survey_version") != LAUNCH_VERSION:
        reasons.append("non_launch_version")
    return reasons


def is_clean(row: Dict[str, Any]) -> bool:
    return not exclusion_reasons(row)


def question_stats(
    question: Dict[str, Any],
    clean: Sequence[Dict[str, Any]],
    acceptable_actions: Sequence[str],
    rekey: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pre-registered per-item aggregates on raw slot keys.

    ``proceed_trap`` and ``proceed_safe`` are never merged; a tie for the top
    vote breaks by instrument option order (a tie caps agreement at 50%, so
    the tie-break can never decide a lock). ``denom`` is the clean-respondent
    count: acceptability is a claim about the whole sample, answered or not.
    """
    option_keys = [option["key"] for option in question.get("options") or []]
    counts = {key: 0 for key in option_keys}
    accept_counts = {key: 0 for key in option_keys}
    for row in clean:
        vote = (row.get("votes") or {}).get(question["id"])
        if vote in counts:
            counts[vote] += 1
        also = set((row.get("also_acceptable") or {}).get(question["id"]) or [])
        for key in option_keys:
            if key == vote or key in also:
                accept_counts[key] += 1
    answered = sum(counts.values())
    denom = len(clean)
    modal = max(option_keys, key=lambda key: counts[key]) if option_keys and answered else None
    modal_count = counts.get(modal, 0) if modal else 0
    agreement = modal_count / answered if answered else 0.0
    locked = (
        answered >= EXPECTED_RESPONDENTS
        and agreement >= LOCK_THRESHOLD / EXPECTED_RESPONDENTS
    )
    acceptable_slots = [
        key
        for key in option_keys
        # proceed_fabricate is never keyed acceptable, by pre-registration.
        if key != "proceed_fabricate" and denom and accept_counts[key] / denom >= ACCEPT_THRESHOLD
    ]
    if not locked:
        key_agreement = "collecting"
    elif rekey:
        # `acceptable_actions` is the effective key, which already carries this
        # re-key, so the agreement check would read "match" and hide the move.
        key_agreement = "rekeyed"
    elif crowd_answer_agrees_with_key(modal, acceptable_actions):
        key_agreement = "match"
    else:
        key_agreement = "conflict"
    return {
        "id": question["id"],
        "text": question["text"],
        "options": [
            {"key": option["key"], "label": option["label"]}
            for option in question.get("options") or []
        ],
        "n": answered,
        "denom": denom,
        "counts": counts,
        "accept_counts": accept_counts,
        "modal": modal,
        "agreement": round(agreement, 4),
        "locked": locked,
        "acceptable_slots": acceptable_slots,
        "key_acceptable_actions": list(acceptable_actions),
        "key_agreement": key_agreement,
        "survey_rekey": rekey,
    }


def reflexive_ask_floor(clean: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Share of clean respondents who asked on cal_1, the maximally-easy
    purchase — the floor against which every scenario's ask rate is read."""
    answers = [
        ((row.get("meta") or {}).get("calibration") or {}).get(CALIBRATION_ID)
        for row in clean
    ]
    answers = [answer for answer in answers if answer]
    asks = sum(1 for answer in answers if answer == "ask_approval")
    return {
        "n": len(answers),
        "ask": asks,
        "ask_share": round(asks / len(answers), 4) if answers else None,
    }


def demographics(clean: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    return {
        field: dict(Counter((row.get(field) or "unknown") for row in clean))
        for field in DEMOGRAPHIC_FIELDS
    }


def instrument_corpus(instrument: Sequence[Dict[str, Any]]) -> str:
    """Every string the instrument itself contains, lowercased.

    The aggregate embeds question texts and option labels verbatim, so this is
    text a committed artifact carries even with zero respondents. The PII scan
    uses it to tell a leak from a collision: a respondent who happens to be
    named after an instrument word ("Bill", "Alice", "Denver") is
    unidentifiable in output that would contain that word regardless.
    """
    return json.dumps(instrument, ensure_ascii=False).lower()


def assert_no_pii(payload: Any, rows: Sequence[Dict[str, Any]], corpus: str = "") -> None:
    serialized = json.dumps(payload, ensure_ascii=False)

    def walk_strings(value: Any) -> Iterable[str]:
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_strings(child)

    for text in walk_strings(payload):
        for token in re.findall(r"\S+@\S+", text):
            if token.lower() not in corpus:
                raise SystemExit("PII check failed: '@' found in the output payload")

    def walk_keys(value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_keys(child)

    forbidden = FORBIDDEN_KEYS & set(walk_keys(payload))
    if forbidden:
        raise SystemExit(f"PII check failed: forbidden keys in output: {sorted(forbidden)}")
    lowered = serialized.lower()
    for row in rows:
        for field in ("respondent_name", "email"):
            value = str(row.get(field) or "").lower()
            if len(value) >= 4 and value in lowered and value not in corpus:
                raise SystemExit(f"PII check failed: a raw {field} value appears in the output")


def analyze(
    rows: Sequence[Dict[str, Any]],
    instrument: Optional[Sequence[Dict[str, Any]]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    if instrument is None:
        instrument = load_instrument()
    # The loader has already adopted any survey re-key, so `keyed` is the
    # effective key — what results are actually scored against. `rekeys` carries
    # what it was before the crowd moved it.
    scenarios = load_scenarios(PHASE2_SCENARIO_SET)
    keyed = {
        scenario.scenario_id: list(scenario.payment_policy.get("acceptable_actions") or [])
        for scenario in scenarios
    }
    rekeys = {
        scenario.scenario_id: scenario.payment_policy["survey_rekey"]
        for scenario in scenarios
        if scenario.payment_policy.get("survey_rekey")
    }
    clean = [row for row in rows if is_clean(row)]
    reason_counts: Counter = Counter()
    for row in rows:
        for reason in exclusion_reasons(row):
            reason_counts[reason] += 1
    questions = [
        question_stats(
            question, clean, keyed.get(question["id"], []), rekeys.get(question["id"])
        )
        for question in scenario_questions(instrument)
    ]
    lock_states = Counter(question["key_agreement"] for question in questions)
    payload = {
        "_meta": {
            "kind": "phase2_web_survey_results",
            "instrument_version": LAUNCH_VERSION,
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "script": "scripts/analyze_phase2_survey.py",
            "preregistration": "data/survey/PHASE2_WEB_SURVEY.md",
            "lock_threshold": LOCK_THRESHOLD / EXPECTED_RESPONDENTS,
            "lock_min_respondents": EXPECTED_RESPONDENTS,
            "accept_threshold": ACCEPT_THRESHOLD,
            "min_duration_seconds": MIN_DURATION_SECONDS,
            "max_tolerated_attention_misses": MAX_TOLERATED_ATTENTION_MISSES,
            "pii": "aggregates only; raw exports stay out of the repo",
        },
        "respondents": {
            "total": len(rows),
            "clean": len(clean),
            "excluded": len(rows) - len(clean),
            "exclusion_reasons": dict(reason_counts),
        },
        "calibration": reflexive_ask_floor(clean),
        "questions": questions,
        "lock_summary": {
            "locked": lock_states.get("match", 0),
            # Locked too, and scored — but on a key the crowd moved, not the one
            # the team authored.
            "rekeyed": lock_states.get("rekeyed", 0),
            "conflict": lock_states.get("conflict", 0),
            "collecting": lock_states.get("collecting", 0),
            "total": len(questions),
        },
        "demographics": demographics(clean),
    }
    assert_no_pii(payload, rows, instrument_corpus(instrument))
    return payload


def votes_file_payload(
    rows: Sequence[Dict[str, Any]],
    instrument: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Anonymized per-respondent votes in the phase2_survey_responses.json
    format, slot keys and ``also_acceptable`` sets preserved verbatim
    (pre-registered import rule). Only clean respondents enter: this file is
    what locks the answer key, and it also feeds acceptability (lock rule 2),
    so the marks travel with the votes. ``ballots`` records the slot keys each
    item offered — a zero is only citable if the option's existence is on
    record."""
    if instrument is None:
        instrument = load_instrument()
    scenario_items = scenario_questions(instrument)
    scenario_ids = [question["id"] for question in scenario_items]
    clean = [row for row in rows if is_clean(row)]
    respondents: Dict[str, Dict[str, str]] = {}
    responses: Dict[str, Dict[str, str]] = {scenario_id: {} for scenario_id in scenario_ids}
    also_acceptable: Dict[str, Dict[str, List[str]]] = {
        scenario_id: {} for scenario_id in scenario_ids
    }
    for index, row in enumerate(clean, start=1):
        respondent_id = f"r{index:03d}"
        respondents[respondent_id] = {
            field: (row.get(field) or "unknown") for field in STRATA_FIELDS
        }
        votes = row.get("votes") or {}
        marks = row.get("also_acceptable") or {}
        for scenario_id in scenario_ids:
            vote = votes.get(scenario_id)
            if vote:
                responses[scenario_id][respondent_id] = vote
            marked = marks.get(scenario_id) or []
            if marked:
                also_acceptable[scenario_id][respondent_id] = list(marked)
    payload = {
        "_meta": {
            "description": (
                "Phase 2 answer-key survey votes, imported from the web instrument "
                "by scripts/analyze_phase2_survey.py. Votes and also-acceptable "
                "marks are ballot slot keys, preserved verbatim; respondent "
                "identities are anonymized. The coarse CLI vocabulary remains "
                "valid for the fallback collector "
                "(`python -m app.cli phase2-survey-collect`)."
            ),
            "instrument_version": LAUNCH_VERSION,
            "expected_respondents": EXPECTED_RESPONDENTS,
            "lock_threshold": LOCK_THRESHOLD,
            "accept_threshold": ACCEPT_THRESHOLD,
            "strata": STRATA_FIELDS,
            "valid_votes": [
                "proceed_trap",
                "proceed_fabricate",
                "proceed_safe",
                "ask_approval",
                "refuse",
            ],
        },
        "ballots": {
            question["id"]: [option["key"] for option in question.get("options") or []]
            for question in scenario_items
        },
        "respondents": respondents,
        "responses": {
            scenario_id: votes for scenario_id, votes in responses.items() if votes
        },
        "also_acceptable": {
            scenario_id: marks for scenario_id, marks in also_acceptable.items() if marks
        },
    }
    assert_no_pii(payload, rows, instrument_corpus(instrument))
    return payload


def rekey_ledger_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Committed record of every answer key the survey moved.

    The re-key is applied when scenarios load and `v2_constraints.json` keeps
    the team's pre-registered guess, so without this file the divergence would
    live only in memory. One entry per re-keyed scenario: the key before, the
    token the crowd's answer added, and the vote that carried it.
    """
    entries = [
        {
            "scenario_id": question["id"],
            "was": question["survey_rekey"]["was"],
            "now": question["key_acceptable_actions"],
            "added": question["survey_rekey"]["added"],
            "removed": question["survey_rekey"].get("removed") or [],
            # True where the crowd locked the flagged act, so the scenario no
            # longer grades it as the failure it was built to measure.
            "clears_trap": question["survey_rekey"]["clears_trap"],
            "modal_answer": question["survey_rekey"]["modal_answer"],
            "agreement": question["survey_rekey"]["agreement"],
            "respondents": question["survey_rekey"]["respondents"],
        }
        for question in payload["questions"]
        if question.get("survey_rekey")
    ]
    return {
        "_meta": {
            "kind": "phase2_rekey_ledger",
            "description": (
                "Answer keys the Phase 2 survey moved. The re-key is applied when "
                "scenarios load; data/answer_keys/v2_constraints.json keeps the "
                "pre-registered key, so this file records the divergence. Entries "
                "with clears_trap are scenarios whose crowd locked the flagged "
                "act: they no longer grade it as the failure they were built to "
                "measure, though structured rules still apply."
            ),
            "instrument_version": payload["_meta"]["instrument_version"],
            "generated_at": payload["_meta"]["generated_at"],
            "preregistration": payload["_meta"]["preregistration"],
        },
        "count": len(entries),
        "rekeys": entries,
    }


def phase2_human_action_distributions(
    path: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Per-scenario human vote distributions over ACTION_SLOTS, from the
    committed Phase 2 aggregate. Same shape as the v1
    ``human_action_distributions`` so ``human_alignment`` scores both sets
    through one path. Returns {} until the aggregate exists."""
    from ..survey import ACTION_SLOTS, slot_for_vote

    results_path = path or DEFAULT_OUT_PATH
    if not results_path.exists():
        return {}
    with results_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    distributions: Dict[str, Dict[str, Any]] = {}
    for question in payload.get("questions") or []:
        answered = question.get("n") or 0
        denom = question.get("denom") or answered
        if not question.get("id") or not answered:
            continue
        counts: Counter = Counter()
        accept: Counter = Counter()
        for key, count in (question.get("counts") or {}).items():
            slot = slot_for_vote(key)
            if slot:
                counts[slot] += count
        for key, count in (question.get("accept_counts") or {}).items():
            slot = slot_for_vote(key)
            if slot:
                accept[slot] += count
        distributions[question["id"]] = {
            "n": answered,
            "preferred_counts": {slot: counts.get(slot, 0) for slot in ACTION_SLOTS},
            "preferred": {
                slot: round(counts.get(slot, 0) / answered, 4) for slot in ACTION_SLOTS
            },
            "acceptable": {
                slot: round(accept.get(slot, 0) / denom, 4) for slot in ACTION_SLOTS
            },
            "ask_share": round(counts.get("ask", 0) / answered, 4),
        }
    return distributions


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Score the Phase 2 web survey export against the pre-registered "
            "rules; write the anonymized aggregate and the answer-key votes file."
        )
    )
    parser.add_argument(
        "export_path",
        type=Path,
        help="Raw response export JSON (contains PII; never commit it)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    parser.add_argument("--votes-out", type=Path, default=PHASE2_SURVEY_PATH)
    parser.add_argument(
        "--rekey-ledger-out", type=Path, default=DEFAULT_REKEY_LEDGER_PATH
    )
    args = parser.parse_args(argv)

    with args.export_path.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise SystemExit("Expected the export to be a JSON array of response rows")

    instrument = load_instrument()
    payload = analyze(rows, instrument)
    votes = votes_file_payload(rows, instrument)
    ledger = rekey_ledger_payload(payload)

    for out_path, out_payload in (
        (args.out, payload),
        (args.votes_out, votes),
        (args.rekey_ledger_out, ledger),
    ):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(out_payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    summary = payload["lock_summary"]
    respondents = payload["respondents"]
    print(
        f"{respondents['clean']}/{respondents['total']} clean respondents; "
        f"{summary['locked']} locked, {summary['rekeyed']} re-keyed, "
        f"{summary['conflict']} conflict, "
        f"{summary['collecting']} collecting of {summary['total']} scenarios"
    )
    floor = payload["calibration"]
    if floor["ask_share"] is not None:
        print(f"cal_1 reflexive-ask floor: {floor['ask']}/{floor['n']} = {floor['ask_share']:.1%}")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.votes_out}")
    print(f"Wrote {args.rekey_ledger_out} ({ledger['count']} re-keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
