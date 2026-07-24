import json

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


@pytest.mark.parametrize(
    "raw_merchant_id",
    ["unknown", "unknown_merchant", "<UNKNOWN>", "N/A", "n/a", "None", "NA", "Unknown Merchant"],
)
def test_parse_action_json_normalizes_junk_merchant_id_to_none(raw_merchant_id):
    # Live runs showed refuse/ask_approval actions filling merchant_id with
    # placeholder reasoning text instead of leaving it null. Harmless to
    # scoring (merchant checks are gated on a payment being attempted), but it
    # pollutes run JSON with junk that reads like a real merchant. Normalize
    # known sentinels to None at parse time so stored actions stay honest.
    action = parse_action_json(
        json.dumps(
            {
                "action_type": "refuse",
                "amount": 45.98,
                "merchant_id": raw_merchant_id,
                "sku": None,
                "payment_type": None,
                "approval_requested": False,
                "disclosed_fields": [],
                "rationale": "Over the cap.",
                "payment_attempts": [],
                "recurring": False,
                "refundable": None,
                "category": None,
                "unclear_ingredients": False,
                "followed_external_instruction": False,
                "completed": False,
            }
        )
    )
    assert action.merchant_id is None


def test_parse_action_json_keeps_real_merchant_id():
    action = parse_action_json(
        json.dumps(
            {
                "action_type": "purchase",
                "amount": 24.99,
                "merchant_id": "Staples",
                "sku": None,
                "payment_type": "card",
                "approval_requested": False,
                "disclosed_fields": [],
                "rationale": "Within policy.",
                "payment_attempts": [],
                "recurring": False,
                "refundable": None,
                "category": None,
                "unclear_ingredients": False,
                "followed_external_instruction": False,
                "completed": False,
            }
        )
    )
    assert action.merchant_id == "Staples"


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
        DEFAULT_INKLING_MODEL,
        DEFAULT_KIMI_MODEL,
        DEFAULT_MODEL_IDS,
        DEFAULT_OPENAI_MODEL,
    )

    assert DEFAULT_OPENAI_MODEL == "gpt-5.4-nano"
    assert DEFAULT_ANTHROPIC_MODEL == "claude-haiku-4-5"
    assert DEFAULT_GEMINI_MODEL == "gemini-3.1-flash-lite"
    assert DEFAULT_KIMI_MODEL == "kimi-k2.6"
    assert DEFAULT_INKLING_MODEL == "thinkingmachines/Inkling"
    assert "gemini" in DEFAULT_MODEL_IDS
    assert "kimi" in DEFAULT_MODEL_IDS
    assert "inkling" in DEFAULT_MODEL_IDS


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


def test_resolve_model_ids_accepts_kimi_and_inkling():
    from app.providers import resolve_model_ids

    assert resolve_model_ids(["kimi"]) == ["kimi"]
    assert resolve_model_ids(["inkling"]) == ["inkling"]
    assert {"kimi", "inkling"} <= set(resolve_model_ids(["all"]))


def test_create_provider_returns_kimi_and_inkling_when_live():
    from app.providers import DryRunProvider, InklingProvider, KimiProvider, create_provider

    assert isinstance(create_provider("kimi", live=True), KimiProvider)
    assert isinstance(create_provider("kimi", live=False), DryRunProvider)
    assert isinstance(create_provider("inkling", live=True), InklingProvider)
    assert isinstance(create_provider("inkling", live=False), DryRunProvider)


def test_kimi_preflight_requires_api_key(monkeypatch):
    from app.providers import KimiProvider, ProviderError

    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    provider = KimiProvider(model_name="kimi-k2.6")
    with pytest.raises(ProviderError, match="API key"):
        provider.preflight()


def test_kimi_preflight_rejects_unknown_model(monkeypatch):
    import app.providers as providers_module
    from app.providers import KimiProvider, ProviderError

    monkeypatch.setattr(
        providers_module,
        "available_kimi_models",
        lambda api_key=None, prefix="kimi": ["kimi-k2.6", "kimi-k3"],
    )
    provider = KimiProvider(model_name="kimi-99-ultra", api_key="fake-key")
    with pytest.raises(ProviderError, match="not available"):
        provider.preflight()


def test_kimi_preflight_accepts_known_model(monkeypatch):
    import app.providers as providers_module
    from app.providers import KimiProvider

    monkeypatch.setattr(
        providers_module,
        "available_kimi_models",
        lambda api_key=None, prefix="kimi": ["kimi-k2.6", "kimi-k3"],
    )
    provider = KimiProvider(model_name="kimi-k2.6", api_key="fake-key")
    provider.preflight()  # does not raise


def test_model_display_name_kimi_and_inkling_defaults(monkeypatch):
    from app.providers import DEFAULT_INKLING_MODEL, DEFAULT_KIMI_MODEL, model_display_name

    monkeypatch.delenv("KIMI_MODEL", raising=False)
    monkeypatch.delenv("INKLING_MODEL", raising=False)
    assert model_display_name("kimi") == DEFAULT_KIMI_MODEL
    assert model_display_name("inkling") == DEFAULT_INKLING_MODEL
    monkeypatch.setenv("KIMI_MODEL", "kimi-k3")
    assert model_display_name("kimi") == "kimi-k3"


def test_inkling_preflight_requires_api_key(monkeypatch):
    from app.providers import InklingProvider, ProviderError

    monkeypatch.delenv("INKLING_API_KEY", raising=False)
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)
    provider = InklingProvider()
    with pytest.raises(ProviderError, match="API key"):
        provider.preflight()


