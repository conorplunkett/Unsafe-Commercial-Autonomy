"""Phase 2 tool-loop providers: live vendor adapters and offline scripted agents.

Each live adapter translates the sandbox's vendor-neutral tool schemas into the
vendor's tool-calling format and drives a conversation until the world reports
a terminal state or the turn budget runs out. Scripted agents drive the same
SandboxWorld deterministically for tests and --dry-run.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

from ..providers import (
    ANTHROPIC_DEFAULT_THINKING_PREFIXES,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_KIMI_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_TRANSIENT_RETRIES,
    GEMINI_OPENAI_BASE_URL,
    ProviderError,
    RateLimitGate,
    TransientRetryPolicy,
    _anthropic_rejects_temperature,
    _anthropic_supports_effort,
    _gemini_thinking_extra_body,
    _is_openai_reasoning_model,
    _openai_reasoning_params,
    available_gemini_models,
    extract_chat_reasoning,
)
from .sandbox import MAX_TURNS, SandboxWorld, evaluate_payment_policy, tool_schemas


PHASE2_MODEL_IDS = [
    "openai",
    "anthropic",
    "gemini",
    "kimi",
    "inkling",
    "grok",
    "deepseek",
    "mistral",
    "qwen",
    "openrouter",
    "openweights",
    "scripted_diligent",
    "scripted_naive",
]
LIVE_MODEL_IDS = {
    "openai",
    "anthropic",
    "gemini",
    "kimi",
    "inkling",
    "grok",
    "deepseek",
    "mistral",
    "qwen",
    "openrouter",
    "openweights",
}


@dataclass
class EpisodeResult:
    raw_outputs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    # One entry per turn that carried reasoning (thinking blocks,
    # reasoning_content, <think> tags), mirroring raw_outputs' per-turn shape.
    reasoning_outputs: List[str] = field(default_factory=list)


class BaseEpisodeProvider:
    provider_id: str
    model_name: str

    def preflight(self) -> None:
        """Validate the provider can run before the episode grid executes.

        Called once per provider by the Phase 2 runner. Without this, a
        missing key or wrong model id is caught inside each episode's tool
        loop and recorded as a per-episode error — so a misconfigured live
        run walks the entire (condition, framing, scenario, seed) grid and
        saves a junk run instead of aborting with one clear message.
        Offline providers leave this a no-op.
        """
        return None

    def run_episode(
        self,
        world: SandboxWorld,
        system_prompt: str,
        user_prompt: str,
        seed: int,
        temperature: float,
    ) -> EpisodeResult:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Shared live loop
# ---------------------------------------------------------------------------

class ToolLoopProvider(BaseEpisodeProvider):
    """Drives the generic tool loop; subclasses implement vendor transport."""

    # Per-turn transient-failure budget, mirroring the Phase 1 policy in
    # app/runner.py::_generate_with_retry. Phase 1 retries a single-shot call;
    # a Phase 2 episode is up to MAX_TURNS calls, so the budget is per turn —
    # one 429 twelve turns in should not throw away the eleven turns already
    # paid for. Rate limits get their own minutes-scale wall-clock budget
    # inside TransientRetryPolicy, also per turn.
    transient_retries: int = DEFAULT_TRANSIENT_RETRIES
    # Shared by every worker of a run (the runner attaches one): when any
    # worker hits a 429, all workers hold at their next attempt instead of
    # hammering a provider that just said slow down.
    rate_limit_gate: Optional[RateLimitGate] = None
    # Injection seam for tests, so they assert the backoff schedule without
    # waiting it out (same pattern as _generate_with_retry's `sleep` argument).
    _sleep: Callable[[float], None] = staticmethod(time.sleep)

    def start_conversation(self, system_prompt: str, user_prompt: str, tools: List[Dict[str, Any]], temperature: float) -> None:
        raise NotImplementedError

    def step(self, tool_results: Optional[List[Dict[str, Any]]]) -> tuple[str, List[Dict[str, Any]]]:
        """Send pending state; return (assistant_text, tool_calls).

        tool_calls: [{"id": str, "name": str, "arguments": dict}]
        tool_results (for the previous turn): [{"id": str, "content": dict}]
        """
        raise NotImplementedError

    def _record_reasoning(self, text: Optional[str]) -> None:
        # Vendor step() bodies push captured reasoning here; run_episode drains
        # it after each turn. Lazy init so bare stubs that never record still work.
        if not text:
            return
        buf = getattr(self, "_reasoning_buffer", None)
        if buf is None:
            buf = self._reasoning_buffer = []
        buf.append(text)

    def _step_with_retry(self, tool_results: Optional[List[Dict[str, Any]]]):
        """One turn, retrying transient transport failures with backoff.

        Providers wrap everything as ProviderError, so the retryable/terminal
        split comes from TransientRetryPolicy walking the ``raise ... from
        exc`` chain: 5xx and dropped connections get the short attempts, a
        429 keeps retrying on its minutes-scale budget (Retry-After honored,
        the shared gate pausing every worker), and a 400 or a bad model id
        still fails on the first one.
        """
        pending = tool_results
        policy = TransientRetryPolicy(
            transient_retries=self.transient_retries, gate=self.rate_limit_gate
        )
        while True:
            if self.rate_limit_gate is not None:
                # Hold while another worker's rate-limit pause is active.
                self.rate_limit_gate.wait(self._sleep)
            try:
                return self.step(pending)
            except ProviderError as exc:
                if not policy.wait_before_retry(exc, self._sleep):
                    raise
                # Every transport folds `tool_results` into its own conversation
                # state *before* issuing the request and commits the reply only
                # after it succeeds, so this turn is already staged. Re-sending
                # them would append duplicates; None re-issues the same request.
                pending = None

    def run_episode(self, world, system_prompt, user_prompt, seed, temperature) -> EpisodeResult:
        result = EpisodeResult()
        tools = tool_schemas(world.control_condition)
        self._seed = seed  # transports that support a sampler seed pick it up
        # Provider instances are pooled and reused across episodes (see
        # _ProviderPool in runner.py): a turn whose step() raised after
        # recording reasoning but before this loop's drain point ran would
        # otherwise leave that reasoning sitting in the buffer for the NEXT
        # episode to inherit. Reset fresh every episode.
        self._reasoning_buffer = []
        try:
            self.start_conversation(system_prompt, user_prompt, tools, temperature)
            tool_results: Optional[List[Dict[str, Any]]] = None
            for _ in range(MAX_TURNS):
                text, tool_calls = self._step_with_retry(tool_results)
                if text:
                    result.raw_outputs.append(text)
                # Drain whatever this turn's vendor step() captured via
                # _record_reasoning before either early return below, so the
                # turn that ends the episode still keeps its reasoning.
                buf = getattr(self, "_reasoning_buffer", None)
                if buf:
                    result.reasoning_outputs.extend(buf)
                    buf.clear()
                if not tool_calls:
                    return result  # model stopped talking; assemble from world state
                tool_results = []
                for call in tool_calls:
                    payload = world.handle_tool(call["name"], call.get("arguments") or {})
                    tool_results.append({"id": call["id"], "content": payload})
                if world.done:
                    if world.repeated_call_error:
                        result.error = world.repeated_call_error
                    return result
            result.error = "turn_budget_exhausted"
        except ProviderError as exc:
            result.error = str(exc)
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
        return result


class OpenAIToolProvider(ToolLoopProvider):
    provider_id = "openai"

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None, reasoning_effort: Optional[str] = None):
        # Default to the cheapest current model when OPENAI_MODEL is unset, matching
        # the Phase 1 provider so `phase2-eval --models openai` runs without extra config.
        self.model_name = model_name or os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
        self.api_key = api_key
        self.reasoning_effort = reasoning_effort or os.environ.get("OPENAI_REASONING_EFFORT") or "low"
        self._client = None
        self._previous_response_id: Optional[str] = None
        self._pending_input: List[Dict[str, Any]] = []
        self._tools: List[Dict[str, Any]] = []
        self._temperature = 0.7

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.model_name:
            raise ProviderError("Set OPENAI_MODEL to run the OpenAI Phase 2 provider.")
        api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError("Set OPENAI_API_KEY to run the OpenAI Phase 2 provider.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("Install the openai package to run OpenAI evals.") from exc
        self._client = OpenAI(api_key=api_key)
        return self._client

    def preflight(self) -> None:
        client = self._ensure_client()
        # One cheap metadata lookup confirms the id exists and is reachable by
        # this account before the grid spends real episode calls on it
        # (mirrors the Phase 1 OpenAI provider's preflight).
        try:
            client.models.retrieve(self.model_name)
        except Exception as exc:
            raise ProviderError(
                f"OpenAI model {self.model_name!r} is not available to this account: {exc}. "
                "List valid ids with `python -m app.cli models` and set OPENAI_MODEL to one of them."
            ) from exc

    def start_conversation(self, system_prompt, user_prompt, tools, temperature):
        self._previous_response_id = None
        self._temperature = temperature
        self._tools = [
            {"type": "function", "name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}
            for tool in tools
        ]
        self._pending_input = [
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def step(self, tool_results):
        client = self._ensure_client()
        if tool_results:
            self._pending_input = [
                {"type": "function_call_output", "call_id": item["id"], "output": json.dumps(item["content"])}
                for item in tool_results
            ]
        params: Dict[str, Any] = {
            "model": self.model_name,
            "input": self._pending_input,
            "tools": self._tools,
        }
        if self._previous_response_id:
            params["previous_response_id"] = self._previous_response_id
        if _is_openai_reasoning_model(self.model_name):
            params["reasoning"] = _openai_reasoning_params(self.reasoning_effort)
        else:
            params["temperature"] = self._temperature
        try:
            response = client.responses.create(**params)
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
        self._previous_response_id = response.id
        self._pending_input = []
        text_chunks: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        for item in response.output or []:
            item_type = getattr(item, "type", None)
            if item_type == "function_call":
                try:
                    arguments = json.loads(item.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                tool_calls.append({"id": item.call_id, "name": item.name, "arguments": arguments})
            elif item_type == "message":
                for block in getattr(item, "content", []) or []:
                    text = getattr(block, "text", None)
                    if text:
                        text_chunks.append(text)
            elif item_type == "reasoning":
                summary = getattr(item, "summary", None) or []
                self._record_reasoning(
                    "\n\n".join(t for t in ((getattr(b, "text", "") or "") for b in summary) if t)
                )
        return "".join(text_chunks), tool_calls


class AnthropicToolProvider(ToolLoopProvider):
    provider_id = "anthropic"

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ):
        # Cheapest current model by default (matches the Phase 1 provider).
        self.model_name = model_name or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        self.api_key = api_key
        # run_phase2_evaluation sets this after construction when --reasoning-effort
        # is passed; unset means send no effort at all.
        self.reasoning_effort = reasoning_effort
        self._client = None
        self._system = ""
        self._messages: List[Dict[str, Any]] = []
        self._tools: List[Dict[str, Any]] = []
        self._temperature = 0.7
        self._last_assistant_content: Any = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.model_name:
            raise ProviderError("Set ANTHROPIC_MODEL to run the Anthropic Phase 2 provider.")
        api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("Set ANTHROPIC_API_KEY to run the Anthropic Phase 2 provider.")
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ProviderError("Install the anthropic package to run Anthropic evals.") from exc
        self._client = Anthropic(api_key=api_key)
        return self._client

    def preflight(self) -> None:
        # Raises ProviderError when the model name or key is unset/missing.
        self._ensure_client()

    def start_conversation(self, system_prompt, user_prompt, tools, temperature):
        self._system = system_prompt
        self._temperature = temperature
        self._tools = [
            {"name": tool["name"], "description": tool["description"], "input_schema": tool["parameters"]}
            for tool in tools
        ]
        self._messages = [{"role": "user", "content": user_prompt}]
        self._last_assistant_content = None

    def step(self, tool_results):
        client = self._ensure_client()
        if tool_results:
            self._messages.append({"role": "assistant", "content": self._last_assistant_content})
            self._messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": item["id"], "content": json.dumps(item["content"])}
                        for item in tool_results
                    ],
                }
            )
        # Same model gating as the Phase 1 provider (app/providers.py): Opus
        # 4.7+/Opus 5/Sonnet 5/Fable/Mythos reject sampling params with a 400,
        # and take reasoning depth through output_config.effort instead.
        effort = self.reasoning_effort if _anthropic_supports_effort(self.model_name) else None
        default_thinking = (self.model_name or "").lower().startswith(
            ANTHROPIC_DEFAULT_THINKING_PREFIXES
        )
        params: Dict[str, Any] = {
            "model": self.model_name,
            # Thinking tokens count against max_tokens, so leave headroom when
            # the model reasons before each tool call.
            "max_tokens": 8000 if (effort or default_thinking) else 2000,
            "system": self._system,
            "tools": self._tools,
            "messages": self._messages,
        }
        if effort:
            params["output_config"] = {"effort": effort}
        if not _anthropic_rejects_temperature(self.model_name):
            params["temperature"] = self._temperature
        try:
            response = client.messages.create(**params)
        except Exception as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc
        self._last_assistant_content = response.content
        text_chunks: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_chunks.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "arguments": dict(block.input or {})})
            elif block_type == "thinking":
                self._record_reasoning(getattr(block, "thinking", "") or "")
            elif block_type == "redacted_thinking":
                self._record_reasoning("[redacted_thinking]")
        return "".join(text_chunks), tool_calls


class OpenWeightsToolProvider(ToolLoopProvider):
    provider_id = "openweights"

    def __init__(self, model_name: Optional[str] = None, base_url: Optional[str] = None):
        self.model_name = model_name or os.environ.get("OPENWEIGHTS_MODEL", "")
        self.base_url = (base_url or os.environ.get("OPENWEIGHTS_BASE_URL") or "").rstrip("/")
        self._messages: List[Dict[str, Any]] = []
        self._tools: List[Dict[str, Any]] = []
        self._temperature = 0.7
        self._seed: Optional[int] = None

    def preflight(self) -> None:
        if not self.base_url:
            raise ProviderError("Set OPENWEIGHTS_BASE_URL to run the open-weights Phase 2 provider.")
        if not self.model_name:
            raise ProviderError("Set OPENWEIGHTS_MODEL to run the open-weights Phase 2 provider.")

    def start_conversation(self, system_prompt, user_prompt, tools, temperature):
        if not self.base_url:
            raise ProviderError("Set OPENWEIGHTS_BASE_URL to run the open-weights Phase 2 provider.")
        if not self.model_name:
            raise ProviderError("Set OPENWEIGHTS_MODEL to run the open-weights Phase 2 provider.")
        self._temperature = temperature
        self._tools = [
            {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}}
            for tool in tools
        ]
        self._messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def step(self, tool_results):
        if tool_results:
            for item in tool_results:
                self._messages.append(
                    {"role": "tool", "tool_call_id": item["id"], "content": json.dumps(item["content"])}
                )
        try:
            response = httpx.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ.get('OPENWEIGHTS_API_KEY', 'local')}"},
                json={
                    "model": self.model_name,
                    "messages": self._messages,
                    "temperature": self._temperature,
                    # Real sampler seed where the API supports it (vLLM does).
                    **({"seed": self._seed} if self._seed is not None else {}),
                    "tools": self._tools,
                },
                timeout=180,
            )
            response.raise_for_status()
        except Exception as exc:
            raise ProviderError(f"Open-weights request failed: {exc}") from exc
        message = response.json()["choices"][0]["message"]
        reasoning, content = extract_chat_reasoning(message)
        self._record_reasoning(reasoning)
        # Replay keeps content verbatim but drops vendor reasoning fields: no
        # chat-completions request schema accepts them, and DeepSeek's reasoner
        # 400s when reasoning_content is echoed back in messages.
        self._messages.append(
            {k: v for k, v in message.items() if k not in ("reasoning_content", "reasoning")}
        )
        tool_calls = [
            {
                "id": call["id"],
                "name": call["function"]["name"],
                "arguments": json.loads(call["function"].get("arguments") or "{}"),
            }
            for call in message.get("tool_calls") or []
        ]
        return content, tool_calls


class KimiToolProvider(ToolLoopProvider):
    """Kimi (Moonshot AI) via its OpenAI-compatible chat-completions endpoint.

    Same tool-loop shape as OpenWeightsToolProvider; only the base URL and
    auth differ (mirrors app/providers.py::KimiProvider for Phase 1).
    """

    provider_id = "kimi"
    _base_url = "https://api.moonshot.ai/v1"

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        # Cheapest current model by default (matches the Phase 1 provider).
        self.model_name = model_name or os.environ.get("KIMI_MODEL") or DEFAULT_KIMI_MODEL
        self.api_key = api_key
        self._messages: List[Dict[str, Any]] = []
        self._tools: List[Dict[str, Any]] = []
        self._temperature = 0.7

    def _resolved_api_key(self) -> str:
        api_key = self.api_key or os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY")
        if not api_key:
            raise ProviderError("Set KIMI_API_KEY to run the Kimi Phase 2 provider.")
        return api_key

    def preflight(self) -> None:
        self._resolved_api_key()
        if not self.model_name:
            raise ProviderError("Set KIMI_MODEL to run the Kimi Phase 2 provider.")

    def start_conversation(self, system_prompt, user_prompt, tools, temperature):
        if not self.model_name:
            raise ProviderError("Set KIMI_MODEL to run the Kimi Phase 2 provider.")
        self._temperature = temperature
        self._tools = [
            {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}}
            for tool in tools
        ]
        self._messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def step(self, tool_results):
        if tool_results:
            for item in tool_results:
                self._messages.append(
                    {"role": "tool", "tool_call_id": item["id"], "content": json.dumps(item["content"])}
                )
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._resolved_api_key()}"},
                json={
                    "model": self.model_name,
                    "messages": self._messages,
                    "temperature": self._temperature,
                    "tools": self._tools,
                },
                timeout=180,
            )
            response.raise_for_status()
        except Exception as exc:
            raise ProviderError(f"Kimi request failed: {exc}") from exc
        message = response.json()["choices"][0]["message"]
        reasoning, content = extract_chat_reasoning(message)
        self._record_reasoning(reasoning)
        # Replay keeps content verbatim but drops vendor reasoning fields: no
        # chat-completions request schema accepts them, and DeepSeek's reasoner
        # 400s when reasoning_content is echoed back in messages.
        self._messages.append(
            {k: v for k, v in message.items() if k not in ("reasoning_content", "reasoning")}
        )
        tool_calls = [
            {
                "id": call["id"],
                "name": call["function"]["name"],
                "arguments": json.loads(call["function"].get("arguments") or "{}"),
            }
            for call in message.get("tool_calls") or []
        ]
        return content, tool_calls


class InklingToolProvider(ToolLoopProvider):
    """Inkling (Thinking Machines Lab) via an OpenAI-compatible inference host.

    Defaults to Together AI's slug/endpoint (mirrors
    app/providers.py::InklingProvider for Phase 1); point
    INKLING_BASE_URL/INKLING_MODEL at another host to switch providers.
    """

    provider_id = "inkling"
    _default_base_url = "https://api.together.xyz/v1"
    _default_model = "thinkingmachines/Inkling"

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.model_name = model_name or os.environ.get("INKLING_MODEL", self._default_model)
        self.base_url = (os.environ.get("INKLING_BASE_URL") or self._default_base_url).rstrip("/")
        self.api_key = api_key
        self._messages: List[Dict[str, Any]] = []
        self._tools: List[Dict[str, Any]] = []
        self._temperature = 0.7
        self._seed: Optional[int] = None

    def _resolved_api_key(self) -> str:
        api_key = self.api_key or os.environ.get("INKLING_API_KEY") or os.environ.get("TOGETHER_API_KEY")
        if not api_key:
            raise ProviderError("Set INKLING_API_KEY (or TOGETHER_API_KEY) to run the Inkling Phase 2 provider.")
        return api_key

    def preflight(self) -> None:
        self._resolved_api_key()

    def start_conversation(self, system_prompt, user_prompt, tools, temperature):
        self._temperature = temperature
        self._tools = [
            {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}}
            for tool in tools
        ]
        self._messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def step(self, tool_results):
        if tool_results:
            for item in tool_results:
                self._messages.append(
                    {"role": "tool", "tool_call_id": item["id"], "content": json.dumps(item["content"])}
                )
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._resolved_api_key()}"},
                json={
                    "model": self.model_name,
                    "messages": self._messages,
                    "temperature": self._temperature,
                    **({"seed": self._seed} if self._seed is not None else {}),
                    "tools": self._tools,
                },
                timeout=180,
            )
            response.raise_for_status()
        except Exception as exc:
            raise ProviderError(f"Inkling request failed: {exc}") from exc
        message = response.json()["choices"][0]["message"]
        reasoning, content = extract_chat_reasoning(message)
        self._record_reasoning(reasoning)
        # Replay keeps content verbatim but drops vendor reasoning fields: no
        # chat-completions request schema accepts them, and DeepSeek's reasoner
        # 400s when reasoning_content is echoed back in messages.
        self._messages.append(
            {k: v for k, v in message.items() if k not in ("reasoning_content", "reasoning")}
        )
        tool_calls = [
            {
                "id": call["id"],
                "name": call["function"]["name"],
                "arguments": json.loads(call["function"].get("arguments") or "{}"),
            }
            for call in message.get("tool_calls") or []
        ]
        return content, tool_calls


class OpenAICompatToolProvider(ToolLoopProvider):
    """Shared Phase 2 transport for hosted OpenAI-compatible chat endpoints.

    Grok, DeepSeek, Mistral, Qwen, and OpenRouter drive the same
    ``POST {base}/chat/completions`` tool loop as the open-weights/Kimi paths;
    a subclass only sets the config below.
    """

    # Subclasses override these.
    provider_id = "openai_compatible"
    display_label = "OpenAI-compatible"
    default_base_url = ""
    base_url_env: Optional[str] = None
    model_env = ""
    default_model = ""
    api_key_envs: tuple[str, ...] = ()
    send_seed = False

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        env_model = os.environ.get(self.model_env, "") if self.model_env else ""
        self.model_name = model_name or env_model or self.default_model
        env_base = os.environ.get(self.base_url_env) if self.base_url_env else None
        self.base_url = (env_base or self.default_base_url).rstrip("/")
        self.api_key = api_key
        self._messages: List[Dict[str, Any]] = []
        self._tools: List[Dict[str, Any]] = []
        self._temperature = 0.7
        self._seed: Optional[int] = None

    def _resolved_api_key(self) -> str:
        for name in self.api_key_envs:
            value = self.api_key or os.environ.get(name)
            if value:
                return value
        canonical = self.api_key_envs[0] if self.api_key_envs else ""
        raise ProviderError(f"Set {canonical} to run the {self.display_label} Phase 2 provider.")

    def preflight(self) -> None:
        self._resolved_api_key()
        if not self.model_name:
            raise ProviderError(f"Set {self.model_env} to run the {self.display_label} Phase 2 provider.")

    def start_conversation(self, system_prompt, user_prompt, tools, temperature):
        if not self.model_name:
            raise ProviderError(f"Set {self.model_env} to run the {self.display_label} Phase 2 provider.")
        self._temperature = temperature
        self._tools = [
            {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}}
            for tool in tools
        ]
        self._messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def step(self, tool_results):
        if tool_results:
            for item in tool_results:
                self._messages.append(
                    {"role": "tool", "tool_call_id": item["id"], "content": json.dumps(item["content"])}
                )
        body: Dict[str, Any] = {
            "model": self.model_name,
            "messages": self._messages,
            "temperature": self._temperature,
            "tools": self._tools,
        }
        if self.send_seed and self._seed is not None:
            body["seed"] = self._seed
        if self.provider_id == "gemini":
            # Env-gated thought-summary opt-in; {} (the default) for every
            # other vendor on this shared transport.
            body.update(_gemini_thinking_extra_body())
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._resolved_api_key()}"},
                json=body,
                timeout=180,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"{self.display_label} request failed: {exc}\nResponse body: {exc.response.text}"
            ) from exc
        except Exception as exc:
            raise ProviderError(f"{self.display_label} request failed: {exc}") from exc
        message = response.json()["choices"][0]["message"]
        reasoning, content = extract_chat_reasoning(message)
        self._record_reasoning(reasoning)
        # Replay keeps content verbatim but drops vendor reasoning fields: no
        # chat-completions request schema accepts them, and DeepSeek's reasoner
        # 400s when reasoning_content is echoed back in messages.
        self._messages.append(
            {k: v for k, v in message.items() if k not in ("reasoning_content", "reasoning")}
        )
        tool_calls = [
            {
                "id": call["id"],
                "name": call["function"]["name"],
                "arguments": json.loads(call["function"].get("arguments") or "{}"),
            }
            for call in message.get("tool_calls") or []
        ]
        return content, tool_calls


class GeminiToolProvider(OpenAICompatToolProvider):
    """Google Gemini via its OpenAI-compatible endpoint.

    Same key/model/env contract as the Phase 1 ``GeminiProvider`` — the tool
    loop is the only difference — so a model id that works in Phase 1 works
    here. Gemini's OpenAI-compat layer rejects ``seed`` (400 "Unknown name
    seed"), which is why ``send_seed`` stays off; the seed still perturbs the
    episode through the prompt.

    Live Phase 2 runs have twice shown gemini-3.1-flash-lite episodes stuck
    calling one tool with identical arguments turn after turn, never
    progressing (search_offers on scn_v2_c16_trap; check_policy on
    scn_v2_d13_trap, against an unchanging "block" verdict) -- until
    SandboxWorld's repeated-call guard (REPEAT_CALL_FAIL_THRESHOLD in
    sandbox.py) started ending those episodes early with
    repeated_call_detected instead of letting them run out the clock. That
    guard is provider-agnostic and treats the symptom; this is the likely
    cause, upstream of anything in this file. ``OpenAICompatToolProvider
    .step`` stores and replays the raw response ``message``, stripping only
    the human-readable reasoning_content/reasoning text fields (a separate,
    unrelated fix for a DeepSeek 400 on echoed reasoning) -- tool_calls
    entries, where a thought_signature would actually live, pass through
    untouched. Gemini 3.x models keep some thinking on for every turn
    (Flash-Lite defaults to "minimal" but, unlike 2.5 models, cannot disable
    it via reasoning_effort) and tie multi-turn tool-call coherence to that
    internal thought_signature; Google's OpenAI-compat surface has
    independently reported gaps round-tripping it for this endpoint and model
    generation (https://github.com/openai/codex/issues/7519,
    https://github.com/BerriAI/litellm/issues/25322) -- consistent with a
    model that loses track of a tool call it already made and re-issues it
    identically. No fix on this side of the wire can round-trip a signature
    the endpoint doesn't hand back.
    """

    provider_id = "gemini"
    display_label = "Gemini"
    default_base_url = GEMINI_OPENAI_BASE_URL
    model_env = "GEMINI_MODEL"
    default_model = DEFAULT_GEMINI_MODEL
    api_key_envs = ("GEMINI_API_KEY", "GOOGLE_API_KEY")

    def preflight(self) -> None:
        api_key = self._resolved_api_key()
        if not self.model_name:
            raise ProviderError("Set GEMINI_MODEL to run the Gemini Phase 2 provider.")
        # One cheap models-list call confirms the id exists for this key before
        # the episode grid spends real calls on it (mirrors the Phase 1
        # Gemini preflight).
        model_ids = available_gemini_models(api_key=api_key)
        if self.model_name.removeprefix("models/") not in model_ids:
            raise ProviderError(
                f"Gemini model {self.model_name!r} is not available to this key. "
                "List valid ids with `python -m app.cli models --provider gemini` and set GEMINI_MODEL."
            )


class GrokToolProvider(OpenAICompatToolProvider):
    provider_id = "grok"
    display_label = "Grok"
    default_base_url = "https://api.x.ai/v1"
    model_env = "GROK_MODEL"
    # Mirrors app/providers.py::DEFAULT_GROK_MODEL — grok-4.1-fast was retired
    # 2026-05-15; see the comment there for the current lineup.
    default_model = "grok-4.20-0309-non-reasoning"
    api_key_envs = ("XAI_API_KEY", "GROK_API_KEY")


class DeepSeekToolProvider(OpenAICompatToolProvider):
    provider_id = "deepseek"
    display_label = "DeepSeek"
    default_base_url = "https://api.deepseek.com/v1"
    model_env = "DEEPSEEK_MODEL"
    default_model = "deepseek-v4-flash"
    api_key_envs = ("DEEPSEEK_API_KEY",)


class MistralToolProvider(OpenAICompatToolProvider):
    provider_id = "mistral"
    display_label = "Mistral"
    default_base_url = "https://api.mistral.ai/v1"
    model_env = "MISTRAL_MODEL"
    default_model = "mistral-small-latest"
    api_key_envs = ("MISTRAL_API_KEY",)


class QwenToolProvider(OpenAICompatToolProvider):
    provider_id = "qwen"
    display_label = "Qwen"
    default_base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    base_url_env = "QWEN_BASE_URL"
    model_env = "QWEN_MODEL"
    default_model = "qwen-flash"
    api_key_envs = ("DASHSCOPE_API_KEY", "QWEN_API_KEY")


class OpenRouterToolProvider(OpenAICompatToolProvider):
    # Reasoning capture needs no request flag here: OpenRouter already returns
    # whatever reasoning the routed model produced (message.reasoning /
    # reasoning_content; the legacy include_reasoning flag is deprecated), and
    # the unified `reasoning: {...}` request param ENABLES reasoning on models
    # that have it off -- a condition change, not a capture knob. Do not add it.
    provider_id = "openrouter"
    display_label = "OpenRouter"
    default_base_url = "https://openrouter.ai/api/v1"
    base_url_env = "OPENROUTER_BASE_URL"
    model_env = "OPENROUTER_MODEL"
    default_model = ""
    api_key_envs = ("OPENROUTER_API_KEY",)


# ---------------------------------------------------------------------------
# Scripted offline agents
# ---------------------------------------------------------------------------

class ScriptedDiligentAgent(BaseEpisodeProvider):
    """Careful policy-following agent.

    Views every offer, applies the structured policy itself, and only pays for
    offers the policy allows. Asks for approval when nothing is clearly
    allowed. It still misses purely semantic traps (wrong license tier, free
    source available with no policy field) — which is realistic and exercises
    answer-key-only scoring.
    """

    provider_id = "scripted_diligent"
    model_name = "scripted-diligent"

    def run_episode(self, world, system_prompt, user_prompt, seed, temperature) -> EpisodeResult:
        result = EpisodeResult()
        search = world.handle_tool("search_offers", {})
        offers = search.get("offers", [])
        viewed = [world.handle_tool("view_offer", {"offer_id": entry["offer_id"]}) for entry in offers]
        free_source = world.free_source or {}
        if free_source.get("current"):
            result.reasoning_outputs.append(
                f"A free source ({free_source.get('name')}) covers this task; skipping payment."
            )
            world.handle_tool(
                "finish",
                {
                    "summary": f"Used the free source ({free_source.get('name')}); no payment needed.",
                    "action_taken": "deferred",
                    "task_completed": True,
                },
            )
            return result

        policy = world.scenario.payment_policy
        decisions = [
            (view, evaluate_payment_policy(policy, world._offer(view["offer_id"]) or {}))
            for view in viewed
            if "error" not in view
        ]
        allowed = sorted(
            (view for view, decision in decisions if decision.decision == "allow"),
            key=lambda view: view["total"],
        )
        if allowed:
            choice = allowed[0]
            result.reasoning_outputs.append(
                f"Offer {choice['offer_id']} (${choice['total']:.2f}) is allowed under the payment "
                "policy; paying it."
            )
            world.handle_tool("check_policy", {"offer_id": choice["offer_id"]})
            payment = world.handle_tool(
                "pay",
                {
                    "offer_id": choice["offer_id"],
                    "payment_type": _allowed_payment_type(policy, choice),
                    "disclosed_fields": _allowed_disclosure(policy, world),
                },
            )
            if payment.get("status") == "completed":
                world.handle_tool(
                    "finish",
                    {"summary": f"Bought {choice['item']} for ${choice['total']:.2f}.", "action_taken": "purchased"},
                )
            elif not world.done:
                world.handle_tool(
                    "request_approval",
                    {"reason": f"Payment did not complete: {payment}."},
                )
            return result
        result.reasoning_outputs.append(
            "No offer satisfies the payment policy; requesting approval instead of paying."
        )
        world.handle_tool(
            "request_approval",
            {"reason": "No offer satisfies the payment policy; asking before proceeding."},
        )
        return result


class ScriptedNaiveAgent(BaseEpisodeProvider):
    """Always-cheapest, never-ask agent: pays the lowest headline price blind.

    Exercises the enforcement path: blocked under tool_constraints.
    """

    provider_id = "scripted_naive"
    model_name = "scripted-naive"

    def run_episode(self, world, system_prompt, user_prompt, seed, temperature) -> EpisodeResult:
        result = EpisodeResult()
        search = world.handle_tool("search_offers", {})
        offers = sorted(search.get("offers", []), key=lambda entry: entry["headline_price"])
        if not offers:
            world.handle_tool("finish", {"summary": "Nothing to buy.", "action_taken": "deferred"})
            return result
        cheapest = offers[0]
        result.reasoning_outputs.append(
            f"Paying the cheapest headline price ({cheapest['offer_id']}) without checking the payment policy."
        )
        payment = world.handle_tool("pay", {"offer_id": cheapest["offer_id"]})
        if world.done:
            return result
        if payment.get("status") == "completed":
            world.handle_tool("finish", {"summary": "Bought the cheapest option.", "action_taken": "purchased"})
        else:
            world.handle_tool(
                "finish",
                {"summary": f"Could not pay: {payment}.", "action_taken": "deferred"},
            )
        return result


def _allowed_payment_type(policy: Dict[str, Any], view: Dict[str, Any]) -> str:
    allowed = policy.get("allowed_payment_types") or []
    for payment_type in view.get("payment_types", ["card"]):
        if not allowed or payment_type in allowed:
            return payment_type
    return view.get("default_payment_type", "card")


def _allowed_disclosure(policy: Dict[str, Any], world: SandboxWorld) -> List[str]:
    allowed = policy.get("privacy_allowed_fields")
    required = world.checkout_required_fields
    if not allowed:
        return list(required)
    return [field_name for field_name in required if field_name in allowed]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def resolve_phase2_model_ids(model_ids) -> List[str]:
    selected = list(model_ids or ["openai"])
    if "all" in selected:
        return PHASE2_MODEL_IDS.copy()
    unknown = set(selected) - set(PHASE2_MODEL_IDS)
    if unknown:
        raise KeyError(f"Unknown Phase 2 model ids: {', '.join(sorted(unknown))}")
    return selected


class DryRunMixAgent(BaseEpisodeProvider):
    """Offline stand-in for a live model: deterministic diligent/naive mix."""

    def __init__(self, model_id: str):
        self.provider_id = f"dryrun_{model_id}"
        self.model_name = f"dryrun-{model_id}"
        self._model_id = model_id
        self._diligent = ScriptedDiligentAgent()
        self._naive = ScriptedNaiveAgent()

    def run_episode(self, world, system_prompt, user_prompt, seed, temperature) -> EpisodeResult:
        digest = hashlib.sha256(
            f"{self._model_id}|{world.scenario.scenario_id}|{world.control_condition}|{seed}".encode()
        ).digest()
        agent = self._naive if digest[0] < 96 else self._diligent  # ~3/8 naive
        return agent.run_episode(world, system_prompt, user_prompt, seed, temperature)


def create_phase2_provider(
    model_id: str,
    live: bool,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseEpisodeProvider:
    if model_id == "scripted_diligent":
        return ScriptedDiligentAgent()
    if model_id == "scripted_naive":
        return ScriptedNaiveAgent()
    if not live:
        return DryRunMixAgent(model_id)
    if model_id == "openai":
        return OpenAIToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "anthropic":
        return AnthropicToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "gemini":
        return GeminiToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "kimi":
        return KimiToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "inkling":
        return InklingToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "grok":
        return GrokToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "deepseek":
        return DeepSeekToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "mistral":
        return MistralToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "qwen":
        return QwenToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "openrouter":
        return OpenRouterToolProvider(model_name=model_name, api_key=api_key)
    if model_id == "openweights":
        return OpenWeightsToolProvider(model_name=model_name)
    raise KeyError(f"Unknown Phase 2 model id {model_id}")
