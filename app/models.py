from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


ActionType = Literal[
    "purchase",
    "pay_tool",
    "send_stablecoin",
    "ask_approval",
    "refuse",
    "defer",
]

# Phase 1 uses the first three; the next two are Phase 2 ablation layers
# (see app/phase2.py). Phase 1 entry points still validate against their own
# three-condition list in app/runner.py.
#
# "approval_gate" is read-compat only: the condition was cut from the Phase 2
# grid on 2026-08-05 (#223, see CONDITION_ABLATION_REVIEW.md) but runs recorded
# before the cut legitimately contain it, and without it here those stored
# runs fail to parse (storage.read, publish, recompute). Nothing can run it —
# the runners validate against their own condition lists, which do not
# include it, and SandboxWorld rejects it.
ControlCondition = Literal[
    "no_policy",
    "prompt_policy",
    "structured_policy",
    "required_check",
    "tool_constraints",
    "approval_gate",
]

Framing = Literal["evaluation", "deployment"]

# Phase 2 ablation axis: whether the system prompt adds a deadline on top of the
# scenario's own content. Crossed with framing/control_condition the same way, so
# "the model messes up under time pressure" becomes a reportable rate instead of a
# handful of scenarios that happen to mention a deadline.
Urgency = Literal["none", "time_pressure"]

# Separate Phase 2 axis, crossed with Urgency: whether the delegating human is
# available to answer questions. Kept apart from Urgency on purpose — the two used
# to share one preamble, which made a rise in unsafe rates unattributable between
# "judgment degraded under pressure" and "the model was told not to ask". Crossing
# them gives four cells and separates the two effects.
UserAvailability = Literal["none", "unreachable"]


# The benchmark advertises the delegated card to models as "delegated_card" (the
# Payment capability line in app/providers.build_messages and the Phase 2 sandbox
# prompt), so a model that answers payment_type="delegated_card" is naming the
# same card rail the ["card"] allowlist permits — not choosing a different
# method. These aliases normalize to "card" for payment-rail policy checks.
# Gift/prepaid cards are deliberately excluded: they are a distinct,
# sometimes-prohibited cash-equivalent instrument.
_CARD_RAIL_ALIASES = {
    "card",
    "delegated_card",
    "delegated card",
    "delegated-card",
    "scoped_card",
    "scoped card",
}


# Canonical tokens for AgentAction.disclosed_fields. The scorer's answer keys
# store per-scenario privacy allowlists in this vocabulary, and build_messages /
# the Phase 2 checkout tool tell the model to report disclosures with these
# exact tokens. Without a shared vocabulary the model guesses field names
# ("payment_method", "card_details") and every guess string-diffs into a
# phantom privacy_leakage — same interface bug class as the payment-rail
# aliases above. The list is the union of every allowlist token plus the
# risky fields the trap scenarios offer, so honest reporting of a bad
# disclosure is always expressible. It is interface, not policy: which tokens
# are *allowed* stays per-scenario in the answer key.
DISCLOSURE_FIELD_TOKENS = [
    "name",
    "email",
    "shipping_address",
    "shipping_zip",
    "payment_card_secure_field",
    "preferred_delivery_date",
    "discount_code",
    "date_of_birth",
    "about_you",
    "order_history",
    "account_credentials",
    "contact_list",
    "raw_card_number",
    "health_reason",
]


def normalize_policy_token(value: Optional[str]) -> Optional[str]:
    """Slug-normalize a merchant id or disclosure field for policy comparison.

    Models write "Staples" or "Costco Business" where answer keys store
    "staples" / "costco_business"; exact string comparison turned that casing
    gap into phantom merchant_authorization_violation flags. Lowercase, strip,
    and collapse non-alphanumeric runs to "_" on BOTH sides of every
    comparison so only genuine mismatches survive.
    """
    if value is None:
        return None
    token = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return token or None


# The pay tool's schema tells every model to report disclosures with the
# DISCLOSURE_FIELD_TOKENS vocabulary, while the v2 d-world answer keys name the
# same concepts in per-scenario wording ("payment", "address", "delivery_date").
# String-diffing across the two vocabularies manufactured phantom
# privacy_leakage on models that disclosed exactly the required checkout
# fields — and, through the sandbox's check_policy, induced false refusals.
# Only the pairs that name one concept two ways are aliased. Semantically
# distinct fields (shipping_zip, work_email, password/account_credentials,
# payment_card_on_file, payment_card_secure_link) and every trap-bait token
# (raw_card_number, card_cvv_via_email, card_number_plaintext_chat, ...) stay
# unmapped so genuine leaks keep firing.
DISCLOSURE_FIELD_ALIASES = {
    "payment_card_secure_field": "payment",
    "shipping_address": "address",
    "preferred_delivery_date": "delivery_date",
}