def test_inkling_preflight_accepts_configured_key(monkeypatch):
    from app.providers import InklingProvider

    monkeypatch.setenv("INKLING_API_KEY", "fake-key")
    provider = InklingProvider()
    provider.preflight()  # does not raise


def test_inkling_base_url_overridable(monkeypatch):
    from app.providers import DEFAULT_INKLING_BASE_URL, InklingProvider

    monkeypatch.delenv("INKLING_BASE_URL", raising=False)
    assert InklingProvider().base_url == DEFAULT_INKLING_BASE_URL
    monkeypatch.setenv("INKLING_BASE_URL", "https://api.fireworks.ai/inference/v1")
    assert InklingProvider().base_url == "https://api.fireworks.ai/inference/v1"


# --- Grok / DeepSeek / Mistral / Qwen / OpenRouter (OpenAICompatibleProvider) --

def test_new_openai_compatible_providers_construct_with_expected_config():
    from app.providers import (
        DeepSeekProvider,
        GrokProvider,
        MistralProvider,
        OpenRouterProvider,
        QwenProvider,
    )

    grok = GrokProvider()
    assert grok.provider_id == "grok"
    assert grok.base_url == "https://api.x.ai/v1"
    assert grok.model_name == "grok-4.1-fast"
    assert grok.structured_output == "json_schema_strict"

    deepseek = DeepSeekProvider()
    assert deepseek.base_url == "https://api.deepseek.com/v1"
    assert deepseek.model_name == "deepseek-v4-flash"
    assert deepseek.structured_output == "json_object"

    assert MistralProvider().base_url == "https://api.mistral.ai/v1"
    assert QwenProvider().base_url.endswith("/compatible-mode/v1")
    # OpenRouter has no single cheapest default — it must be set explicitly.
    assert OpenRouterProvider().model_name == ""


@pytest.mark.parametrize("model_id", ["grok", "deepseek", "mistral", "qwen", "openrouter"])
def test_create_provider_returns_new_providers_when_live(model_id):
    from app.providers import DryRunProvider, create_provider

    live = create_provider(model_id, live=True)
    assert live.provider_id == model_id
    assert isinstance(create_provider(model_id, live=False), DryRunProvider)


@pytest.mark.parametrize("model_id", ["grok", "deepseek", "mistral", "qwen", "openrouter"])
def test_resolve_model_ids_and_all_include_new_providers(model_id):
    from app.providers import resolve_model_ids

    assert resolve_model_ids([model_id]) == [model_id]
    assert model_id in resolve_model_ids(["all"])


def test_new_provider_response_format_modes():
    from app.providers import DeepSeekProvider, GrokProvider, OpenRouterProvider

    # json_object mode is a plain type with no schema block.
    assert DeepSeekProvider()._response_format() == {"type": "json_object"}
    # strict mode includes the strict flag; non-strict omits it.
    grok_fmt = GrokProvider()._response_format()
    assert grok_fmt["type"] == "json_schema"
    assert grok_fmt["json_schema"]["strict"] is True
    assert "strict" not in OpenRouterProvider()._response_format()["json_schema"]


def test_grok_preflight_requires_api_key(monkeypatch):
    from app.providers import GrokProvider, ProviderError

    for var in ("XAI_API_KEY", "GROK_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ProviderError, match="API key"):
        GrokProvider().preflight()


def test_grok_preflight_rejects_unknown_model(monkeypatch):
    import app.providers as providers_module
    from app.providers import GrokProvider, ProviderError

    monkeypatch.setattr(
        providers_module,
        "_list_openai_compatible_models",
        lambda base_url, api_key, prefix="": ["grok-4.1-fast", "grok-4.3"],
    )
    provider = GrokProvider(model_name="grok-999", api_key="xai-test")
    with pytest.raises(ProviderError, match="not available"):
        provider.preflight()


def test_qwen_preflight_is_key_check_only(monkeypatch):
    # Qwen sets list_prefix=None, so preflight must not attempt a /models call;
    # a present key + model is enough to pass.
    from app.providers import QwenProvider

    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    QwenProvider(model_name="qwen-flash").preflight()  # does not raise


def test_qwen_base_url_overridable(monkeypatch):
    from app.providers import DEFAULT_QWEN_BASE_URL, QwenProvider

    monkeypatch.delenv("QWEN_BASE_URL", raising=False)
    assert QwenProvider().base_url == DEFAULT_QWEN_BASE_URL
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope-us.aliyuncs.com/compatible-mode/v1")
    assert QwenProvider().base_url == "https://dashscope-us.aliyuncs.com/compatible-mode/v1"


def test_grok_accepts_alternate_key_env(monkeypatch):
    # GROK_API_KEY works as a fallback for XAI_API_KEY.
    from app.providers import GrokProvider

    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("GROK_API_KEY", "xai-alt")
    assert GrokProvider(model_name="grok-4.1-fast")._resolved_api_key() == "xai-alt"


def test_model_display_name_new_providers(monkeypatch):
    from app.providers import (
        DEFAULT_DEEPSEEK_MODEL,
        DEFAULT_GROK_MODEL,
        model_display_name,
    )

    for var in ("GROK_MODEL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert model_display_name("grok") == DEFAULT_GROK_MODEL
    assert model_display_name("deepseek") == DEFAULT_DEEPSEEK_MODEL
    monkeypatch.setenv("GROK_MODEL", "grok-4-heavy")
    assert model_display_name("grok") == "grok-4-heavy"


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
