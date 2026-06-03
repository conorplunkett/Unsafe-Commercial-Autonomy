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


class RunRequest(BaseModel):
    agent_ids: Optional[List[str]] = None
    scenario_ids: Optional[List[str]] = None


class BenchmarkRun(BaseModel):
    run_id: str
    created_at: str
    agent_ids: List[str]
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

