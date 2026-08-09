"""Import a Google Form CSV export into Phase 2 human-baseline sessions.

A real human baseline is collected by having 5-10 people fill in a Google Form,
then exporting the responses as a CSV. This module turns that CSV into the same
session shape ``collect_human_session`` records, so imported humans are scored by
the identical model pipeline (``evaluate_phase1_action``).

CSV contract (one row per form response = one participant):

* **Identity** - a ``participant_id`` column (aliases: ``participant``, ``id``,
  ``respondent_id``). Falls back to an ``email`` column, then to ``p01``, ``p02``...
* **Demographics** - any of the canonical :data:`~app.phase2.humans.DEMOGRAPHIC_FIELDS`
  columns (``age_band``/``age``, ``gender``, ``country``, ``occupation``/``job``,
  ``purchasing_role``/``role``, ``education``, ``ai_familiarity``). Unrecognized
  non-scenario columns are preserved verbatim in the session's ``demographics``.
* **Decisions** - every column whose header *contains* a scenario id (e.g. a
  question titled ``[scn_v2_a1_trap] You're asked to ...``, or just the bare id
  ``scn_v2_a1_trap``). The cell value is a coarse decision verb:

  ===========  =============================================  ===================
  Verb         Aliases                                        Scored action
  ===========  =============================================  ===================
  ``proceed``  buy, pay, purchase                             purchase
  ``ask``      approve, approval, escalate, request approval  ask_approval
  ``refuse``   decline, reject, deny                          refuse
  ``done``     complete, task complete                        defer (task done)
  ``skip``     abandon, do nothing, none                      defer (abandoned)
  ===========  =============================================  ===================

  (``pay_tool`` / ``send_stablecoin`` are accepted for the rarer rails.)

* **Optional richer fields** - when a form captures more than the verb, add
  ``<scenario_id>:amount`` columns (also ``:merchant``, ``:sku``,
  ``:payment_type``, ``:disclosed_fields`` (``;``-separated), ``:rationale``,
  ``:recurring``, ``:refundable``). ``__`` works in place of ``:`` for tools
  that dislike colons in headers.

Every payment decision is **grounded in the scenario's sandbox world** before
it is stored: the response is resolved to one concrete offer (by ``:sku``,
then ``:merchant``, then ``:amount``; a single-offer scenario needs no
disambiguator) and the stored action carries that offer's real amount,
merchant, offer id, rail, disclosed fields, and marker attributes — the same
action surface a model's sandbox payment produces. A payment response that
does not pin down one offer is recorded with ``underspecified: true`` and
excluded from scoring; grading a guess would fabricate a choice the
participant never expressed. ``done`` claims are world-grounded the same way
sandbox assembly grounds a model's: honored only when the scenario has a
currently-available free source.

The ``condition`` passed to the importer must reflect what the form actually
showed participants: only claim ``structured_policy`` if the form question
included the scenario's structured policy text alongside the task.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..data import load_scenarios
from ..models import AgentAction, Scenario, model_to_dict, normalize_policy_token
from .humans import DEMOGRAPHIC_FIELDS, PHASE2_SESSIONS_PATH, load_sessions
from .runner import PHASE2_SCENARIO_SET
from .sandbox import SandboxWorld, _attempt_to_action


# A scenario id is ``scn_`` followed by single-underscore-joined alnum segments.
# Written so a trailing ``__attr`` / ``:attr`` suffix is NOT swallowed into the
# id (the double underscore / colon stops the match).
_SCENARIO_RE = re.compile(r"scn_(?:[a-z0-9]+_)*[a-z0-9]+")
_ATTR_SEP_RE = re.compile(r"^\s*(?:__|:)\s*(.+)$")

# Per-scenario detail columns a form may optionally carry alongside the verb.
_ATTR_ALIASES = {
    "amount": "amount",
    "total": "amount",
    "merchant": "merchant_id",
    "merchant_id": "merchant_id",
    "sku": "sku",
    "offer": "sku",
    "offer_id": "sku",
    "payment_type": "payment_type",
    "payment": "payment_type",
    "rail": "payment_type",
    "disclosed_fields": "disclosed_fields",
    "disclosed": "disclosed_fields",
    "fields": "disclosed_fields",
    "rationale": "rationale",
    "reason": "rationale",
    "recurring": "recurring",
    "refundable": "refundable",
}

# Coarse decision verb -> (action_type, default field overrides).
_DECISION_MAP: Dict[str, Tuple[str, Dict[str, Any]]] = {
    "proceed": ("purchase", {}),
    "buy": ("purchase", {}),
    "buy_it": ("purchase", {}),
    "pay": ("purchase", {}),
    "purchase": ("purchase", {}),
    "pay_tool": ("pay_tool", {"paid_tool_used": True}),
    "send_stablecoin": ("send_stablecoin", {}),
    "stablecoin": ("send_stablecoin", {}),
    "ask": ("ask_approval", {"approval_requested": True}),
    "ask_approval": ("ask_approval", {"approval_requested": True}),
    "ask_for_approval": ("ask_approval", {"approval_requested": True}),
    "approve": ("ask_approval", {"approval_requested": True}),
    "approval": ("ask_approval", {"approval_requested": True}),
    "request_approval": ("ask_approval", {"approval_requested": True}),
    "escalate": ("ask_approval", {"approval_requested": True}),
    "pause": ("ask_approval", {"approval_requested": True}),
    "refuse": ("refuse", {}),
    "decline": ("refuse", {}),
    "reject": ("refuse", {}),
    "deny": ("refuse", {}),
    "do_not_buy": ("refuse", {}),
    "dont_buy": ("refuse", {}),
    "done": ("defer", {"completed": True}),
    "complete": ("defer", {"completed": True}),
    "completed": ("defer", {"completed": True}),
    "task_complete": ("defer", {"completed": True}),
    "skip": ("defer", {"completed": False}),
    "abandon": ("defer", {"completed": False}),
    "nothing": ("defer", {"completed": False}),
    "do_nothing": ("defer", {"completed": False}),
    "none": ("defer", {"completed": False}),
    "walk_away": ("defer", {"completed": False}),
}

_PAYMENT_ACTIONS = {"purchase", "pay_tool", "send_stablecoin"}

# Demographic column aliases -> canonical field. Canonical names map to
# themselves; only synonyms need listing.
_DEMOGRAPHIC_ALIASES = {
    "age": "age_band",
    "age_range": "age_band",
    "age_group": "age_band",
    "sex": "gender",
    "country_of_residence": "country",
    "nationality": "country",
    "job": "occupation",
    "job_title": "occupation",
    "profession": "occupation",
    "role": "purchasing_role",
    "buyer_role": "purchasing_role",
    "education_level": "education",
    "ai_experience": "ai_familiarity",
    "ai_usage": "ai_familiarity",
    "llm_familiarity": "ai_familiarity",
}

# Non-demographic identity / bookkeeping columns Google Forms emits.
_PARTICIPANT_KEYS = {"participant_id", "participant", "id", "subject_id", "respondent_id"}
_EMAIL_KEYS = {"email", "email_address"}
_TIMESTAMP_KEYS = {"timestamp", "started_at", "start_time"}
_DURATION_KEYS = {"duration_seconds", "duration"}
_IGNORED_KEYS = {"score", "username", "name"}


def _canonical(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


def _parse_scenario_header(header: str) -> Optional[Tuple[str, str]]:
    """Return ``(scenario_id, attr)`` for a scenario column, else ``None``.

    ``attr`` is ``"decision"`` for the main verb column, or a normalized detail
    name (``amount``, ``merchant_id``, ...) for an optional richer column.
    """
    match = _SCENARIO_RE.search(header.lower())
    if not match:
        return None
    scenario_id = match.group(0)
    suffix = _ATTR_SEP_RE.match(header.lower()[match.end():])
    if not suffix:
        return scenario_id, "decision"
    attr = _canonical(suffix.group(1))
    return scenario_id, _ATTR_ALIASES.get(attr, attr)


def _to_float(value: str) -> Optional[float]:
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if not cleaned or cleaned in {"-", ".", "-."}:
        return None
    return float(cleaned)


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def decision_to_action(token: str, extras: Optional[Dict[str, str]] = None) -> AgentAction:
    """Map a coarse decision verb (plus optional detail columns) to an AgentAction."""
    extras = extras or {}
    norm = re.sub(r"[\s\-]+", "_", str(token).strip().strip("\"'").lower())
    if norm not in _DECISION_MAP:
        valid = ", ".join(sorted({"proceed", "ask", "refuse", "done", "skip"}))
        raise ValueError(
            f"Unknown decision {token!r}. Use one of: {valid} (see human_import for aliases)."
        )
    action_type, overrides = _DECISION_MAP[norm]
    fields: Dict[str, Any] = dict(overrides)

    if action_type in _PAYMENT_ACTIONS:
        # The benchmark advertises a delegated card; default to it so the
        # payment-rail policy check sees a valid rail unless the form overrides.
        fields.setdefault("payment_type", "card")
        amount = _to_float(extras["amount"]) if extras.get("amount") else None
        if amount is not None:
            fields["amount"] = amount
        if extras.get("merchant_id"):
            fields["merchant_id"] = extras["merchant_id"]
        if extras.get("sku"):
            fields["sku"] = extras["sku"]
        if extras.get("payment_type"):
            fields["payment_type"] = extras["payment_type"]
        if extras.get("disclosed_fields"):
            fields["disclosed_fields"] = [
                part.strip() for part in re.split(r"[;,]", extras["disclosed_fields"]) if part.strip()
            ]
        if extras.get("recurring"):
            fields["recurring"] = _truthy(extras["recurring"])
        if extras.get("refundable"):
            fields["refundable"] = _truthy(extras["refundable"])

    fields["rationale"] = extras.get("rationale") or f"Imported from Google Form response ({token})."
    return AgentAction(action_type=action_type, **fields)  # type: ignore[arg-type]


def _split_fields(raw: str) -> List[str]:
    return [part.strip() for part in re.split(r"[;,]", raw) if part.strip()]


def _resolve_offer(
    offers: List[Dict[str, Any]], extras: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    """Pin a form response to one sandbox offer, or ``None`` when it can't be.

    An explicit ``:sku``/``:offer`` id wins; otherwise ``:merchant`` and
    ``:amount`` narrow the candidates, and a single-offer world needs no
    disambiguator at all. Anything still ambiguous stays unresolved rather
    than guessed.
    """
    sku = (extras.get("sku") or "").strip()
    if sku:
        return next((offer for offer in offers if offer.get("offer_id") == sku), None)
    candidates = offers
    merchant = normalize_policy_token(extras.get("merchant_id"))
    if merchant:
        candidates = [
            offer
            for offer in candidates
            if normalize_policy_token(offer.get("merchant_id")) == merchant
        ]
    amount = _to_float(extras["amount"]) if extras.get("amount") else None
    if amount is not None:
        candidates = [
            offer
            for offer in candidates
            if abs(float(offer.get("total") or 0.0) - amount) < 0.005
        ]
    return candidates[0] if len(candidates) == 1 else None


def ground_form_action(
    scenario: Scenario,
    token: str,
    extras: Optional[Dict[str, str]] = None,
    control_condition: str = "structured_policy",
) -> Tuple[Optional[AgentAction], Optional[str]]:
    """Ground a form decision in the scenario's sandbox world.

    A payment verb is resolved to a concrete offer and rebuilt the way the
    sandbox assembles a model's payment, so the stored action carries the
    offer's real amount, merchant, offer id, rail, disclosed fields, and
    marker attributes — the same action surface models are scored on, instead
    of a bare verb the scorer's amount/merchant/marker checks silently skip.
    Returns ``(action, None)`` on success, or ``(None, "offer_unresolved")``
    when the response does not pin down one offer. A ``done`` claim is honored
    only when the world backs it (a currently-available free source),
    mirroring sandbox assembly.
    """
    extras = extras or {}
    coarse = decision_to_action(token, extras)
    if coarse.action_type not in _PAYMENT_ACTIONS:
        if coarse.action_type == "defer" and coarse.completed:
            sandbox = scenario.environment.get("sandbox") or {}
            free_source = sandbox.get("free_source")
            if not (free_source and free_source.get("current", True)):
                coarse.completed = False
                coarse.rationale = (coarse.rationale + " " if coarse.rationale else "") + (
                    "[completion claim not backed by the sandbox world]"
                )
        return coarse, None
    world = SandboxWorld(scenario, control_condition)
    offer = _resolve_offer(world.offers, extras)
    if offer is None:
        return None, "offer_unresolved"
    if extras.get("disclosed_fields"):
        disclosed = _split_fields(extras["disclosed_fields"])
    else:
        disclosed = list(world.checkout_required_fields)
    payment_type = extras.get("payment_type") or (
        "stablecoin"
        if coarse.action_type == "send_stablecoin"
        else offer.get("default_payment_type") or "card"
    )
    grounded = _attempt_to_action(
        world,
        {
            "offer_id": offer["offer_id"],
            "payment_type": payment_type,
            "disclosed_fields": disclosed,
            "amount": offer["total"],
        },
    )
    grounded.action_type = coarse.action_type
    grounded.paid_tool_used = coarse.paid_tool_used
    grounded.rationale = extras.get("rationale") or (
        f"Imported from Google Form response ({token}); grounded in offer {offer['offer_id']}."
    )
    return grounded, None


def _classify_columns(fieldnames: List[str]) -> Dict[str, Any]:
    decision_cols: Dict[str, str] = {}
    attr_cols: Dict[Tuple[str, str], str] = {}
    demo_cols: Dict[str, str] = {}
    extra_demo_cols: Dict[str, str] = {}
    participant_col = email_col = timestamp_col = duration_col = None
    unknown_columns: List[str] = []

    for header in fieldnames or []:
        if header is None or not header.strip():
            continue
        scenario = _parse_scenario_header(header)
        if scenario:
            scenario_id, attr = scenario
            if attr == "decision":
                decision_cols[scenario_id] = header
            elif attr in {
                "amount",
                "merchant_id",
                "sku",
                "payment_type",
                "disclosed_fields",
                "rationale",
                "recurring",
                "refundable",
            }:
                attr_cols[(scenario_id, attr)] = header
            else:
                unknown_columns.append(header)
            continue

        canon = _canonical(header)
        field = _DEMOGRAPHIC_ALIASES.get(canon, canon)
        if field in DEMOGRAPHIC_FIELDS:
            demo_cols[field] = header
        elif canon in _PARTICIPANT_KEYS:
            participant_col = header
        elif canon in _EMAIL_KEYS:
            email_col = header
        elif canon in _TIMESTAMP_KEYS:
            timestamp_col = timestamp_col or header
        elif canon in _DURATION_KEYS:
            duration_col = header
        elif canon in _IGNORED_KEYS:
            continue
        else:
            # Anything left over is treated as an extra demographic so a richer
            # form is not silently dropped; preserved under its slug.
            extra_demo_cols[canon] = header

    return {
        "decision_cols": decision_cols,
        "attr_cols": attr_cols,
        "demo_cols": demo_cols,
        "extra_demo_cols": extra_demo_cols,
        "participant_col": participant_col,
        "email_col": email_col,
        "timestamp_col": timestamp_col,
        "duration_col": duration_col,
        "unknown_columns": unknown_columns,
    }


def import_google_form_csv(
    csv_path: Any,
    *,
    condition: str = "structured_policy",
    sessions_path: Optional[Path] = None,
    write: bool = True,
) -> Dict[str, Any]:
    """Import a Google Form CSV into the human-baseline sessions file.

    Existing real sessions are upserted by ``session_id``; a shipped
    example-only file is replaced (its ``_meta.example`` flag is cleared).
    Returns import statistics including any unknown scenarios/columns so a
    researcher can spot a mis-built form.
    """
    csv_path = Path(csv_path)
    target = sessions_path or PHASE2_SESSIONS_PATH
    valid_scenarios = {
        scenario.scenario_id: scenario for scenario in load_scenarios(PHASE2_SCENARIO_SET)
    }

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = _classify_columns(reader.fieldnames or [])
        rows = list(reader)

    if not columns["decision_cols"]:
        raise ValueError(
            "No scenario decision columns found. At least one column header must "
            "contain a scenario id like 'scn_v2_a1_trap'."
        )

    new_sessions: Dict[str, Dict[str, Any]] = {}
    participants: set[str] = set()
    unknown_scenarios: set[str] = set()
    imported_scenarios: set[str] = set()
    underspecified_sessions: List[str] = []
    blank_cells = 0

    for index, row in enumerate(rows):
        if not any((value or "").strip() for value in row.values()):
            continue  # skip wholly blank rows
        participant_id = ""
        if columns["participant_col"]:
            participant_id = (row.get(columns["participant_col"]) or "").strip()
        if not participant_id and columns["email_col"]:
            # The sessions table is published with public SELECT, so never store a
            # raw email. Pseudonymize to a stable id instead (same respondent ->
            # same id across forms) and keep the address out of the data entirely.
            email = (row.get(columns["email_col"]) or "").strip()
            if email:
                participant_id = "p_" + hashlib.sha1(email.encode("utf-8")).hexdigest()[:8]
        if not participant_id:
            participant_id = f"p{index + 1:02d}"

        demographics: Dict[str, str] = {}
        for field, header in columns["demo_cols"].items():
            value = (row.get(header) or "").strip()
            if value:
                demographics[field] = value
        for slug, header in columns["extra_demo_cols"].items():
            value = (row.get(header) or "").strip()
            if value:
                demographics[slug] = value

        started_at = None
        if columns["timestamp_col"]:
            started_at = (row.get(columns["timestamp_col"]) or "").strip() or None
        duration_seconds = None
        if columns["duration_col"]:
            duration_seconds = _to_float(row.get(columns["duration_col"]) or "")

        for scenario_id, header in columns["decision_cols"].items():
            token = (row.get(header) or "").strip()
            if not token:
                blank_cells += 1
                continue
            scenario = valid_scenarios.get(scenario_id)
            if scenario is None:
                unknown_scenarios.add(scenario_id)
                continue
            extras = {
                attr: (row.get(attr_header) or "").strip()
                for (sid, attr), attr_header in columns["attr_cols"].items()
                if sid == scenario_id and (row.get(attr_header) or "").strip()
            }
            action, problem = ground_form_action(scenario, token, extras, condition)
            session_id = f"hb_{participant_id}_{scenario_id}"
            session: Dict[str, Any] = {
                "session_id": session_id,
                "participant_id": participant_id,
                "demographics": demographics,
                "scenario_id": scenario_id,
                "control_condition": condition,
                "action": model_to_dict(action if action is not None else decision_to_action(token, extras)),
                "source": "google_form_csv",
            }
            if problem:
                # The verb is kept for the record, but nothing says which
                # offer was bought, so the session is flagged and stays out of
                # scoring (score_sessions skips it).
                session["underspecified"] = True
                underspecified_sessions.append(session_id)
            if started_at:
                session["started_at"] = started_at
            if duration_seconds is not None:
                session["duration_seconds"] = duration_seconds
            new_sessions[session_id] = session
            participants.add(participant_id)
            imported_scenarios.add(scenario_id)

    if write and new_sessions:
        payload = load_sessions(target)
        existing = [] if payload.get("_meta", {}).get("example") else payload.get("sessions", [])
        merged: Dict[str, Dict[str, Any]] = {
            session.get("session_id"): session for session in existing if session.get("session_id")
        }
        merged.update(new_sessions)
        payload["sessions"] = list(merged.values())
        payload["_meta"] = {
            "example": False,
            "source": "google_form_csv",
            "imported_from": csv_path.name,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    return {
        "csv": str(csv_path),
        "participants": len(participants),
        "sessions_imported": len(new_sessions),
        "scenarios": sorted(imported_scenarios),
        "unknown_scenarios": sorted(unknown_scenarios),
        "unknown_columns": columns["unknown_columns"],
        "underspecified_sessions": sorted(underspecified_sessions),
        "blank_cells": blank_cells,
        "sessions_path": str(target),
        "written": bool(write and new_sessions),
    }
