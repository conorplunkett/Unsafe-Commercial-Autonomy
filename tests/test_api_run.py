"""Tests for the Vercel serverless entrypoint (api/run.py).

The public "Run it yourself" page posts to this function, so the set of
providers it accepts must stay in sync with app.providers. These tests cover
the input-validation gate only (offline, no API calls) — the live scoring path
is exercised by the harness tests.
"""

import importlib.util
from pathlib import Path

import pytest

_RUN_PY = Path(__file__).resolve().parents[1] / "api" / "run.py"
_spec = importlib.util.spec_from_file_location("paybench_api_run", _RUN_PY)
api_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api_run)


def test_allowed_providers_include_all_live_providers():
    assert api_run.ALLOWED_PROVIDERS == {
        "openai",
        "anthropic",
        "gemini",
        "kimi",
        "inkling",
    }


def test_run_cell_rejects_unknown_provider():
    with pytest.raises(ValueError, match="provider must be one of"):
        api_run.run_cell({"provider": "grok", "model": "x", "apiKey": "k"})


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini", "kimi", "inkling"])
def test_run_cell_accepts_provider_then_validates_rest(provider):
    # A known provider must pass the provider gate and fail on the *next* check
    # (missing model) rather than being rejected as an unknown provider. This
    # proves each provider is wired in without making a live API call.
    with pytest.raises(ValueError, match="A model name is required"):
        api_run.run_cell({"provider": provider, "model": "", "apiKey": "k"})
