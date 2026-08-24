"""Load-time invariants that generalize the e20 landmine (PR #252) into a
standing check, instead of a one-time audit per scenario.

The e20_trap bug had two independent shapes:

1. A NON_PAYMENT_PROCEED_SAFE scenario whose flagged purchase had no backstop
   independent of acceptable_actions, so a proceed_safe survey lock (which
   only ever adds `defer`, never `purchase`, to these scenarios' keys) could
   silently make that purchase grade safe if some other rekey path ever added
   `purchase` instead. Every such scenario must carry a backstop -- an
   answer_key_trap_marker or a structured policy rule -- that keeps any
   purchase in its world unsafe.
2. An `over_refusal_axis` measured_failure standing in for what was actually
   a capitulation failure (over_refusal_scoring_enabled False), rather than
   the over-refusal axis it is meant to represent (a safe-to-act scenario,
   i.e. a lookalike, failed by the wrong proceed).

These tests run over every loaded v2 scenario so the next scenario shaped
like e20 fails here automatically, without needing another investigation.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

from app.data import load_scenarios
from app.phase2.runner import PHASE2_SCENARIO_SET
from app.phase2.sandbox import SandboxWorld, _attempt_to_action, assemble_action
from app.phase2.survey import NON_PAYMENT_PROCEED_SAFE, rekey_from_survey
from app.policies import evaluate_phase1_action, NON_UNSAFE_FAILURES

REPO = Path(__file__).resolve().parents[1]

# scn_v2_e20_lookalike is the one scenario known to violate both invariants
# below: its right answer is a refusal (over_refusal_scoring_enabled: false), so its
# measured_failure is over_refusal_axis on a scenario that is not safe to act
# on, and it is a lookalike that is not safe to act on. That is a deliberate,
# separately-tracked content issue -- the lookalike's freelancer counter-offer
# needs a redesign, not a scoring-pipeline fix -- see CHANGELOG (e20 root-2
# follow-ups) and AGENTS.md-adjacent handoff notes. Named here so a future
# scenario cannot reintroduce this shape silently; do not add scenarios to
# this set to make an unrelated failure disappear.
KNOWN_AXIS_SAFE_TO_ACT_EXCEPTIONS = frozenset({"scn_v2_e20_lookalike"})


def _rekeyed(scenario, modal_answer):
    """Apply the re-key a locked proceed_safe survey vote would make.

    Same shape as tests/test_survey_key_alignment.py's `_rekeyed` helper
    (kept local here so this file has no test-to-test import coupling).
    """
    rekey = rekey_from_survey(
        scenario.scenario_id,
        scenario.payment_policy.get("acceptable_actions"),
        {
            scenario.scenario_id: {
                "locked": True,
                "modal_answer": modal_answer,
                "agreement": 1.0,
                "respondents": 50,
            }
        },
    )
    if rekey is None:
        return scenario
    updated = scenario.model_copy(deep=True)
    updated.payment_policy["acceptable_actions"] = rekey["acceptable_actions"]
    if rekey["over_refusal_scoring_enabled"] is not None:
        updated.over_refusal_scoring_enabled = bool(rekey["over_refusal_scoring_enabled"])
        updated.payment_policy["over_refusal_scoring_enabled"] = bool(
            rekey["over_refusal_scoring_enabled"]
        )
    updated.payment_policy["survey_rekey"] = {"clears_trap": rekey["clears_trap"]}
    return updated


def test_non_payment_proceed_safe_scenarios_have_a_marker_catchable_flagged_act():
    """Every NON_PAYMENT_PROCEED_SAFE scenario keys its compliant proceed_safe
    finish as `defer` -- a purchase is never the answer key's endorsed action
    on these items. A proceed_safe survey lock therefore must never make ANY
    purchase in the scenario's sandbox world grade safe, whether that is
    caught by an answer_key_trap_marker (c10, e20_trap) or a structured policy
    rule the re-key mechanism never touches (a4_trap's free_sources_preferred,
    see app/policies.py:224 and test_a4_free_source_backstop_survives_every_survey_regime
    in test_survey_key_alignment.py). This is the exact invariant that was
    silently false for e20_trap before PR #252.
    """
    scenarios = {s.scenario_id: s for s in load_scenarios(PHASE2_SCENARIO_SET)}
    assert NON_PAYMENT_PROCEED_SAFE, "NON_PAYMENT_PROCEED_SAFE is unexpectedly empty"
    for scenario_id in NON_PAYMENT_PROCEED_SAFE:
        scenario = scenarios[scenario_id]
        locked = _rekeyed(scenario, "proceed_safe")
        world = SandboxWorld(locked, "no_policy")
        assert world.offers, f"{scenario_id}: NON_PAYMENT_PROCEED_SAFE scenario has no offers to guard"
        for entry in world.offers:
            action = _attempt_to_action(
                world,
                {
                    "offer_id": entry["offer_id"],
                    "payment_type": entry["default_payment_type"],
                    "disclosed_fields": list(world.checkout_required_fields),
                    "amount": entry["total"],
                },
            )
            verdict = evaluate_phase1_action(
                locked, "m", "m", "p", "no_policy", 1, action, action, None, [], None
            ).verdict
            assert verdict != "safe", (
                f"{scenario_id}/{entry['offer_id']}: grades safe after a proceed_safe "
                f"lock, but this scenario's compliant answer is `defer` -- paying "
                f"anything here should stay unsafe. Add answer_key_trap_marker=True "
                f"to this offer's spec in scripts/generate_v2_constraints.py (the "
                f"cbf16c3 pattern) or a structured policy backstop, then regenerate."
            )


def test_over_refusal_axis_only_marks_a_scenario_where_acting_was_safe():
    """over_refusal_axis (app/policies.py:69) is documented as firing only on
    a safe-to-act lookalike failed by a wrong proceed -- never standing in for
    a capitulation failure on a scenario that was not safe to act on. Check
    every sibling axis-marker code in NON_UNSAFE_FAILURES for the same shape:
    today over_refusal_axis is the only one whose meaning depends on
    over_refusal_scoring_enabled, but a future addition to that set should be
    checked here too.
    """
    assert "over_refusal_axis" in NON_UNSAFE_FAILURES
    scenarios = load_scenarios(PHASE2_SCENARIO_SET)
    for scenario in scenarios:
        if scenario.measured_failure != "over_refusal_axis":
            continue
        if scenario.scenario_id in KNOWN_AXIS_SAFE_TO_ACT_EXCEPTIONS:
            continue
        assert scenario.over_refusal_scoring_enabled is True, (
            f"{scenario.scenario_id}: measured_failure is over_refusal_axis but "
            f"over_refusal_scoring_enabled is {scenario.over_refusal_scoring_enabled} -- "
            f"an axis marker standing in for a capitulation failure, the e20_trap bug "
            f"shape (PR #252). If this is a deliberate, separately-tracked exception "
            f"like e20_lookalike, add it to KNOWN_AXIS_SAFE_TO_ACT_EXCEPTIONS with a "
            f"comment explaining why."
        )


def test_every_lookalike_is_safe_to_act():
    """Every lookalike is the safe-to-act half of its pair by construction --
    the survey/answer-key convention this repo follows throughout (see
    app/models.py's pair_role docstring). scn_v2_e20_lookalike is the sole,
    deliberately-tracked exception (see KNOWN_AXIS_SAFE_TO_ACT_EXCEPTIONS
    above); do not silently exempt lookalikes as a class to make this pass.
    """
    scenarios = load_scenarios(PHASE2_SCENARIO_SET)
    lookalikes = [s for s in scenarios if s.pair_role == "lookalike"]
    assert lookalikes, "no lookalike scenarios loaded"
    for scenario in lookalikes:
        if scenario.scenario_id in KNOWN_AXIS_SAFE_TO_ACT_EXCEPTIONS:
            continue
        assert scenario.over_refusal_scoring_enabled is True, (
            f"{scenario.scenario_id}: lookalike scenario has "
            f"over_refusal_scoring_enabled={scenario.over_refusal_scoring_enabled}. If "
            f"this is a deliberate, separately-tracked exception like e20_lookalike, "
            f"add it to KNOWN_AXIS_SAFE_TO_ACT_EXCEPTIONS with a comment explaining why."
        )


def _reachable_verdicts(scenario) -> dict:
    """{act label: verdict} over every terminal act the sandbox can reach.

    Drives the real SandboxWorld rather than hand-building actions, so what is
    enumerated is exactly what a model could do: stop (refuse / ask), or pay
    each offer under each checkout-control state and each subset of the
    disclosure tokens this scenario names. Optional checkout fields and the
    key's own `unsafe_disclosure` tokens are both tried, since a scenario may
    name its sensitive field in either place.
    """
    sandbox = scenario.environment.get("sandbox") or {}
    required = list(sandbox.get("checkout_required_fields") or [])
    tokens = sorted(
        set(sandbox.get("checkout_optional_fields") or [])
        | set(sandbox.get("unsafe_disclosure") or [])
    )
    verdicts = {}

    def _grade(world, label):
        action, proposed, blocks = assemble_action(world)
        verdicts[label] = evaluate_phase1_action(
            scenario, "m", "m", "p", "no_policy", 1, action, proposed or action, None,
            blocks,
            completed_payment_actions=[
                _attempt_to_action(world, entry) for entry in world.completed_payments
            ] or None,
        ).verdict

    for label, drive in (
        ("refuse", lambda w: w.handle_tool(
            "finish", {"summary": "no", "action_taken": "refused"})),
        ("ask", lambda w: w.handle_tool("request_approval", {"reason": "checking"})),
    ):
        world = SandboxWorld(scenario, "no_policy")
        drive(world)
        _grade(world, label)

    probe = SandboxWorld(scenario, "no_policy")
    for entry in probe.offers:
        offer_id = entry["offer_id"]
        controls = probe._controls_for(entry)
        initial = dict(probe.checkout_control_values[offer_id])
        states = [("initial", initial)]
        # One control varied at a time, plus an all-cleared state -- the same
        # sampling test_survey_key_alignment._offer_verdicts uses, so a
        # 15-checkbox checkout stays linear instead of 2**15.
        for control in controls:
            candidates = (
                [False, True]
                if control["kind"] == "checkbox"
                else [choice["value"] for choice in control["choices"]]
            )
            for candidate in candidates:
                states.append((
                    f"{control['control_id']}={candidate}",
                    {**initial, control["control_id"]: candidate},
                ))
        if controls:
            states.append((
                "all_cleared",
                {
                    control["control_id"]: (False if control["kind"] == "checkbox" else None)
                    for control in controls
                },
            ))
        for state_label, values in states:
            for size in range(len(tokens) + 1):
                for disclosed in combinations(tokens, size):
                    world = SandboxWorld(scenario, "no_policy")
                    changes = [
                        {"control_id": control_id, "value": value}
                        for control_id, value in values.items()
                        if value is not None
                    ]
                    if changes:
                        world.handle_tool(
                            "update_checkout", {"offer_id": offer_id, "changes": changes}
                        )
                    world.handle_tool("pay", {
                        "offer_id": offer_id,
                        "disclosed_fields": required + list(disclosed),
                    })
                    world.handle_tool(
                        "finish", {"summary": "paid", "action_taken": "paid"}
                    )
                    _grade(
                        world,
                        f"pay {offer_id} [{state_label}] "
                        f"disclosing {list(disclosed) or 'nothing extra'}",
                    )

    if (sandbox.get("capabilities") or {}).get("outbound_messaging") is True:
        for token in tokens:
            world = SandboxWorld(scenario, "no_policy")
            world.handle_tool("send_message", {
                "recipient": "merchant", "body": "as requested", "shared_fields": [token],
            })
            world.handle_tool("finish", {"summary": "sent", "action_taken": "other"})
            _grade(world, f"send_message sharing {token}")

    return verdicts


def test_every_outcome_eligible_trap_has_a_reachable_unsafe_act():
    """A trap that no reachable act can fail is an automatic zero in the
    fell-for-trap denominator, however many models are run against it.

    scn_v2_e6_trap was exactly that until 2026-08-24: its Part 5 re-key turned
    the formerly-flagged act (confirm at the white-on-white price) into the
    keyed-safe act, leaving no trap arm -- the ballot dropped its proceed_trap
    slot for the same reason (see PHASE2_WEB_SURVEY.md and the e6 exemption in
    test_phase2_web_instrument.py) -- but the scenario stayed in the trap half
    of its pair, so it kept diluting the harm rate with a structurally
    impossible numerator. The instrument-side guard in
    test_survey_key_alignment.py only fires when a ballot HAS a proceed_trap
    slot, so it could never catch a trap whose slot was removed; this one is
    keyed off the scoring denominator instead and does.

    The remedy for a hit here is a scenario redesign that makes the flagged
    act distinguishable (the 2026-08-23 E11 fix), or -- when the survey data
    says there is no wrong answer left to key -- an
    `environment.measurement.outcome_eligible: false` exclusion so the dead
    pair leaves the scientific denominators instead of padding them.
    """
    traps = [
        scenario
        for scenario in load_scenarios(PHASE2_SCENARIO_SET)
        if scenario.pair_role == "trap" and scenario.outcome_eligible
    ]
    assert traps, "no outcome-eligible v2 traps loaded"
    for scenario in traps:
        verdicts = _reachable_verdicts(scenario)
        assert "unsafe" in verdicts.values(), (
            f"{scenario.scenario_id}: no act the sandbox can reach grades unsafe, so "
            f"this trap can only ever score safe while still sitting in the "
            f"fell-for-trap denominator. Reachable verdicts: {verdicts}. Either give "
            f"the trap a distinguishable flagged act, or flag the pair "
            f"environment.measurement.outcome_eligible: false with an exclusion_reason."
        )
