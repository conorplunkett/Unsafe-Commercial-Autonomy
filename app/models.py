from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ActionType = Literal[
    "purchase",
    "pay_tool",
    "send_stablecoin",
    "ask_approval",
    "refuse",
    "defer",
]

# Phase 1 uses the first three; the remaining three are Phase 2 ablation layers
# (see app/phase2.py). Phase 1 entry points still validate against their own
# three-condition list in app/runner.py.
ControlCondition = Literal[
    "no_policy",
    "prompt_policy",
    "structured_policy",
    "preflight_check",
    "tool_constraints",
    "approval_gate",
]

Framing = Literal["evaluation", "deployment"]


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
    answer_key_status: Literal["provisional", "locked"] = "provisional"
    safe_to_act: Optional[bool] = None


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
    simulated_outcome: Optional[Literal["safe", "unsafe", "false_refusal", "welfare_loss"]] = None


class EvaluationResult(BaseModel):
    scenario_id: str
    scenario_title: str
    category: str
    agent_id: str
    agent_name: str
    action: AgentAction
    verdict: Literal["safe", "unsafe", "false_refusal", "welfare_loss"]
    failure_metrics: List[str] = Field(default_factory=list)
    unsafe_payment: bool = False
    false_refusal: bool = False
    welfare_loss: bool = False
    user_welfare_score: float = 1.0
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    provider_id: Optional[str] = None
    control_condition: Optional[ControlCondition] = None
    framing: Optional[Framing] = None
    seed: Optional[int] = None
    raw_model_output: Optional[str] = None
    proposed_action: Optional[AgentAction] = None
    block_reasons: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    safe_to_act: Optional[bool] = None
    stakes: Optional[Literal["low", "high"]] = None
    answer_key_status: Optional[Literal["provisional", "locked"]] = None


class RunRequest(BaseModel):
    agent_ids: Optional[List[str]] = None
    model_ids: Optional[List[str]] = None
    control_conditions: Optional[List[ControlCondition]] = None
    scenario_ids: Optional[List[str]] = None
    scenario_set_path: Optional[str] = None
    seeds: Optional[List[int]] = None
    temperature: Optional[float] = None
    reasoning_effort: Optional[Literal["minimal", "low", "medium", "high"]] = None
    live: bool = False
    # Bring-your-own-key: a user-supplied API key and model name for a single
    # provider, used for one live run and never persisted server-side.
    api_key: Optional[str] = None
    byok_model_name: Optional[str] = None


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
    framings: List[Framing] = Field(default_factory=list)
    seeds: List[int] = Field(default_factory=list)
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = None
    live: bool = False
    answer_key_status: Literal["provisional", "locked"] = "provisional"
    scenario_ids: List[str]
    results: List[EvaluationResult]
    events: List[Dict[str, Any]]
    metrics: Dict[str, Any]


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
