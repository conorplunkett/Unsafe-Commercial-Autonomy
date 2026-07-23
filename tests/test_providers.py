import pytest

from app.models import AgentAction
from app.providers import DryRunProvider, ProviderOutputError, build_messages, parse_action_json
from app.data import get_scenario


def test_build_messages_injects_structured_policy_per_condition():
    # Flaw A regression: the three Phase 1 conditions must differ in what policy
    # the model is shown. Previously the user message was byte-identical across
    # them and the structured policy was never injected.
    scenario = get_scenario("scn_v1_a1_trap")  # carries a $50 spend cap
    user = {
        condition: build_messages(scenario, condition, 1)[1]["content"]
        for condition in ("no_policy", "prompt_policy", "tool_constraints")
    }

    # no_policy: task + situation only, no policy block.
    assert "Payment policy" not in user["no_policy"]
    assert "Structured payment policy" not in user["no_policy"]

    # prompt_policy: the spend cap rendered as natural language.
    assert "Payment policy:" in user["prompt_policy"]
    assert "$50.00" in user["prompt_policy"]

    # tool_constraints: the policy as machine-readable JSON.
    assert "Structured payment policy" in user["tool_constraints"]
    assert '"max_total_spend": 50.0' in user["tool_constraints"]

    # The three user messages are now pairwise distinct.
    assert len(set(user.values())) == 3


def test_parse_action_json_accepts_fenced_structured_output():
    action = parse_action_json(
        """```json
        {
          "action_type": "purchase",
          "amount": 45.98,
          "merchant_id": "costco_business",
          "sku": "charger",
          "payment_type": "card",
          "approval_requested": false,
          "disclosed_fields": ["shipping_address"],
          "rationale": "Within policy.",
          "payment_attempts": [],
          "recurring": false,
          "refundable": null,
          "category": null,
          "unclear_ingredients": false,
          "followed_external_instruction": false,
          "completed": false
        }
        ```"""
    )

    assert isinstance(action, AgentAction)
    assert action.action_type == "purchase"
    assert action.payment_type == "card"


def test_parse_action_json_rejects_invalid_json():
    with pytest.raises(ProviderOutputError):
        parse_action_json("not json")


def test_dry_run_provider_returns_agent_action():
    scenario = get_scenario("scn_v1_a1_lookalike")
    result = DryRunProvider("openai").generate_action(
        scenario,
        "no_policy",
        seed=1,
        temperature=0.7,
    )

    assert result.provider_id == "dryrun_openai"
    assert result.action.action_type == "purchase"
    assert result.action.payment_type == "card"


def test_naive_baseline_provider_always_buys_and_never_asks():
    from app.providers import NaiveBaselineProvider

    provider = NaiveBaselineProvider()
    for scenario_id in ("scn_v1_a1_trap", "scn_v1_a1_lookalike", "scn_v1_c1_trap"):
        scenario = get_scenario(scenario_id)
        result = provider.generate_action(scenario, "no_policy", seed=1, temperature=0.7)
        assert result.action.action_type == "purchase"
        assert result.action.approval_requested is False


def test_create_provider_returns_naive_baseline_even_when_live():
    from app.providers import NaiveBaselineProvider, create_provider

    assert isinstance(create_provider("baseline_naive", live=True), NaiveBaselineProvider)
    assert isinstance(create_provider("baseline_naive", live=False), NaiveBaselineProvider)


def test_openai_provider_param_selection_by_model_family():
    from app.providers import _is_openai_reasoning_model

    assert _is_openai_reasoning_model("gpt-5.5") is True
    assert _is_openai_reasoning_model("o3-mini") is True
    assert _is_openai_reasoning_model("gpt-4o") is False
    assert _is_openai_reasoning_model("") is False


def test_openai_provider_reasoning_effort_configurable():
    from app.providers import OpenAIResponsesProvider

    assert OpenAIResponsesProvider(model_name="gpt-5.5").reasoning_effort == "low"
    provider = OpenAIResponsesProvider(model_name="gpt-5.5", reasoning_effort="high")
    assert provider.reasoning_effort == "high"


def test_openai_empty_model_name_falls_back_to_cheapest_default(monkeypatch):
    from app.providers import DEFAULT_OPENAI_MODEL, OpenAIResponsesProvider, ProviderError

    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    provider = OpenAIResponsesProvider(model_name="", api_key="sk-test")
    assert provider.model_name == DEFAULT_OPENAI_MODEL

    # Explicitly blanking the env var still surfaces the clear error.
    monkeypatch.setenv("OPENAI_MODEL", "")
    provider = OpenAIResponsesProvider(model_name="", api_key="sk-test")
    with pytest.raises(ProviderError, match="model name"):
        provider.preflight()


def test_openai_preflight_requires_api_key(monkeypatch):
    from app.providers import OpenAIResponsesProvider, ProviderError

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIResponsesProvider(model_name="gpt-5.5")
    with pytest.raises(ProviderError, match="API key"):
        provider.preflight()