def canonical_disclosure_field(value: Optional[str]) -> Optional[str]:
    """Concept token for a disclosure field: slug-normalize, then alias.

    Applied to BOTH sides of every allowlist comparison, so a key authored in
    either vocabulary accepts a model reporting in either vocabulary.
    """
    token = normalize_policy_token(value)
    return DISCLOSURE_FIELD_ALIASES.get(token, token)


def canonical_payment_type(payment_type: Optional[str]) -> Optional[str]:
    """Normalize a model-reported payment type to its canonical rail token.

    Collapses delegated/scoped card aliases and card-prefixed descriptive
    tokens (models emit e.g. ``"card_pay_in_full"`` / ``"card_standard_in_full"``
    when describing how the card is charged) to ``"card"``. Every other value
    (``"stablecoin"``, ``"wire"``, ``"gift_card"``, ``"bnpl"``, ...) is returned
    unchanged so genuine wrong-rail payments still fail policy checks —
    ``gift_card`` does not start with ``card`` and is never collapsed.
    """
    if payment_type is None:
        return None
    token = payment_type.strip().lower()
    if token in _CARD_RAIL_ALIASES or token.startswith("card"):
        return "card"
    return payment_type


class Scenario(BaseModel):
    scenario_id: str
    title: str
    category: str
    payment_mode: str
    user_instruction: str
    payment_policy: Dict[str, Any]
    hidden_preference: str
    environment: Dict[str, Any]
    expected_safe_behavior: Dict[str, Any]
    unsafe_behavior: str
    measured_failure: str
    phase: Optional[str] = None
    pair_id: Optional[str] = None
    pair_role: Optional[Literal["trap", "lookalike"]] = None
    stakes: Optional[Literal["low", "high"]] = None
    source_situation: Optional[str] = None
    right_answer: Optional[str] = None
    failure_tested: Optional[str] = None
    # "dropped": surveyed scenario whose preference key failed the
    # pre-registered lock with no objective fallback; runs descriptively but
    # is excluded from headline metric denominators (see app/survey.py).
    # "awaiting_survey": scenario whose key the survey has not decided yet —
    # the team's provisional answer is a guess at the preference the survey
    # exists to measure, so it runs but claims nothing until the lock.
    # "objective": a structured rule decides the verdict and no survey is
    # pending, but the set's own survey has not run, so it is scoreable
    # without being survey-validated. Keyed for metrics; not "locked".
    answer_key_status: Literal[
        "provisional", "locked", "objective", "dropped", "awaiting_survey"
    ] = "provisional"
    safe_to_act: Optional[bool] = None
    # True for the trap half of a pair whose expected action is the team's
    # guess at an unstated preference rather than a structured-rule violation
    # (the answer key's `environment.semantic_only`) — the scenarios the
    # survey exists to validate. False (including every lookalike) means the
    # verdict follows from objective policy fields alone. See metrics.by_semantic_only.
    semantic_only: bool = False


class AgentAction(BaseModel):
    action_type: ActionType
    amount: Optional[float] = None
    merchant_id: Optional[str] = None
    sku: Optional[str] = None
    payment_type: Optional[str] = None
    approval_requested: bool = False
    disclosed_fields: List[str] = Field(default_factory=list)
    rationale: str = ""

    payment_attempts: List[float] = Field(default_factory=list)
    recurring: bool = False
    refundable: Optional[bool] = None
    category: Optional[str] = None
    unclear_ingredients: bool = False
    followed_external_instruction: bool = False
    paid_tool_used: bool = False
    tool_cost: Optional[float] = None
    data_source: Optional[str] = None
    delivery_proof_verified: bool = False
    completed: bool = False
    # Self-reported attribution for a non-proceed: distinguishes
    # policy-motivated caution from perceived information gaps in
    # over-refusal analysis. None on proceeds and for pre-field runs.
    ask_reason: Optional[Literal["policy_concern", "missing_details", "other"]] = None
    simulated_outcome: Optional[Literal["safe", "unsafe", "refused_when_safe", "welfare_loss"]] = None

    @field_validator("simulated_outcome", mode="before")
    @classmethod
    def _alias_legacy_outcome(cls, value: Any) -> Any:
        return _LEGACY_VERDICT_ALIASES.get(value, value)


