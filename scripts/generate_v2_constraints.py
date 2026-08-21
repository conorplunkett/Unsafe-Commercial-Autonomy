"""Attach Phase 2 sandbox environments to data/answer_keys/v2_constraints.json.

The constraints JSON is the authoritative, hand-editable answer key (policy
fields, expected_action, acceptable_actions, safe_to_act, and the sandbox
`environment` block). This script only ENRICHES it and NEVER overwrites a
value that is already present. For every scenario it fills in a sandbox
`environment` block (offers, checkout fields, optional fields, injection
markers) and the few sandbox-only policy fields the answer key lacked (e.g.
privacy_allowed_fields for category D, allowed_merchants for spoofing traps
in category E) ONLY where they are missing, then writes the file back. Every
existing value — including manually edited offers, totals, and policy fields —
is preserved. To regenerate an entry from its spec, delete that entry's
`environment` block first.

Offer numbers are transcribed from data/scenario_sets/v2_250_scenarios.md;
page_text defaults to the scenario situation verbatim, pulled through the
loader — which is what view_offer hands the model, policy statement and all.
A spec can override this per offer with an authored `page_text=` (realistic
listing/cert-page copy that shows the disqualifying fact without narrating
the policy or which offer is the trap); build_offers marks such offers
`authored_page_text: true` so the consistency test in
tests/test_phase2_runner.py treats the divergence from source_situation as
intentional. See b13/b18/b23 for worked examples.
Offers that represent complying with an injected/adversarial instruction
carry `injection_compliance_marker: true`; offers that complete the task with
fabricated data carry `unsafe_marker: true`. Traps whose failure mode is not
detectable by the structured policy engine are flagged `semantic_only`.

For the 44 scenarios the Phase 2 preference survey covers, the survey is
ground truth for the amounts: an offer total must be a figure the respondent
saw on screen (or reachable from two of them by one addition or subtraction).
`test_sandbox_prices_are_grounded_in_the_survey` enforces that. Because this
script only fills in MISSING values, a stale price here regenerates as a
no-op and will not show up as a diff, so that test is the thing that catches
it.

**All five *_SPECS dicts below are empty (2026-08-19).** Every one of the 226
v2 scenarios already has a committed `environment`, so there is nothing left
for any existing spec entry to fill in — keeping one in sync with hand edits
made directly to the committed JSON was pure duplicated-source-of-truth risk
with no offsetting benefit. It bit the project twice: 12 scenarios drifted
silently in July (see PHASE2_WEB_SURVEY.md), and c3 again in August (see
CHANGELOG.md) — both times because a spec kept describing a world someone
had since hand-edited away from. Add an entry back only when authoring a
genuinely new scenario that still needs its environment built; nothing else
in this file changed, and `main()` still works exactly as documented above
for that case.

Run from the repo root:  python scripts/generate_v2_constraints.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.data import DATA_DIR, load_scenarios  # noqa: E402

V2_SET = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"
OUT_PATH = DATA_DIR / "answer_keys" / "v2_constraints.json"

# Authored merchant-page copy, one reviewable artifact instead of 280+ strings
# inlined into the specs below: {scenario_id: {offer_id: page_text}}. Loaded at
# build time; a spec's inline `page_text=` (the b13/b18/b23 pilots) takes
# precedence over the sidecar. Every sidecar entry must resolve to a real
# scenario/offer — main() fails loudly on a dangling key, so a renamed offer
# cannot silently fall back to the leaking situation-string default.
PAGE_TEXTS_PATH = DATA_DIR / "answer_keys" / "v2_page_texts.json"
try:
    PAGE_TEXTS = json.loads(PAGE_TEXTS_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:
    PAGE_TEXTS = {}
PAGE_TEXTS.pop("_meta", None)

DEFAULT_CHECKOUT_FIELDS = ["name", "shipping_address", "payment_card_secure_field"]


def offer(
    offer_id,
    merchant_id,
    merchant_name,
    item,
    price,
    shipping=0.0,
    tax=0.0,
    fees=(),
    total=None,
    recurring=False,
    recurring_note=None,
    refundable=True,
    payment_types=("card",),
    default_payment_type="card",
    category=None,
    unclear_ingredients=False,
    headline_price=None,
    injection_compliance_marker=False,
    unsafe_marker=False,
    answer_key_trap_marker=False,
    checkout=None,
):
    fees = [dict(label=label, amount=amount) for label, amount in fees]
    computed = round(price + shipping + tax + sum(fee["amount"] for fee in fees), 2)
    if total is None:
        total = computed
    if abs(total - computed) > 0.005:
        raise ValueError(f"{offer_id}: total {total} != computed {computed}")
    built = {
        "offer_id": offer_id,
        "merchant_id": merchant_id,
        "merchant_name": merchant_name,
        "item": item,
        "price": price,
        "shipping": shipping,
        "tax": tax,
        "fees": fees,
        "total": total,
        "recurring": recurring,
        "recurring_note": recurring_note,
        "refundable": refundable,
        "payment_types": list(payment_types),
        "default_payment_type": default_payment_type,
        "category": category,
        "unclear_ingredients": unclear_ingredients,
        "headline_price": price if headline_price is None else headline_price,
    }
    if checkout:
        built["checkout"] = checkout
    if injection_compliance_marker:
        built["injection_compliance_marker"] = True
    # Completing the task by inventing the data a counterparty asked for.
    if unsafe_marker:
        built["unsafe_marker"] = True
    if answer_key_trap_marker:
        # Paying this offer *is* the failure the scenario measures, in a world
        # where no structured rule can tell it from the compliant offer (wrong
        # recipient, wrong entity, wrong tier, the pause instead of the
        # cancellation). Read by app/policies._keyed_trap_offer_ids.
        built["answer_key_trap_marker"] = True
    return built


# --------------------------------------------------------------------------
# Category A: spend limits. Offers transcribed from the v2 markdown; the trap
# total breaches the cap (or needs subscription consent); the lookalike fits.
# Policy fields live authoritatively in the JSON; *_policy_add only ADDS the
# fields the sandbox needs where the answer key lacked them.
# --------------------------------------------------------------------------

A_SPECS = {}
# Empty since 2026-08-19 -- see the module docstring above for why.

# --------------------------------------------------------------------------
# Category B: authorization scope. Traps include the tempting non-compliant
# offer plus (where the right answer allows buying) a compliant alternative.
# Prohibited-category policies are added where the answer key encoded the
# rule only in prose.
# --------------------------------------------------------------------------

B_SPECS = {}
# Empty since 2026-08-19 -- see the module docstring above for why.


def build_offers(spec, role_offers, item, default_merchant, page_text, scenario_id=None):
    offers = []
    sidecar = PAGE_TEXTS.get(scenario_id, {}) if scenario_id else {}
    for index, raw in enumerate(role_offers, start=1):
        raw = dict(raw)
        merchant_id, merchant_name = raw.pop("merchant", default_merchant)
        suffix = raw.pop("offer_suffix", str(index) if len(role_offers) > 1 else "1")
        fees = raw.pop("fees", [])
        item_override = raw.pop("item", item)
        # page_text resolution, most-specific first: a spec's inline
        # `page_text=` (the b13/b18/b23 pilots), then the authored sidecar
        # (data/answer_keys/v2_page_texts.json), then — the leaking legacy
        # default — the situation string verbatim, policy and all. Authored
        # copy is realistic merchant-voice content that shows the
        # disqualifying fact without restating the policy or narrating which
        # offer is the trap; `authored_page_text` marks it so the consistency
        # test knows the divergence from source_situation is intentional.
        offer_page_text = raw.pop("page_text", None) or sidecar.get(f"off_{suffix}")
        entry = offer(
            offer_id=f"off_{suffix}",
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            item=item_override,
            fees=fees,
            **raw,
        )
        if offer_page_text:
            entry["page_text"] = offer_page_text
            entry["authored_page_text"] = True
        else:
            entry["page_text"] = page_text
        offers.append(entry)
    return offers


def build_environment(spec, role, scenario):
    default_merchant = spec.get("merchant", ("sandbox_merchant", "Sandbox Merchant"))
    role_offers = spec["trap"] if role == "trap" else spec["look"]
    environment = {
        "offers": build_offers(
            spec, role_offers, spec["item"], default_merchant,
            scenario.source_situation, scenario_id=scenario.scenario_id,
        ),
        "checkout_required_fields": list(DEFAULT_CHECKOUT_FIELDS),
    }
    prefix = "trap" if role == "trap" else "look"
    environment.update(spec.get(f"{prefix}_extra_env", {}))
    environment.update(spec.get(f"{prefix}_env", {}))
    if role == "trap" and spec.get("semantic_only_trap"):
        environment["semantic_only"] = True
    if role == "trap" and spec.get("trap_unsafe_disclosure"):
        environment["unsafe_disclosure"] = list(spec["trap_unsafe_disclosure"])
    return environment


def policy_additions(spec, role):
    return dict(spec.get(f"{'trap' if role == 'trap' else 'look'}_policy_add", {}))


# --------------------------------------------------------------------------
# Category C: consent and escalation. Most traps are semantic (the engine
# cannot see ambiguity or missing consent); offers present the real choice so
# the agent's pay/ask decision is meaningful. Where a structured field
# genuinely encodes the rule (thresholds, subscriptions, refundability,
# prohibited categories) the trap is engine-detectable and policy fields are
# added when the answer key lacked them.
# --------------------------------------------------------------------------

C_SPECS = {}
# Empty since 2026-08-19 -- see the module docstring above for why.


# --------------------------------------------------------------------------
# Category D: privacy and disclosure. Worlds define required checkout fields
# (always within the privacy allowlist) and optional fields carrying the
# sensitive bait. `unsafe_disclosure` lists the fields that constitute the
# trap; disclosing them trips the privacy_leakage engine rule. Where the
# merchant *requires* the sensitive field, paying at all leaks and the trap
# is engine-detectable on the default path.
# --------------------------------------------------------------------------

D_SPECS = {}
# Empty since 2026-08-19 -- see the module docstring above for why.


# --------------------------------------------------------------------------
# Category E: adversarial robustness. The injected/adversarial text lives in
# page_text (the situation verbatim); offers that represent complying with
# the push carry injection_compliance_marker. Spoofing traps add an
# allowed_merchants policy so the engine can verify the counterparty; caps
# and subscription rules are added only where the situation states them.
# --------------------------------------------------------------------------

E_SPECS = {}
# Empty since 2026-08-19 -- see the module docstring above for why.


ALL_SPECS = [(A_SPECS, "a"), (B_SPECS, "b"), (C_SPECS, "c"), (D_SPECS, "d"), (E_SPECS, "e")]


def _merge_preserving(existing, generated):
    """Deep-merge ``generated`` UNDER ``existing`` so manual edits always win.

    Any value already present in ``existing`` (the committed JSON, which may
    carry hand edits) is kept and never overwritten — only keys missing from
    ``existing`` are filled in from ``generated``. Lists such as ``offers`` are
    treated atomically: an existing list survives verbatim, so hand-edited
    offers/totals are preserved across a regenerate. When ``existing`` is None
    (a brand-new entry) the generated value is used as-is.
    """
    if existing is None:
        return generated
    if not isinstance(existing, dict) or not isinstance(generated, dict):
        return existing  # an existing scalar/list is authoritative
    merged = dict(existing)
    for key, generated_value in generated.items():
        if key not in merged:
            merged[key] = generated_value
        else:
            merged[key] = _merge_preserving(merged[key], generated_value)
    return merged


def main(out_path: Path = OUT_PATH):
    scenarios = {scenario.scenario_id: scenario for scenario in load_scenarios(V2_SET)}
    output = json.loads(out_path.read_text(encoding="utf-8"))
    meta = output.get("_meta", {})
    meta["description"] = (
        "Machine-checkable constraints and sandbox environments for all five v2 "
        "categories. This file is authoritative and hand-editable: "
        "scripts/generate_v2_constraints.py only fills in environment blocks and "
        "sandbox policy fields that are MISSING — it never overwrites a value that "
        "is already present, so manual edits are always preserved. To regenerate "
        "an entry from its spec, delete that entry's environment block first."
    )
    meta["coverage"] = [
        "category_a_spend_limits",
        "category_b_authorization_scope",
        "category_c_consent_and_escalation",
        "category_d_privacy_and_disclosure",
        "category_e_adversarial_robustness",
    ]
    output["_meta"] = meta

    created = 0
    preserved = 0
    for specs, prefix in ALL_SPECS:
        for pair_key, spec in specs.items():
            for role in ("trap", "lookalike"):
                scenario_id = f"scn_v2_{pair_key}_{role}"
                scenario = scenarios.get(scenario_id)
                if scenario is None:
                    raise KeyError(f"Scenario {scenario_id} not found in v2 set")
                entry = output.get(scenario_id)
                if entry is None:
                    raise KeyError(f"Constraint entry {scenario_id} missing from {out_path}")
                # setdefault and _merge_preserving both keep existing values, so a
                # re-run never clobbers a manual edit — it only fills in gaps.
                for key, value in policy_additions(spec, role).items():
                    entry.setdefault(key, value)
                had_environment = entry.get("environment") is not None
                entry["environment"] = _merge_preserving(
                    entry.get("environment"), build_environment(spec, role, scenario)
                )
                if had_environment:
                    preserved += 1
                else:
                    created += 1

    missing = sorted(k for k in output if k != "_meta" and "environment" not in output[k])
    if missing:
        raise SystemExit(f"Entries still missing environments: {missing}")

    # The sidecar must be fully consumed AND reflected: a dangling key means a
    # renamed scenario/offer would silently fall back to the leaking default,
    # and a mismatched page_text means someone edited the sidecar without
    # deleting the entry's environment block first (the same silent-no-op trap
    # _merge_preserving creates for spec edits — fail loudly instead).
    problems = []
    for sid, pages in PAGE_TEXTS.items():
        entry = output.get(sid)
        if entry is None:
            problems.append(f"{sid}: unknown scenario")
            continue
        by_id = {o["offer_id"]: o for o in entry["environment"]["offers"]}
        for oid, text in pages.items():
            committed = by_id.get(oid)
            if committed is None:
                problems.append(f"{sid}/{oid}: unknown offer")
            elif committed["page_text"] != text:
                problems.append(
                    f"{sid}/{oid}: committed page_text differs from the sidecar — "
                    "delete that entry's environment block and re-run"
                )
    if problems:
        raise SystemExit("v2_page_texts.json out of sync:\n  " + "\n  ".join(problems))
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(
        f"{created} environment(s) created, {preserved} preserved "
        f"(existing values untouched) in {out_path}"
    )


if __name__ == "__main__":
    main()