def test_openai_preflight_rejects_unknown_model(monkeypatch):
    # Simulate the real failure mode: the model id does not exist for the
    # account. retrieve() raises, and preflight must surface a clear, actionable
    # error rather than letting the grid burn calls one combo at a time.
    import openai

    from app.providers import OpenAIResponsesProvider, ProviderError

    class _Models:
        def retrieve(self, model_id):
            raise RuntimeError(f"model {model_id} not found")

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            self.models = _Models()

    monkeypatch.setattr(openai, "OpenAI", _FakeClient)
    provider = OpenAIResponsesProvider(model_name="gpt-5.5-nano", api_key="sk-test")
    with pytest.raises(ProviderError, match="not available to this account"):
        provider.preflight()


def test_openai_preflight_accepts_known_model(monkeypatch):
    import openai

    from app.providers import OpenAIResponsesProvider

    class _Models:
        def retrieve(self, model_id):
            return {"id": model_id}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            self.models = _Models()

    monkeypatch.setattr(openai, "OpenAI", _FakeClient)
    provider = OpenAIResponsesProvider(model_name="gpt-5.5", api_key="sk-test")
    provider.preflight()  # does not raise


def test_defaults_are_cheapest_current_models():
    # Defaults minimize spend when no *_MODEL env var is set; prices verified
    # 2026-07-22 (see the comment block in app/providers.py).
    from app.providers import (
        DEFAULT_ANTHROPIC_MODEL,
        DEFAULT_GEMINI_MODEL,
        DEFAULT_MODEL_IDS,
        DEFAULT_OPENAI_MODEL,
    )

    assert DEFAULT_OPENAI_MODEL == "gpt-5.4-nano"
    assert DEFAULT_ANTHROPIC_MODEL == "claude-haiku-4-5"
    assert DEFAULT_GEMINI_MODEL == "gemini-2.5-flash-lite"
    assert "gemini" in DEFAULT_MODEL_IDS


def test_resolve_model_ids_accepts_gemini():
    from app.providers import resolve_model_ids

    assert resolve_model_ids(["gemini"]) == ["gemini"]
    assert "gemini" in resolve_model_ids(["all"])


def test_create_provider_returns_gemini_when_live():
    from app.providers import DryRunProvider, GeminiProvider, create_provider

    assert isinstance(create_provider("gemini", live=True), GeminiProvider)
    assert isinstance(create_provider("gemini", live=False), DryRunProvider)


def test_gemini_preflight_requires_api_key(monkeypatch):
    from app.providers import GeminiProvider, ProviderError

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    provider = GeminiProvider(model_name="gemini-2.5-flash-lite")
    with pytest.raises(ProviderError, match="API key"):
        provider.preflight()


def test_gemini_preflight_rejects_unknown_model(monkeypatch):
    import app.providers as providers_module
    from app.providers import GeminiProvider, ProviderError

    monkeypatch.setattr(
        providers_module,
        "available_gemini_models",
        lambda api_key=None, prefix="gemini": ["gemini-2.5-flash-lite"],
    )
    provider = GeminiProvider(model_name="gemini-99-ultra", api_key="fake-key")
    with pytest.raises(ProviderError, match="not available"):
        provider.preflight()


def test_gemini_preflight_accepts_known_model(monkeypatch):
    import app.providers as providers_module
    from app.providers import GeminiProvider

    monkeypatch.setattr(
        providers_module,
        "available_gemini_models",
        lambda api_key=None, prefix="gemini": ["gemini-2.5-flash-lite"],
    )
    provider = GeminiProvider(model_name="gemini-2.5-flash-lite", api_key="fake-key")
    provider.preflight()  # does not raise


def test_model_display_name_gemini_defaults(monkeypatch):
    from app.providers import DEFAULT_GEMINI_MODEL, model_display_name

    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert model_display_name("gemini") == DEFAULT_GEMINI_MODEL
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    assert model_display_name("gemini") == "gemini-3.1-flash-lite"


def test_action_schema_constrains_payment_type_and_documents_self_reports():
    # payment_type must be an enum (free text drifts into invented composites
    # that misread as disallowed rails), and the self-report booleans the
    # scorer trusts need explicit semantics.
    from app.providers import ACTION_JSON_SCHEMA

    pt = ACTION_JSON_SCHEMA["properties"]["payment_type"]
    enum_branch = next(b for b in pt["anyOf"] if b.get("type") == "string")
    assert "card" in enum_branch["enum"]
    assert "bnpl" in enum_branch["enum"]
    assert "gift_card" in enum_branch["enum"]

    fei = ACTION_JSON_SCHEMA["properties"]["followed_external_instruction"]
    assert "complied" in fei["description"]
    completed = ACTION_JSON_SCHEMA["properties"]["completed"]
    assert "free source" in completed["description"]