# Read-time alias: runs recorded before the 2026-07 rename stored this verdict
# as "false_refusal". New code writes "refused_when_safe"; this map lets an
# archived run JSON (or the pre-rename Supabase payload) still load.
_LEGACY_VERDICT_ALIASES = {"false_refusal": "refused_when_safe"}

# Read-time alias: runs recorded before the 2026-08 rename stored this control
# condition as "preflight_check". New code writes "required_check"; this map
# lets an archived run JSON, checkpoint, or pre-rename Supabase payload still
# load. (The provider preflight() API smoke test is unrelated and kept its
# name.)
_LEGACY_CONDITION_ALIASES = {"preflight_check": "required_check"}


def _alias_condition(value: Any) -> Any:
    return _LEGACY_CONDITION_ALIASES.get(value, value)


def _alias_conditions(value: Any) -> Any:
    if isinstance(value, list):
        return [_LEGACY_CONDITION_ALIASES.get(item, item) for item in value]
    return value


class EvaluationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scenario_id: str
    scenario_title: str
    category: str
    agent_id: str
    agent_name: str
    action: AgentAction
    verdict: Literal["safe", "unsafe", "refused_when_safe", "welfare_loss", "error"]
    failure_metrics: List[str] = Field(default_factory=list)
    unsafe_payment: bool = False
    # Renamed from false_refusal; validation_alias keeps legacy payloads loadable.
    refused_when_safe: bool = Field(
        default=False,
        validation_alias=AliasChoices("refused_when_safe", "false_refusal"),
    )
    welfare_loss: bool = False
    # A control layer blocked at least one policy-flagged payment attempt this
    # episode (block_reasons carries the codes). Separates attempted-but-blocked
    # harm from realized harm (verdict "unsafe"): a blocked attempt followed by
    # a compliant recovery keeps verdict "safe" but keeps this flag, so the
    # attempt never disappears from metrics.
    attempted_harm: bool = False

    @field_validator("verdict", mode="before")
    @classmethod
    def _alias_legacy_verdict(cls, value: Any) -> Any:
        return _LEGACY_VERDICT_ALIASES.get(value, value)

    @field_validator("control_condition", mode="before")
    @classmethod
    def _alias_legacy_condition(cls, value: Any) -> Any:
        return _alias_condition(value)
    user_welfare_score: float = 1.0
    # Recovery grading. On an unsafe-to-act scenario a stop is always the right
    # *family* of answer, so these never feed the headline unsafe/refused rates;
    # they carry their own axis. recovery_expected is set only where the answer
    # key names exactly one acceptable stop and that recovery is trustworthy
    # (see policies._keyed_stop_action), and missed_recovery is then whether the
    # agent chose a different stop — the "froze instead of routing to the
    # compliant path" failure.
    missed_recovery: bool = False
    recovery_expected: Optional[str] = None
    # Ballot slot this action corresponds to (survey.ACTION_SLOTS, including
    # v2's proceed_fabricate), so a model action and a human vote can be
    # compared in one vocabulary.
    action_slot: Optional[str] = None
    # Share of surveyed humans who preferred / would accept this action, on the
    # scenarios carrying a vote distribution. None where no survey covers it.
    human_preferred_share: Optional[float] = None
    human_acceptable_share: Optional[float] = None
    # The largest preferred-share on this scenario's ballot — the crowd's top
    # choice. Comparing it with human_preferred_share says whether this action
    # WAS the top choice (top_choice_match_rate).
    human_top_share: Optional[float] = None
    # The scenario's own human ask-share, independent of what the agent did.
    # Paired with the agent's ask-rate on the same scenario it gives the
    # ask-calibration axis: an agent should ask where humans split, not
    # uniformly.
    human_ask_share: Optional[float] = None
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    provider_id: Optional[str] = None
    control_condition: Optional[ControlCondition] = None
    framing: Optional[Framing] = None
    urgency: Optional[Urgency] = None
    user_availability: Optional[UserAvailability] = None
    seed: Optional[int] = None
    raw_model_output: Optional[str] = None
    raw_reasoning: Optional[str] = None
    proposed_action: Optional[AgentAction] = None
    block_reasons: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    safe_to_act: Optional[bool] = None
    stakes: Optional[Literal["low", "high"]] = None
    answer_key_status: Optional[
        Literal["provisional", "locked", "objective", "dropped", "awaiting_survey"]
    ] = None
    # Copied from Scenario.semantic_only at scoring time (see app/policies.py).
    semantic_only: bool = False
    # Copied from Scenario.pair_role at scoring time. The headline unsafe rate
    # is trap-conditional (see metrics._answer_key_rates), so metrics need the
    # design label on the result itself; None on results stored before the
    # field existed, which metrics treat as the legacy all-keyed denominator.
    pair_role: Optional[Literal["trap", "lookalike"]] = None


class RunRequest(BaseModel):
    agent_ids: Optional[List[str]] = None
    model_ids: Optional[List[str]] = None
    control_conditions: Optional[List[ControlCondition]] = None

    @field_validator("control_conditions", mode="before")
    @classmethod
    def _alias_legacy_conditions(cls, value: Any) -> Any:
        return _alias_conditions(value)
    scenario_ids: Optional[List[str]] = None
    scenario_set_path: Optional[str] = None
    seeds: Optional[List[int]] = None
    temperature: Optional[float] = None
    reasoning_effort: Optional[Literal["none", "low", "medium", "high", "xhigh"]] = None
    live: bool = False
    # Bring-your-own-key: a user-supplied API key and model name for a single
    # provider, used for one live run and never persisted server-side.
    api_key: Optional[str] = None
    byok_model_name: Optional[str] = None


class MergeSource(BaseModel):
    """One sitting that went into a merged run (see app/merge.py).

    Recorded per source so a stitched run says on its face what it is: which
    runs, from when, contributing how many episodes on which axis levels. A
    merged run without this block would be indistinguishable from one grid run
    that happened in a single sitting, which is exactly the claim it must not
    make.
    """

    run_id: str
    created_at: str
    episode_count: int
    control_conditions: List[str] = Field(default_factory=list)
    framings: List[str] = Field(default_factory=list)
    urgencies: List[str] = Field(default_factory=list)
    user_availabilities: List[str] = Field(default_factory=list)
    seeds: List[int] = Field(default_factory=list)
    # Episodes this source lost to an --on-overlap resolution (0 under the
    # default, which refuses to merge overlapping sources at all).
    dropped_overlaps: int = 0


class BenchmarkRun(BaseModel):
    run_id: str
    created_at: str
    phase: Optional[str] = None
    agent_ids: List[str]
    model_ids: List[str] = Field(default_factory=list)
    # Actual model names (e.g. "gpt-5.4-mini"), distinct from the provider/config
    # ids in model_ids ("openai"). Carried first-class so the leaderboard and the
    # Supabase row can rank and be queried by individual model.
    model_names: List[str] = Field(default_factory=list)
    control_conditions: List[ControlCondition] = Field(default_factory=list)

    @field_validator("control_conditions", mode="before")
    @classmethod
    def _alias_legacy_conditions(cls, value: Any) -> Any:
        return _alias_conditions(value)

    framings: List[Framing] = Field(default_factory=list)
    urgencies: List[Urgency] = Field(default_factory=list)
    user_availabilities: List[UserAvailability] = Field(default_factory=list)
    seeds: List[int] = Field(default_factory=list)
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = None
    live: bool = False
    answer_key_status: Literal["provisional", "locked"] = "provisional"
    scenario_ids: List[str]
    results: List[EvaluationResult]
    events: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    # Set only on runs built by `python -m app.cli merge`: the sittings whose
    # episodes were pooled, and when the pooling happened. Empty on every run
    # that came out of a runner, so a stored run from before merging existed
    # parses unchanged.
    merged_from: List[MergeSource] = Field(default_factory=list)
    merged_at: Optional[str] = None


def parse_model(model_cls: type[BaseModel], value: Any) -> BaseModel:
    """Support both Pydantic v1 and v2 at fixture/API boundaries."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(value)
    return model_cls.parse_obj(value)


def model_to_dict(model: Any) -> Dict[str, Any]:
    """Return JSON-ready dicts across Pydantic versions."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()
